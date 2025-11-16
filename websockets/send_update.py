# websocket/send_update.py
import boto3
import json
import os

apigw = boto3.client("apigatewaymanagementapi", endpoint_url=os.environ["WS_ENDPOINT"])
connections_table = boto3.resource("dynamodb").Table(os.environ["connections_table"])

def lambda_handler(event, context):
    body = json.loads(event.get('body', '{}'))
    message = body.get("message", "Hola mundo")

    connections = connections_table.scan().get("Items", [])
    for conn in connections:
        try:
            apigw.post_to_connection(
                ConnectionId=conn["connection_id"],
                Data=json.dumps({"message": message}).encode("utf-8")
            )
        except apigw.exceptions.GoneException:
            connections_table.delete_item(Key={"connection_id": conn["connection_id"]})

    return {"statusCode": 200, "body": "Mensaje enviado"}
