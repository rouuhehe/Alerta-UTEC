import json
import boto3
import os

dynamodb = boto3.client("dynamodb")
table_name = os.environ["incidents_table"]

def lambda_handler(event, context):
    try:
        # Obtenemos el path parameter 'id'
        incident_id = event.get("pathParameters", {}).get("incident_id")
        if not incident_id:
            return {
                "statusCode": 400,
                "body": json.dumps({"error": "Missing incident_id in path"}),
                "headers": {"Access-Control-Allow-Origin": "*"}
            }

        # Obtenemos el item de DynamoDB
        resp = dynamodb.get_item(
            TableName=table_name,
            Key={"incident_id": {"S": incident_id}}
        )

        if "Item" not in resp:
            return {
                "statusCode": 404,
                "body": json.dumps({"error": "Incident not found"}),
                "headers": {"Access-Control-Allow-Origin": "*"}
            }

        # Convertimos el formato de DynamoDB a JSON simple
        item = {k: list(v.values())[0] for k, v in resp["Item"].items()}

        return {
            "statusCode": 200,
            "body": json.dumps(item),
            "headers": {"Access-Control-Allow-Origin": "*"}
        }

    except Exception as e:
        return {
            "statusCode": 500,
            "body": json.dumps({"error": str(e)}),
            "headers": {"Access-Control-Allow-Origin": "*"}
        }