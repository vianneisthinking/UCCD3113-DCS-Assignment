"""Local API Gateway HTTP API v2 smoke test for the Mangum handler."""

import base64
import json
import time

from lambda_handler import handler


def invoke(method, path, body=None, token=None, query=""):
    headers = {"content-type": "application/json"}
    if token:
        headers["authorization"] = f"Bearer {token}"
    event = {
        "version": "2.0",
        "routeKey": "$default",
        "rawPath": path,
        "rawQueryString": query,
        "headers": headers,
        "requestContext": {
            "http": {
                "method": method,
                "path": path,
                "protocol": "HTTP/1.1",
                "sourceIp": "127.0.0.1",
                "userAgent": "lambda-local-test",
            },
            "requestId": "local-test",
            "routeKey": "$default",
            "stage": "$default",
            "time": "20/Aug/2026:00:00:00 +0000",
            "timeEpoch": 0,
        },
        "isBase64Encoded": False,
    }
    if body is not None:
        event["body"] = json.dumps(body)
    response = handler(event, {})
    payload = response.get("body", "")
    if response.get("isBase64Encoded"):
        payload = base64.b64decode(payload).decode()
    return response["statusCode"], json.loads(payload) if payload else None


def main():
    suffix = int(time.time() * 1000)
    email = f"lambda_{suffix}@example.com"
    password = "LambdaTest!123"

    code, user = invoke("POST", "/auth/register", {"email": email, "password": password, "name": "Lambda Test"})
    assert code == 201, (code, user)
    code, login = invoke("POST", "/auth/login", {"email": email, "password": password})
    assert code == 200, (code, login)
    token = login["access_token"]
    code, me = invoke("GET", "/auth/me", token=token)
    assert code == 200 and me["email"] == email
    code, ticket = invoke("POST", "/tickets", {"complaint": "I was charged twice for my monthly subscription."}, token)
    assert code == 201 and ticket["category"] and ticket["priority"], (code, ticket)
    code, tickets = invoke("GET", "/tickets", token=token)
    assert code == 200 and tickets[0]["id"] == ticket["id"]
    code, _ = invoke("GET", "/tickets", token="invalid")
    assert code == 401
    print(json.dumps({"status": "PASS", "ticket_id": ticket["id"], "category": ticket["category"], "priority": ticket["priority"]}))


if __name__ == "__main__":
    main()
