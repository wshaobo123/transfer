import requests

API_URL = "http://25.50.206.61:6080/v1/chat-messages"
API_KEY = "app-xxxxxxxxxxxxxxxx"

headers = {
    "Authorization": f"Bearer {API_KEY}",
    "Content-Type": "application/json"
}

data = {
    "inputs": {},
    "query": "员工请假流程是什么？",
    "response_mode": "blocking",
    "conversation_id": "",
    "user": "test-user"
}

response = requests.post(
    API_URL,
    headers=headers,
    json=data
)

print(response.json())