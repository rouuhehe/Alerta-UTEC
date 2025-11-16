import boto3, os, json

def lambda_handler(event, context):
    dynamodb = boto3.resource('dynamodb')
    table_name = os.environ['users_table']
    table = dynamodb.Table(table_name)

    user_id = event["pathParameters"]["user_id"]

    try:
        response = table.get_item(
            Key={
                "user_id": user_id
            }
        )

        item = response.get("Item")
        if not item:
            return {
                "statusCode": 404,
                "body": "User not found"
            }

        return {
            "statusCode": 200,
            "body": json.dumps(item)
        }

    except Exception as e:
        print("Error:", e)
        return {"statusCode": 500, "body": "Internal error"}
