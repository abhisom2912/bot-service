import requests
from dotenv import dotenv_values
import json
import sys

config = dotenv_values("../../.env")


def get_valid_protocol_ids():
    response = requests.get(config['BASE_API_URL'] + "protocol/getAllProtocols")
    protocols = json.loads(response.content)
    protocol_ids = []
    for protocol in protocols:
        for server in protocol['servers'].keys():
            if 'enable_mod_training' in protocol['servers'][server].keys() and \
                    protocol['servers'][server]['enable_mod_training']:
                protocol_ids.append(protocol['_id'])
    return protocol_ids


def trigger_training_for_protocols(protocol_ids, reset_flag):
    url = config['BASE_API_URL'] + "data/trainUsingModResponses"
    for protocol_id in protocol_ids:
        body = {"protocol_id": protocol_id ,"reset": reset_flag}
        response = requests.put(url, json.dumps(body))
        if response.status_code not in [200, 204]:
            raise Exception(f"Encountered error in training for protocol - {protocol_id} !")


def read_command_line_params():
    arguments = {}
    n = len(sys.argv)

    for i in range(1, n):
        argument = sys.argv[i].split('=')
        arguments[argument[0]] = argument[1]
    return arguments


if __name__ == '__main__':
    args = read_command_line_params()
    reset_flag = args['reset_flag'] if 'reset_flag' in args.keys() else False
    trigger_training_for_protocols(get_valid_protocol_ids(), reset_flag)
