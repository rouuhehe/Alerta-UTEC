import boto3
import os
import json
import hashlib
import time

def hash_password(p):
    return hashlib.sha256(p.encode()).hexdigest()

def lambda_handler(event, context):
    dynamodb = boto3.resource("dynamodb")
    table = dynamodb.Table(os.environ["users_table"])

    type = event["pathParameters"]["type"]
    user_id = event["pathParameters"]["user_id"]

    body = event.get("body")
    if isinstance(body, str):
        body = json.loads(body)

    update_expr = []
    expr_values = {}

    if "name" in body:
        name = body["name"].strip()
        if not name or not all(c.isalpha() or c.isspace() for c in name):
            return {"statusCode": 400, "body": "Invalid name"}

        update_expr.append("name = :name")
        expr_values[":name"] = name

    if "password" in body:
        if len(body["password"]) < 6:
            return {"statusCode": 400, "body": "Password too short"}

        update_expr.append("password_hash = :pwd")
        expr_values[":pwd"] = hash_password(body["password"])

    if "active" in body:
        if not isinstance(body["active"], bool):
            return {"statusCode": 400, "body": "active must be boolean"}

        update_expr.append("active = :active")
        expr_values[":active"] = body["active"]

    if not update_expr:
        return {"statusCode": 400, "body": "No valid fields to update"}

    update_expr.append("updated_at = :ts")
    expr_values[":ts"] = int(time.time())

    update_expression = "SET " + ", ".join(update_expr)

    try:
        res = table.update_item(
            Key={"user_id": user_id},
            UpdateExpression=update_expression,
            ExpressionAttributeValues=expr_values,
            ConditionExpression="attribute_exists(user_id)",
            ReturnValues="ALL_NEW"
        )

        return {
            "statusCode": 200,
            "body": json.dumps(res["Attributes"])
        }

    except dynamodb.meta.client.exceptions.ConditionalCheckFailedException:
        return {"statusCode": 404, "body": "User not found"}
    except Exception as e:
        print(e)
        return {"statusCode": 500, "body": f"Internal error: {str(e)}"}
