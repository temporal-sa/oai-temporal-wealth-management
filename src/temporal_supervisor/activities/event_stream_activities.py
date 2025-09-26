from temporalio import activity
from temporalio.workflow import logger

from common.event_stream_manager import EventStreamManager, EventType
from common.user_message import ChatInteraction
from common.status_update import StatusUpdate

class EventStreamActivities:
    """
    Activities for event stream operations.
    
    These are lightweight operations for Redis-based event streaming.
    """
    
    @staticmethod
    @activity.defn
    async def append_chat_interaction(workflow_id: str, chat_interaction: ChatInteraction) -> int:
        """Append a chat interaction to the event stream"""
        manager = EventStreamManager()
        try:
            sequence = await manager.append_chat_interaction(
                workflow_id=workflow_id,
                chat_interaction=chat_interaction
            )
            activity.logger.info(f"Appended chat interaction to stream {workflow_id}, sequence {sequence}")
            return sequence
        finally:
            await manager.close()
    
    @staticmethod
    @activity.defn
    async def append_status_update(workflow_id: str, status_update: StatusUpdate) -> int:
        """Append a status update to the event stream"""
        manager = EventStreamManager()
        try:
            sequence = await manager.append_status_update(
                workflow_id=workflow_id,
                status_update=status_update
            )
            activity.logger.info(f"Appended status update to stream {workflow_id}, sequence {sequence}")
            return sequence
        finally:
            await manager.close()
    

    @staticmethod
    @activity.defn
    async def delete_conversation(workflow_id: str) -> bool:
        """Delete the conversation for a workflow"""
        manager = EventStreamManager()
        try:
            return await manager.delete_stream(workflow_id)
        finally:
            await manager.close()