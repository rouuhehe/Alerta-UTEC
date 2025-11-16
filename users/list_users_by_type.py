import boto3
import os
import json
from boto3.dynamodb.conditions import Key

def lambda_handler(event, context):
    dynamodb = boto3.resource('dynamodb')
    table_name = os.environ['users_table']
    table = dynamodb.Table(table_name)

    user_type = event.get("query", {}).get("type")

    if not user_type:
        return {
            "statusCode": 400,
            "body": "Missing 'type' parameter"
        }

    if user_type not in ["admin", "user", "solver"]:
        return {
            "statusCode": 400,
            "body": "Invalid type value"
        }

    try:
        response = table.query(
            KeyConditionExpression=Key('type').eq(user_type)
        )

        items = response.get("Items", [])

        return {
            "statusCode": 200,
            "body": json.dumps(items)
        }

    except Exception as e:
        print("Error:", e)
        return {
            "statusCode": 500,
            "body": "Error fetching users"
        }
