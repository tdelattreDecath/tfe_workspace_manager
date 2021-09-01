#!/usr/bin/env python3

import requests
import argparse
import json
# from requests.exceptions import HTTPError
from os import environ

#
parser = argparse.ArgumentParser()
parser.add_argument('action', help="Action of the workspace", choices=['create', 'modify', 'delete'], type=str)
parser.add_argument('organisation', help="Name of the organisation", type=str)
parser.add_argument('workspace', help="Name of the Workspace to create", type=str)
parser.add_argument('-t', '--token', help="TFE User token (overrides environment variables)", type=str)
parser.add_argument('-u', '--url', help="TFE URL (overrides environment variables)", type=str)
parser.add_argument('-x', '--execution', help="exection mode", choices=['remote', 'local', 'agent'],
                    default="remote", type=str)
parser.add_argument('-tv', '--terraform_version', help="Terraform version", type=str)
parser.add_argument('-wd', '--working_directory', help="Working directory", type=str)
parser.add_argument('-p', '--path', help="Only trigger runs when files in specified paths change", type=str)
parser.add_argument('--auto_trigger', help="Do not trigger plan on change", type=bool)
parser.add_argument('--repo', help="Workspace's VCS repository.", type=str)
parser.add_argument('--branch', help="The repository branch that Terraform will execute from.", type=str)
parser.add_argument('--oauth', help="VCS OAUTH id.", type=str)
parser.add_argument('--vault_token', help="Vault Token var", type=str)

args = parser.parse_args()

ACTION = args.action
WS_NAME = args.workspace
ORGANISATION = args.organisation

# set token
if args.token:
    TOKEN = args.token
elif environ.get("TFE_TOKEN"):
    TOKEN = environ["TFE_TOKEN"]
else:
    print("You need to provide a token via an environment variable or the --token argument")
    exit(1)

# set the URL
if args.url:
    URL = args.url
elif environ.get("TFE_URL"):
    URL = environ["TFE_URL"]
else:
    print("You need to provide a URL via an environment variable or the --url argument")
    exit(1)

# API_URL = f"{URL}/api/v2"


def send_post_request(endpoint_url: str, data: dict):
    response = requests.post(
        endpoint_url,
        headers={
            "Content-Type": "application/vnd.api+json",
            "Authorization": f"Bearer {TOKEN}"
        },
        data=json.dumps(data)
    )
    return response


def data_generation():
    data = {
        "data": {
            "attributes": {
                "name": f"{WS_NAME}",
                "vcs-repo": {},
            },
            "type": "workspaces",
        }
    }

    if ACTION == "create":
        if args.terraform_version:
            data["data"]["attributes"]["terraform_version"] = args.terraform_version

        if args.execution:
            data["data"]["attributes"]["execution-mode"] = args.execution

        if args.working_directory:
            data["data"]["attributes"]["working-directory"] = args.working_directory

        if args.auto_trigger:
            data["data"]["attributes"]["file-triggers-enabled"] = args.auto_trigger

        if args.repo:
            # a oauth token is required if vcs repo is stated
            if args.oauth:
                data["data"]["attributes"]["vcs-repo"]["oauth-token-id"] = args.token
            elif environ.get("TFE_OAUTH_TOKEN_ID"):
                data["data"]["attributes"]["vcs-repo"]["oauth-token-id"] = environ["TFE_OAUTH_TOKEN_ID"]
            else:
                print("You need to provide a OAUTH token ID via an environment variable or the --oauth argument")
                exit(2)

            data["data"]["attributes"]["vcs-repo"]["identifier"] = args.repo

        if args.branch:
            data["data"]["attributes"]["vcs-repo"]["branch"] = args.branch

    return data


def create_variable(name: str, value: str, ws_id: str, category: str, sensitive=False, hcl=False):
    var_url = f"{URL}/api/v2/workspaces/{ws_id}/vars"
    payload = {
        "data": {
            "type": "vars",
            "attributes": {
                "key": name,
                "value": value,
                "sensitive": sensitive,
                "category": category,
                "hcl": hcl,
            }
        }
    }
    send_post_request(var_url, payload)


def create_workspace():
    org_url = f"{URL}/api/v2/organizations/{ORGANISATION}/workspaces"
    payload = data_generation()

    response = send_post_request(org_url, payload).json()

    ws_id = response["data"]["id"]
    # create the VAULT_TOKEN variable
    if args.vault_token:
        vault_token = args.vault_token
    elif environ.get("VAULT_TOKEN"):
        vault_token = environ["VAULT_TOKEN"]
    else:
        vault_token = ""
    create_variable("VAULT_TOKEN", vault_token, ws_id, 'env', True)


def delete_workspace():
    org_url = f"{URL}/api/v2/organizations/{ORGANISATION}/workspaces/{WS_NAME}"
    response = requests.delete(
        org_url,
        headers={
            "Content-Type": "application/vnd.api+json",
            "Authorization": f"Bearer {TOKEN}"
        },
    )

    print(response)


if __name__ == '__main__':
    if ACTION == "create":
        create_workspace()
    elif ACTION == "delete":
        delete_workspace()
    else:
        print(f"{ACTION} not implemented yet")
