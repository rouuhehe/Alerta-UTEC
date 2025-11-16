import boto3
import os
import uuid
import time
import json

# DynamoDB
dynamo = boto3.resource("dynamodb")
table_name = os.environ["incidents_table"]
incidents_table = dynamo.Table(table_name)

def lambda_handler(event, context):
    try:
        # Body esperado en JSON
        body = event.get("body")
        if isinstance(body, str):
            body = json.loads(body)
        
        required_fields = ["category", "reporter_id", "place_id"]
        for field in required_fields:
            if field not in body:
                return {"statusCode": 400, "body": f"Missing required field: {field}"}

        # Generamos ID y timestamp
        incident_id = str(uuid.uuid4())
        timestamp = str(int(time.time()))
        state = "PENDIENTE"

        # Creamos el item a guardar
        item = {
            "incident_id": incident_id,
            "category": body["category"],
            "reporter_id": body["reporter_id"],
            "place_id": body["place_id"],
            "time_created": timestamp
        }

        # solo si ya fue resuelto 
        if body.get("state"): item["state"] = body["state"]
        if body.get("solver_id"): item["solver_id"] = body["solver_id"]
        if body.get("time_resolved"): item["time_resolved"] = body["time_resolved"]
        if body.get("description"): item["description"] = body["description"]

        # Guardamos en DynamoDB
        incidents_table.put_item(Item=item)

        return {
            "statusCode": 201,
            "body": json.dumps({"message": "Incident reported", "incident_id": incident_id}),
            "headers": {"Access-Control-Allow-Origin": "*"}
        }

    except Exception as e:
        return {
            "statusCode": 500,
            "body": json.dumps({"error": str(e)}),
            "headers": {"Access-Control-Allow-Origin": "*"}
        }