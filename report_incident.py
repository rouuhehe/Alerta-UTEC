import base64, hashlib, hmac, boto3, os, uuid, time, json
from notify_incident import notify_incident

SECRET_KEY = os.environ["JWT_SECRET"]

# DynamoDB
dynamo = boto3.resource("dynamodb")
table_name = os.environ["incidents_table"]
incidents_table = dynamo.Table(table_name)

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
        return {"statusCode": 401, "body": "missing token"}
    token = auth.replace("Bearer ", "")
    user = verify_token(token)
    if not user:
        return {"statusCode": 401, "body": "invalid token"}

    try:
        body = event.get("body")
        if isinstance(body, str):
            body = json.loads(body)

        required_fields = ["category", "place", "description"]
        for field in required_fields:
            if field not in body:
                return {"statusCode": 400, "body": f"Missing required field: {field}"}

        incident_id = str(uuid.uuid4())
        timestamp = str(int(time.time()))

        reporter_id = user["sub"]

        # Creamos el item a guardar
        item = {
            "incident_id": incident_id,
            "category": body["category"],
            "reporter_id": reporter_id,
            "place": body["place"],
            "time_created": timestamp,
            "description": body.get("description")
        }

        # Campos opcionales
        for optional in ["state", "solver_id", "time_resolved"]:
            if body.get(optional):
                item[optional] = body[optional]

        # Guardamos en DynamoDB :)
        incidents_table.put_item(Item=item)

        # Enviamos notificacion
        notify_incident(item)

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