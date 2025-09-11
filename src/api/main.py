from contextlib import asynccontextmanager
from typing import Optional, AsyncGenerator

from fastapi import FastAPI, HTTPException, Request, Query
from fastapi.middleware.cors import CORSMiddleware
from temporalio.client import Client
from temporalio.common import WorkflowIDReusePolicy
from temporalio.exceptions import TemporalError
from temporalio.contrib.openai_agents import OpenAIAgentsPlugin
from temporalio.service import RPCError

from common.event_stream_manager import EventStreamManager
from common.client_helper import ClientHelper
from common.user_message import ProcessUserMessageInput
from temporal_supervisor.claim_check.claim_check_plugin import ClaimCheckPlugin
from temporal_supervisor.workflows.supervisor_workflow import WealthManagementWorkflow

temporal_client: Optional[Client] = None
task_queue: Optional[str] = None

WORKFLOW_ID = "oai-temporal-agent"

@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    # app startup
    print("API is starting up...")
    global temporal_client
    global task_queue
    client_helper = ClientHelper()
    task_queue = client_helper.taskQueue
    temporal_client = await Client.connect(
        target_host=client_helper.address,
        namespace=client_helper.namespace,
        tls=client_helper.get_tls_config(),
        plugins=[
            OpenAIAgentsPlugin(),
            ClaimCheckPlugin(),
        ]
    )
    yield
    print("API is shutting down...")
    # app teardown
app = FastAPI(lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://127.0.0.1:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/")
def root():
    return {"message": "OpenAI Agent SDK + Temporal Agent!"}

@app.get("/get-chat-history")
async def get_chat_history(
    from_index: int = Query(0, description="Get events starting from this index")
):
    """ Retrieves the chat history from Redis """
    try:
        history = await EventStreamManager().get_events_from_index(WORKFLOW_ID, from_index)
        if history is None:
            return ""

        return history

    except Exception as e:
        error_message = str(e)
        print(f"Redis error retrieving chat history: {error_message}")

        # For other errors, return a 500
        raise HTTPException(
            status_code=500,
            detail=f"Internal server error while querying workflow. {error_message}",
        )

@app.post("/send-prompt")
async def send_prompt(prompt: str):
    print(f"Received prompt {prompt}")

    message = ProcessUserMessageInput(
        user_input = prompt,
    )

    try:
        handle = temporal_client.get_workflow_handle(workflow_id=WORKFLOW_ID)
        await handle.signal(WealthManagementWorkflow.process_user_message,
                            args=[message])
        print(f"Sent message {message}")
        response = "Message sent"
    except RPCError as e:
        response = f"Error: {e}"

    return {"response": response}


@app.post("/end-chat")
async def end_chat():
    """Sends an end_workflow signal to the workflow."""
    try:
        handle = temporal_client.get_workflow_handle(WORKFLOW_ID)
        await handle.signal("end_workflow")
        return {"message": "End chat signal sent."}
    except TemporalError as e:
        print(e)
        # Workflow not found; return an empty response
        return {}

UPDATE_STATUS_NAME = "update_status"

@app.post("/start-workflow")
async def start_workflow(request: Request):
    try:
        # start the workflow
        await temporal_client.start_workflow(
            WealthManagementWorkflow.run,
            args=[],
            id=WORKFLOW_ID,
            task_queue=task_queue,
            id_reuse_policy=WorkflowIDReusePolicy.ALLOW_DUPLICATE
        )

        return {
            "message": f"Workflow started."
        }
    except Exception as e:
        print(f"Exception occurred starting workflow {e}")
        return {
            "message": f"An error occurred starting the workflow {e}"
        }
