# websocket/disconnect.py
import boto3
import os

dynamodb = boto3.resource("dynamodb")
connections_table = dynamodb.Table(os.environ["connections_table"])

def lambda_handler(event, context):
    connection_id = event['requestContext']['connectionId']
    connections_table.delete_item(Key={'connection_id': connection_id})
    return {"statusCode": 200}
