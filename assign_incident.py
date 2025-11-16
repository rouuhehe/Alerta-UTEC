import boto3
import os
import json

# Conexión a DynamoDB
dynamo = boto3.resource("dynamodb")
table_name = os.environ["incidents_table"]
incidents_table = dynamo.Table(table_name)

def lambda_handler(event, context):
    try:
        # Tomamos el incident_id desde path parameter
        incident_id = event.get("pathParameters", {}).get("incident_id")
        if not incident_id:
            return {
                "statusCode": 400,
                "body": json.dumps({"error": "Missing incident_id in path"}),
                "headers": {"Access-Control-Allow-Origin": "*"}
            }

        # Tomamos body
        body = event.get("body")
        if isinstance(body, str):
            body = json.loads(body)

        area = body.get("area")
        if not area:
            return {
                "statusCode": 400,
                "body": json.dumps({"error": "Missing required field: area"}),
                "headers": {"Access-Control-Allow-Origin": "*"}
            }

        # Actualizamos solo el campo area
        response = incidents_table.update_item(
            Key={"incident_id": incident_id},
            UpdateExpression="SET area = :a",
            ExpressionAttributeValues={":a": area},
            ReturnValues="ALL_NEW"
        )

        return {
            "statusCode": 200,
            "body": json.dumps({
                "message": "Incident area updated",
                "incident": response.get("Attributes", {})
            }),
            "headers": {"Access-Control-Allow-Origin": "*"}
        }

    except Exception as e:
        return {
            "statusCode": 500,
            "body": json.dumps({"error": str(e)}),
            "headers": {"Access-Control-Allow-Origin": "*"}
        }