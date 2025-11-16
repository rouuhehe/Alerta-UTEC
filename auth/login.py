import uuid, boto3, os, json, hashlib, hmac, base64, time

SECRET = os.environ["JWT_SECRET"]

def make_token(payload):
    header = base64.urlsafe_b64encode(json.dumps({"alg": "HS256"}).encode()).decode().rstrip("=")
    body = base64.urlsafe_b64encode(json.dumps(payload).encode()).decode().rstrip("=")
    signature = base64.urlsafe_b64encode(
        hmac.new(SECRET.encode(), f"{header}.{body}".encode(), hashlib.sha256).digest()
    ).decode().rstrip("=")
    return f"{header}.{body}.{signature}"

def hash_password(password): 
    return hashlib.sha256(password.encode()).hexdigest()

def lambda_handler(event, context):
    body = event.get("body")

    if isinstance(body, str):
        body = json.loads(body)

    user_id = body["user_id"]
    password = body["password"]

    if not user_id or not password:
        return {"statusCode": 400, "body": "missing fields"}
    
    type = body.get("type", "user")   # 'USER', 'ADMIN', 'SOLVER'
    department = body.get("department", None)  # SOLO SI ES SOLVER

    dynamo = boto3.resource('dynamodb')
    users = dynamo.Table(os.getenv("users_table"))
    sessions = dynamo.Table(os.getenv("sessions_table"))

    old = sessions.scan(
        FilterExpression="user_id = :u AND valid = :v",
        ExpressionAttributeValues={":u": user_id, ":v": True}
    ).get("Items", [])

    for s in old:
        sessions.update_item(
            Key={"session_id": s["session_id"]},
            UpdateExpression="set valid = :f",
            ExpressionAttributeValues={":f": False}
        )


    # BUSCAMOS AL USUARIO DIRECTO POR TYPE Y user_id
    res = users.get_item(Key={"type": type, "user_id": user_id})

    if "Item" not in res:
        return {"statusCode": 404, "body": "user not found"}

    user = res["Item"]

    if user["type"] != type:
        return {"statusCode": 403, "body": "role mismatch"}

    if not user["active"]:
        return {"statusCode": 403, "body": "user disabled"}

    # VALIDACIÓN DE PASSWORD
    if user["password_hash"] != hash_password(password):
        return {"statusCode": 401, "body": "invalid credentials"}

    session_id = str(uuid.uuid4())

    # CREAMOS TOKEN
    payload = {
        "sub": user["user_id"],
        "type": user["type"],
        "session_id": session_id,
        "iat": int(time.time()),
        "exp": int(time.time()) + 43200,
    }

    token = make_token(payload)

    sessions.put_item(Item={
        "session_id": session_id,
        "user_id": user["user_id"],
        "type": user["type"],
        "token": token,
        "created_at": int(time.time()),
        "expires_at": payload["exp"],
        "valid": True
    })

    log_info = {
        "event": "login",
        "user_id": user["user_id"],
        "type": user["type"],
        "session_id": session_id,
        "timestamp": int(time.time())
    }
    print("INFO:", json.dumps(log_info))

    return {
        "statusCode": 200,
        "body": json.dumps({
            "token": token,
            "session_id": session_id,
        })
    }
