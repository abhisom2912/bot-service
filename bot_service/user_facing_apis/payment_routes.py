from fastapi import APIRouter, Body, Request, Response, HTTPException, status
from fastapi.encoders import jsonable_encoder

from models import Payment, PaymentUpdate
import uuid
import json
from datetime import datetime
from web3 import Web3


payment_router = APIRouter()

erc20_abi = '[{"constant":true,"inputs":[],"name":"name","outputs":[{"name":"","type":"string"}],"payable":false,"type":"function"},{"constant":true,"inputs":[],"name":"decimals","outputs":[{"name":"","type":"uint8"}],"payable":false,"type":"function"},{"constant":true,"inputs":[{"name":"_owner","type":"address"}],"name":"balanceOf","outputs":[{"name":"balance","type":"uint256"}],"payable":false,"type":"function"},{"constant":true,"inputs":[],"name":"symbol","outputs":[{"name":"","type":"string"}],"payable":false,"type":"function"}]'
accepted_method = '0xa9059cbb'
accepted_address = '0x6387251a287d570252ddfeda963d2ceb1181644e'


def get_accepted_payment_info(chain_id):
    file = open('./resources/accepted_payment_methods.json')
    chain_id = str(chain_id)
    accepted_payments = json.load(file)
    accepted_tokens = {}

    chain_accepted_payment = accepted_payments[chain_id]
    if chain_accepted_payment is None:
        raise HTTPException(status_code=status.HTTP_406_NOT_ACCEPTABLE,
                            detail=f"This chain is not supported for payment")

    for accepted_token in chain_accepted_payment['accepted_tokens']:
        accepted_tokens[accepted_token['token_address'].lower()] = accepted_token['token_name']
    return chain_accepted_payment['chain_name'], accepted_tokens, chain_accepted_payment['minimum_amount']


def get_payment_details(chain_id, transaction_hash):
    chain_name, accepted_tokens, min_amount = get_accepted_payment_info(chain_id)
    file = open('./resources/rpc.json')
    chain_rpc = json.load(file)
    web3 = Web3(Web3.HTTPProvider(chain_rpc[chain_id]))
    transaction = web3.eth.get_transaction(transaction_hash)
    transaction_receipt = web3.eth.get_transaction_receipt(transaction_hash)
    method = transaction['input'][0:10]
    if method != accepted_method:
        raise HTTPException(status_code=status.HTTP_405_METHOD_NOT_ALLOWED,
                            detail=f"The transaction is not for a correct method")

    destination_address = '0x' + transaction['input'][11:74].lstrip('0')
    if destination_address != accepted_address:
        raise HTTPException(status_code=status.HTTP_412_PRECONDITION_FAILED,
                            detail=f"The destination address is not an accepted address")

    token_address = transaction_receipt['logs'][0]['address']
    if token_address.lower() not in accepted_tokens.keys():
        raise HTTPException(status_code=status.HTTP_406_NOT_ACCEPTABLE, detail=f"This token address is not supported "
                                                                               f"for payment")

    token_contract = web3.eth.contract(transaction_receipt['logs'][0]['address'], abi=erc20_abi)
    decimals = token_contract.functions.decimals().call()
    amount = int(transaction['input'][75:139].lstrip('0'), 16) / 10 ** decimals
    if amount < min_amount:
        raise HTTPException(status_code=status.HTTP_406_NOT_ACCEPTABLE, detail=f"Amount should be more than the min "
                                                                               f"value - {min_amount} USD")
    payment_details = {"transaction_hash":transaction_hash,"chain_id":chain_id,"chain":chain_name,
                                  "token_address":token_address,"token_symbol":accepted_tokens[token_address.lower()],
                                  "amount":amount}
    return payment_details



@payment_router.post("/", response_description="Create/Update a new payment", status_code=status.HTTP_201_CREATED)
def create_payment(request: Request, payment: Payment = Body(...)):
    payment = jsonable_encoder(payment)
    amount = payment['payment_details']['amount']
    chain_name, accepted_tokens, min_amount = get_accepted_payment_info(payment['payment_details']['chain_id'])

    if payment['payment_details']['token_address'].lower() not in accepted_tokens.keys():
        raise HTTPException(status_code=status.HTTP_406_NOT_ACCEPTABLE, detail=f"This token address is not supported "
                                                                               f"for payment")
    if amount < min_amount:
        raise HTTPException(status_code=status.HTTP_406_NOT_ACCEPTABLE, detail=f"Amount should be more than the min "
                                                                               f"value - {min_amount} USD")

    if request.app.database["payments"].find_one(
            {"payment_details.transaction_hash": payment['payment_details']['transaction_hash']}):
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=f"This txn hash already exists")

    protocol_payments = request.app.database["payments"].find_one({"protocol_id": payment['protocol_id']})
    payment['payment_details']['update_time'] = datetime.now()

    if protocol_payments is None:
        payment['payment_details'] = [payment['payment_details']]
        request.app.database["payments"].insert_one(payment)
    else:
        protocol_payments['payment_details'].append(payment['payment_details'])
        request.app.database["payments"].update_one({"protocol_id": payment['protocol_id']},
                                                    {'$set': protocol_payments})
    protocol = request.app.database["protocols"].find_one({"_id": payment['protocol_id']})

    if protocol is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Protocol with id {payment['protocol_id']} "
                                                                          f"not found")

    total_credits = protocol['credits'] + amount
    print(total_credits)
    update_result = request.app.database["protocols"].update_one(
        {"_id": protocol['_id']}, {"$set": {"credits": total_credits}}
    )

    return {'status': 'Payment details successfully updated'}


@payment_router.post("/{protocol_id}/{chain_id}/{transaction_hash}", response_description="Create/Update a new payment",
                     status_code=status.HTTP_201_CREATED)
def create_payment(protocol_id: str, chain_id: str, transaction_hash: str, request: Request):
    protocol = request.app.database["protocols"].find_one({"_id": protocol_id})

    if protocol is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Protocol with id {protocol_id} "
                                                                          f"not found")
    if request.app.database["payments"].find_one({"payment_details.transaction_hash": transaction_hash}):
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=f"This txn hash already exists")

    payment_details = get_payment_details(chain_id, transaction_hash)
    payment_details['update_time'] = datetime.now()

    protocol_payments = request.app.database["payments"].find_one({"protocol_id": protocol_id})
    if protocol_payments is None:
        payment = {'protocol_id':protocol_id, 'payment_details': [payment_details], "_id": uuid.uuid4()}
        request.app.database["payments"].insert_one(jsonable_encoder(payment))
    else:
        protocol_payments['payment_details'].append(payment_details)
        request.app.database["payments"].update_one({"protocol_id": protocol_id}, {'$set': protocol_payments})

    total_credits = protocol['credits'] + payment_details['amount']
    print(total_credits)
    update_result = request.app.database["protocols"].update_one(
        {"_id": protocol['_id']}, {"$set": {"credits": total_credits}}
    )

    return {'status': 'Payment details successfully updated'}


@payment_router.get("/{transaction_hash}", response_description="Get a payment by transaction hash",
                    response_model=Payment)
def find_payment(transaction_hash: str, request: Request):
    if (payment := request.app.database["payments"].find_one(
            {"payment_details.transaction_hash": transaction_hash})) is not None:
        return payment
    raise HTTPException(status_code=status.HTTP_404_NOT_FOUND,
                        detail=f"Payment with txn hash {transaction_hash} not found")


if __name__ == '__main__':
    get_accepted_payment_info(56)
    get_payment_details('137', '0x360de3b3a73678cf8bd952511f8ca66395a986b612ccf4682b1d535dc5ae79f3')
