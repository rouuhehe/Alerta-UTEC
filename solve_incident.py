import boto3
import os
import time
import json
import base64
import hmac
import hashlib

SECRET_KEY = os.environ["JWT_SECRET"]

def b64url_encode(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).decode().rstrip("=")

def b64url_decode(data: str) -> bytes:
    padding = "=" * (-len(data) % 4)
    return base64.urlsafe_b64decode(data + padding)

def verify_token(token):
    try:
        header_b64, body_b64, signature = token.split(".")
        expected_sig = b64url_encode(
            hmac.new(SECRET_KEY.encode(), f"{header_b64}.{body_b64}".encode(), hashlib.sha256).digest()
        )
        if not hmac.compare_digest(expected_sig, signature):
            return None
        payload = json.loads(b64url_decode(body_b64))
        if payload.get("exp", 0) < time.time():
            return None
        return payload
    except:
        return None

dynamo = boto3.resource("dynamodb")
table_name = os.environ["incidents_table"]
incidents_table = dynamo.Table(table_name)

def lambda_handler(event, context):
    headers = event.get("headers", {})
    auth = headers.get("authorization") or headers.get("Authorization") or ""

    if not auth.startswith("Bearer "):
        return {"statusCode": 401, "body": "missing token", "headers": {"Access-Control-Allow-Origin": "*"}}

    token = auth.replace("Bearer ", "")
    user = verify_token(token)

    if not user:
        return {"statusCode": 401, "body": "invalid token", "headers": {"Access-Control-Allow-Origin": "*"}}

    # SOLO admin o solver pueden resolver incidentes
    if user.get("type") not in ["admin", "solver"]:
        return {
            "statusCode": 403,
            "body": "forbidden: only admins or solvers can resolve incidents",
            "headers": {"Access-Control-Allow-Origin": "*"}
        }

    try:
        incident_id = event["pathParameters"].get("incident_id")
        if not incident_id:
            return {
                "statusCode": 400,
                "body": json.dumps({"error": "Missing incident_id in path"}),
                "headers": {"Access-Control-Allow-Origin": "*"}
            }

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
            "body": json.dumps({
                "message": "Incident resolved",
                "incident": response["Attributes"]
            }),
            "headers": {"Access-Control-Allow-Origin": "*"}
        }

    except Exception as e:
        return {
            "statusCode": 500,
            "body": json.dumps({"error": str(e)}),
            "headers": {"Access-Control-Allow-Origin": "*"}
        }
