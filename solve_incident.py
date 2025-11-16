import boto3
import os
import time
import json

dynamo = boto3.resource("dynamodb")
table_name = os.environ["incidents_table"]
incidents_table = dynamo.Table(table_name)

def lambda_handler(event, context):
    try:
        incident_id = event["pathParameters"]["incident_id"]

        body = event.get("body")
        if isinstance(body, str):
            body = json.loads(body)
        solver_id = body.get("solver_id")
        description = body.get("description")

        if not solver_id:
            return {"statusCode": 400, "body": "Missing required field: solver_id"}

        timestamp = str(int(time.time()))
        update_expr = "SET #st = :s, solver_id = :solver, time_resolved = :tr"
        expr_attr_vals = {":s": "RESUELTO", ":solver": solver_id, ":tr": timestamp}
        expr_attr_names = {"#st": "state"}

        if description:
            update_expr += ", description = :desc"
            expr_attr_vals[":desc"] = description

        response = incidents_table.update_item(
            Key={"incident_id": incident_id},
            UpdateExpression=update_expr,
            ExpressionAttributeValues=expr_attr_vals,
            ExpressionAttributeNames=expr_attr_names,
            ReturnValues="ALL_NEW"
        )

        return {
            "statusCode": 200,
            "body": json.dumps({"message": "Incident resolved", "incident": response["Attributes"]}),
            "headers": {"Access-Control-Allow-Origin": "*"}
        }

    except Exception as e:
        return {"statusCode": 500, "body": json.dumps({"error": str(e)}), "headers": {"Access-Control-Allow-Origin": "*"}}