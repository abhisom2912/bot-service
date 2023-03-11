# Assuming we take trial payments in one of the wallets from the users
# valid_token_addresses are the token addresses in which payment is accepted
# payment_address is the address in which payment is expected to come
import requests
from dotenv import dotenv_values
import math
import enum

config = dotenv_values(".env")
api_key = config['POLYGON_SCAN_API_KEY']
valid_token_addresses = ['0x0fa8781a83e46826621b3bc094ea2a0212e71b23']
payment_address = '0xfaec431cb76e10b6c2c275ae4baad2f34ac46322'
expected_txn_amount = 10


class Status(enum.Enum):
    SUCCESS = 0
    AMOUNT_NOT_CORRECT = 1
    TOKEN_ADDRESS_NOT_VALID = 2
    FROM_ADDRESS_NOT_MATCHING = 3
    TXN_HASH_NOT_FOUND = 4
    UNKNOWN_ERROR = 5


def validate_payment(txn_hash, address):
    response = requests.get("https://api-testnet.polygonscan.com/api?module=account&action=tokentx&sort=desc&"
                            "&page=1&offset=1000&address=" + payment_address + "&apikey=" + api_key)

    txn_hash_found = False
    for transaction in response.json()['result']:
        if transaction['hash'] == txn_hash:
            txn_hash_found = True
            txn_amount = int(transaction['value']) / math.pow(10, int(transaction['tokenDecimal']))
            if txn_amount == expected_txn_amount and transaction['contractAddress'].lower() in valid_token_addresses \
                    and transaction['from'].lower() == address:
                return Status.SUCCESS
            elif txn_amount != expected_txn_amount:
                return Status.AMOUNT_NOT_CORRECT
            elif not transaction['contractAddress'].lower() in valid_token_addresses:
                return Status.TOKEN_ADDRESS_NOT_VALID
            elif transaction['from'].lower() != address:
                return Status.FROM_ADDRESS_NOT_MATCHING
    if txn_hash_found == False:
        return Status.TXN_HASH_NOT_FOUND
    return Status.UNKNOWN_ERROR


def main():
    address = '0x48520ff9b32d8b5bf87abf789ea7b3c394c95ebe'
    txn_hash = '0xc3b0f7c25fc1418be7ef1c7a4ebf5b05bb852564f688bde1538f5daa8d602ff1'
    status = validate_payment(txn_hash, address)
    print(status.name, status.value)


if __name__ == '__main__':
    main()
