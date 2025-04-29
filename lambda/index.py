# lambda/index.py
import json
import os
import re
import requests  # 新しく追加
from botocore.exceptions import ClientError

FASTAPI_URL = os.environ.get("FASTAPI_URL", "https://a0f9-34-83-228-88.ngrok-free.app//generate")

def extract_region_from_arn(arn):
    match = re.search('arn:aws:lambda:([^:]+):', arn)
    if match:
        return match.group(1)
    return "us-east-1"

def lambda_handler(event, context):
    try:
        print("Received event:", json.dumps(event))

        # Cognitoで認証されたユーザー情報を取得
        user_info = None
        if 'requestContext' in event and 'authorizer' in event['requestContext']:
            user_info = event['requestContext']['authorizer']['claims']
            print(f"Authenticated user: {user_info.get('email') or user_info.get('cognito:username')}")

        # リクエストボディの解析
        body = json.loads(event['body'])
        message = body['message']
        conversation_history = body.get('conversationHistory', [])

        print("Sending request to FastAPI:", FASTAPI_URL)

        # FastAPI に送信するペイロード
        payload = {
            "message": message,
            "conversationHistory": conversation_history
        }

        # FastAPI に POST リクエスト送信
        fastapi_response = requests.post(FASTAPI_URL, json=payload, timeout=10)
        fastapi_response.raise_for_status()
        response_data = fastapi_response.json()

        # 応答の検証
        if not response_data.get("response"):
            raise Exception("FastAPI response missing 'response' field")

        # アシスタント応答と会話履歴
        assistant_response = response_data["response"]
        updated_history = response_data.get("conversationHistory", conversation_history + [{"role": "assistant", "content": assistant_response}])

        return {
            "statusCode": 200,
            "headers": {
                "Content-Type": "application/json",
                "Access-Control-Allow-Origin": "*",
                "Access-Control-Allow-Headers": "Content-Type,X-Amz-Date,Authorization,X-Api-Key,X-Amz-Security-Token",
                "Access-Control-Allow-Methods": "OPTIONS,POST"
            },
            "body": json.dumps({
                "success": True,
                "response": assistant_response,
                "conversationHistory": updated_history
            })
        }

    except Exception as error:
        print("Error:", str(error))

        return {
            "statusCode": 500,
            "headers": {
                "Content-Type": "application/json",
                "Access-Control-Allow-Origin": "*",
                "Access-Control-Allow-Headers": "Content-Type,X-Amz-Date,Authorization,X-Api-Key,X-Amz-Security-Token",
                "Access-Control-Allow-Methods": "OPTIONS,POST"
            },
            "body": json.dumps({
                "success": False,
                "error": str(error)
            })
        }
