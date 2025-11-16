import boto3
import os
import json
import base64
import hmac
import hashlib
import time

SECRET_KEY = os.environ["JWT_SECRET"]
dynamo = boto3.resource("dynamodb")
table_name = os.environ["incidents_table"]
incidents_table = dynamo.Table(table_name)

# Funciones de JWT
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

def lambda_handler(event, context):
    headers = event.get("headers", {})
    auth = headers.get("authorization") or headers.get("Authorization") or ""
    if not auth.startswith("Bearer "):
        return {"statusCode": 401, "body": "missing token", "headers": {"Access-Control-Allow-Origin": "*"}}
    
    token = auth.replace("Bearer ", "")
    user = verify_token(token)
    if not user:
        return {"statusCode": 401, "body": "invalid token", "headers": {"Access-Control-Allow-Origin": "*"}}
    
    if user.get("type") != "admin":
        return {"statusCode": 403, "body": "forbidden: admin only", "headers": {"Access-Control-Allow-Origin": "*"}}

    try:
        incident_id = event.get("pathParameters", {}).get("incident_id")
        if not incident_id:
            return {"statusCode": 400, "body": json.dumps({"error": "Missing incident_id in path"}), "headers": {"Access-Control-Allow-Origin": "*"}}

        body = event.get("body")
        if isinstance(body, str):
            body = json.loads(body)

        area = body.get("area")
        valid_areas = ["limpieza", "mantenimiento", "seguridad"]
        if not area or area not in valid_areas:
            return {
                "statusCode": 400,
                "body": json.dumps({"error": f"Invalid area. Must be one of: {valid_areas}"}),
                "headers": {"Access-Control-Allow-Origin": "*"}
            }

        response = incidents_table.update_item(
            Key={"incident_id": incident_id},
            UpdateExpression="SET area = :a",
            ExpressionAttributeValues={":a": area},
            ReturnValues="ALL_NEW"
        )

        return {
            "statusCode": 200,
            "body": json.dumps({"message": "Incident area updated", "incident": response.get("Attributes", {})}),
            "headers": {"Access-Control-Allow-Origin": "*"}
        }

    except Exception as e:
        return {"statusCode": 500, "body": json.dumps({"error": str(e)}), "headers": {"Access-Control-Allow-Origin": "*"}}
