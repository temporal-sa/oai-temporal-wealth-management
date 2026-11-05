# API to OpenAI Agents SDK + Temporal Workflow

Exposes the Temporal chat workflow (`WealthManagementWorkflow`) with an easy to use API. The
[web application](../frontend/README.md) uses it; you can also call it with curl.

Operations (all parameters are query parameters)

| Method | Endpoint | Parameters | Description |
|---|---|---|---|
| GET | `/` | | Health check |
| POST | `/start-workflow` | `workflow_id` | Starts a chat workflow with that ID on `TEMPORAL_TASK_QUEUE` (default `Supervisor`) |
| POST | `/send-prompt` | `workflow_id`, `prompt` | Sends the customer's message to the workflow (`process_user_message` signal) |
| GET | `/get-chat-history` | `workflow_id`, `from_index` (default `0`) | Returns the conversation events (chat messages and account-opening status updates) stored in Redis, starting at `from_index` |
| POST | `/end-chat` | `workflow_id` | Sends the `end_workflow` signal |
| GET | `/chaos` | | The chaos panel's failure-injection flags and the failures they recently caused |
| POST | `/chaos` | `flag`, `enabled` (`true` / `false`) | Turns a flag on or off. Flags: `tool_down`, `llm_down`, `llm_rate_limited`, `custodian_rejects`, `slow_saga`, `workflow_bug` |
| POST | `/chaos/reset` | | Turns every flag off and clears the failure log |

CORS allows the web application at `http://localhost:3000` and `http://127.0.0.1:3000`.

## Prerequisites

* [uv](https://docs.astral.sh/uv/) - Python Dependency Management
* Temporal running (`temporal server start-dev` locally, or Temporal Cloud)
* [Redis](https://redis.io/downloads/) running (`REDIS_HOST` / `REDIS_PORT`, default `localhost:6379`)
* The worker running (`src/temporal_supervisor/startlocalworker.sh` or `startcloudworker.sh`). The API
  and the worker must use the same `TEMPORAL_TASK_QUEUE`.

See the [Temporal README](../temporal_supervisor/README.md) for setting these up.

## Set up Python Environment
From the repository root:
```bash
uv sync
```

### Start API Server

The API listens on http://127.0.0.1:8000 (uvicorn's default, with `--reload`). Both scripts source
`../../setclaimcheck.sh`. Claim check is optional: if you haven't created it, the script prints a
harmless "No such file or directory" message.

#### Connect locally
From the repository root:
```bash
cd src/api
./startlocalapi.sh
```

#### Connect to Temporal Cloud
Be sure to have created setcloudenv.sh in the repository root. See the [Temporal README](../temporal_supervisor/README.md#running-the-demo-in-temporal-cloud) for more details.
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

Send a prompt
```bash
curl -X POST 'http://127.0.0.1:8000/send-prompt?workflow_id=<your-workflow-id>&prompt=Who%20are%20my%20beneficiaries%3F'
```

Respond with a client ID
```bash
curl -X POST 'http://127.0.0.1:8000/send-prompt?workflow_id=<your-workflow-id>&prompt=123'
```

Ask about investment accounts
```bash
curl -X POST 'http://127.0.0.1:8000/send-prompt?workflow_id=<your-workflow-id>&prompt=What%20investment%20accounts%20do%20I%20have%3F'
```

Get the chat history
```bash
curl "http://127.0.0.1:8000/get-chat-history?workflow_id=<your-workflow-id>&from_index=0"
```

Turn a chaos flag on, list the flags, and turn them all off
```bash
curl -X POST 'http://127.0.0.1:8000/chaos?flag=tool_down&enabled=true'
curl http://127.0.0.1:8000/chaos
curl -X POST http://127.0.0.1:8000/chaos/reset
```

End the Chat
```bash
curl -X POST "http://127.0.0.1:8000/end-chat?workflow_id=<your-workflow-id>"
```
