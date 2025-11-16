import json, boto3, os, base64, hmac, hashlib, time

SECRET_KEY = os.environ["JWT_SECRET_KEY"]
dynamodb = boto3.client("dynamodb")
table_name = os.environ["incidents_table"]

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
        return {
            "statusCode": 401, 
            "body": "missing token", 
            "headers": {"Access-Control-Allow-Origin": "*"}
            }

    token = auth.replace("Bearer ", "")
    user = verify_token(token)
    if not user:
        return {
            "statusCode": 401, 
            "body": "invalid token", 
            "headers": {"Access-Control-Allow-Origin": "*"}
            }
    try:
        incident_id = event.get("pathParameters", {}).get("incident_id")
        if not incident_id:
            return {
                "statusCode": 400, 
                "body": json.dumps({"error": "Missing incident_id in path"}), 
                "headers": {"Access-Control-Allow-Origin": "*"}
                }

        resp = dynamodb.get_item(TableName=table_name, Key={"incident_id": {"S": incident_id}})
        if "Item" not in resp:
            return {
                "statusCode": 404, 
                "body": json.dumps({"error": "Incident not found"}), 
                "headers": {"Access-Control-Allow-Origin": "*"}
                }

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
