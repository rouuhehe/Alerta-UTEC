import json
import boto3
import os

dynamodb = boto3.client("dynamodb")
table_name = os.environ["incidents_table"]

def lambda_handler(event, context):
    print("Llegue aca :) !!!")
    try:
        params = event.get("queryStringParameters") or {}
        state = params.get("state")
        category = params.get("category")
        reporter = params.get("reporter_id")
        solver = params.get("solver_id")

        if state and category:
            resp = dynamodb.query(
                TableName=table_name,
                IndexName="state_category_index",
                KeyConditionExpression="state = :s AND category = :c",
                ExpressionAttributeValues={
                    ":s": {"S": state},
                    ":c": {"S": category}
                }
            )
        
        elif reporter:
            resp = dynamodb.query(
                TableName=table_name,
                IndexName="reporter_history_index",
                KeyConditionExpression="reporter_id = :r",
                ExpressionAttributeValues={
                    ":r": {"S": reporter}
                }
            )

        elif solver:
            resp = dynamodb.query(
                TableName=table_name,
                IndexName="solver_history_index",
                KeyConditionExpression="solver_id = :s",
                ExpressionAttributeValues={
                    ":s": {"S": solver}
                }
            )

        else:
            resp = dynamodb.scan(TableName=table_name)

        items = [{k: list(v.values())[0] for k, v in item.items()} for item in resp.get("Items", [])]
        
        items.sort(key=lambda x: int(x["time_created"]), reverse=True)

        return {
            "statusCode": 200,
            "body": json.dumps(items),
            "headers": {"Access-Control-Allow-Origin": "*"}
        }

    except Exception as e:
        return {"statusCode": 500, "body": json.dumps({"error": str(e)})}
