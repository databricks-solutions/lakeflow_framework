import json
import requests
import time

from pyspark.sql.types import StructType


API_STATEMENTS = "/api/2.0/sql/statements/"


def api_get(url: str, token, payload: str):

    headers = {
        'Authorization': f'Bearer {token}',
        'Content-Type': 'application/json'
    }

    if payload:
        data = json.dumps(payload)

    return requests.post(url, headers=headers, data=data)


def api_post(url: str, token, payload: str = None):

    headers = {
        'Authorization': f'Bearer {token}',
        'Content-Type': 'application/json'
    }

    return requests.get(url, headers=headers, data=json.dumps(payload))


def call_statement_api(workspace_url: str, token, payload: str):

    api = API_STATEMENTS
    base_url = f"{workspace_url}{api}"
    response = api_post(base_url, token, payload)

    # Check the response
    if response.status_code == 200:
        statement_id = response.json()['statement_id']
        print(f"Statement ID: {statement_id}")
        while 1:
            response = api_get(f"{base_url}/{statement_id}", token)
            state = response.json()['status']['state']
            if state in ('SUCCEEDED', 'FAILED'):
                print(state)
                break
            else:
                time.sleep(2)
    else:
        print(f"API Error: Failed to execute SQL statement, status: {response.status_code}")