# API to OpenAI Agents SDK + Temporal Workflow

Exposes a Temporal Workflow with an easy to use API

Operations
* 

## Prerequisites

* [Poetry](https://python-poetry.org/docs/) - Python Dependency Management

## Set up Python Environment
```bash
poetry install
```

### Start API Server

#### Connect locally
```bash
cd src/api
./startlocalapi.sh
```

#### Connect to Temporal Cloud
Be sure to have created / updated ../../setcloudenv.sh. See [README](../temporal_supervisor/README.md) for more details.
```bash
cd src/api
./startcloudapi.sh
```

Test that the API is running:
```bash
curl http://127.0.0.1:8000
```

Start a workflow:
```bash
curl -X POST 'http://127.0.0.1:8000/start-workflow?workflow_id=<your-workflow-id>'
```

Send a prompt (first time)
```bash
curl -X POST 'http://127.0.0.1:8000/send-prompt?workflow_id=<your-workflow-id>&prompt=Who%20are%20my%20beneficiaries%3F&chat_len=0'
```

Respond with an account ID
```bash
curl -X POST 'http://127.0.0.1:8000/send-prompt?workflow_id=<your-workflow-id>&prompt=123&chat_len=1'
```

Ask about investment accounts
```bash
curl -X POST 'http://127.0.0.1:8000/send-prompt?workflow_id=<your-workflow-id>&prompt=What%20investment%20accounts%20do%20I%20have%3F&chat_len=2'
```

Query the chat history
```bash
curl "http://127.0.0.1:8000/get-chat-history?workflow_id=<your-workflow-id>&from_index=<index (integer)>"
```

End the Chat
```bash
curl -X POST "http://127.0.0.1:8000/end-chat?workflow_id=<your-workflow-id>"
```