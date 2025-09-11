import json
import time
import os
from typing import List, Dict, Any, Union
from enum import Enum
from dataclasses import asdict

import redis.asyncio as redis

from .user_message import ChatInteraction
from .status_update import StatusUpdate

class EventType(str, Enum):
    """Event types for the chat event stream"""
    CHAT_INTERACTION = "chat_interaction"
    STATUS_UPDATE = "status_update"

class EventStreamManager:
    """
    Manages a Redis list-based event stream for chat conversations.
    
    Uses LPUSH for O(1) appends and LRANGE for efficient range queries.
    Each event has an implicit sequence number based on its position in the list.
    """
    
    def __init__(self, redis_host: str = None, redis_port: int = None):
        self.redis_host = redis_host or os.getenv("REDIS_HOST", "localhost")
        self.redis_port = redis_port or int(os.getenv("REDIS_PORT", "6379"))
        self.redis_client = redis.Redis(
            host=self.redis_host, 
            port=self.redis_port,
            decode_responses=True
        )
    
    def _get_stream_key(self, workflow_id: str) -> str:
        """Get the Redis key for the event stream"""
        return f"events:{workflow_id}"
    
    def _get_meta_key(self, workflow_id: str) -> str:
        """Get the Redis key for stream metadata"""
        return f"events:{workflow_id}:meta"
        
    async def append_chat_interaction(
        self, 
        workflow_id: str, 
        chat_interaction: ChatInteraction
    ) -> int:
        """
        Append a chat interaction to the stream.
        
        Returns the new total length of the event stream.
        """
        return await self._append_domain_event(
            workflow_id, 
            EventType.CHAT_INTERACTION, 
            chat_interaction
        )
    
    async def append_status_update(
        self, 
        workflow_id: str, 
        status_update: StatusUpdate
    ) -> int:
        """
        Append a status update to the stream.
        
        Returns the new total length of the event stream.
        """
        return await self._append_domain_event(
            workflow_id, 
            EventType.STATUS_UPDATE, 
            status_update
        )
    
    async def _append_domain_event(
        self, 
        workflow_id: str, 
        event_type: EventType, 
        domain_object: Union[ChatInteraction, StatusUpdate]
    ) -> int:
        """
        Internal method to append domain objects to the stream.
        
        Returns the new total length of the event stream.
        """
        stream_key = self._get_stream_key(workflow_id)
        
        # Convert domain object to dict
        content_dict = asdict(domain_object)
        
        # Build the event with structured content
        event = {
            "type": event_type.value,
            "content": content_dict
        }
        
        event_json = json.dumps(event)
        
        # Use RPUSH to add to the end (chronological order)
        # RPUSH returns the new length of the list after insertion
        new_length = await self.redis_client.rpush(stream_key, event_json)
        
        return new_length
    
    async def get_events_from_index(
        self, 
        workflow_id: str, 
        from_index: int = 0
    ) -> List[Dict[str, Any]]:
        """
        Get events starting from a specific index.
        
        Args:
            workflow_id: The workflow ID
            from_index: Start from this index (0-based)
            
        Returns:
            List of events in chronological order
        """
        stream_key = self._get_stream_key(workflow_id)
        
        # Get all events from the specified index to the end
        event_strings = await self.redis_client.lrange(stream_key, from_index, -1)
        
        # Parse events
        events = []
        for event_str in event_strings:
            try:
                event = json.loads(event_str)
                events.append(event)
            except json.JSONDecodeError:
                continue  # Skip malformed events
        
        return events
    
    async def get_all_events(self, workflow_id: str) -> List[Dict[str, Any]]:
        """
        Get all events in the stream.
        
        Returns events in chronological order.
        """
        stream_key = self._get_stream_key(workflow_id)
        
        # Get all events
        event_strings = await self.redis_client.lrange(stream_key, 0, -1)
        
        # Parse events (already in chronological order due to RPUSH)
        events = []
        for event_str in event_strings:
            try:
                events.append(json.loads(event_str))
            except json.JSONDecodeError:
                continue  # Skip malformed events
        
        return events
    
    async def get_total_events(self, workflow_id: str) -> int:
        """Get the total number of events in the stream"""
        stream_key = self._get_stream_key(workflow_id)
        return await self.redis_client.llen(stream_key)
    
    async def delete_stream(self, workflow_id: str) -> bool:
        """
        Delete the entire event stream for a workflow.
        
        Returns True if the stream was deleted, False if it didn't exist.
        """
        stream_key = self._get_stream_key(workflow_id)
        meta_key = self._get_meta_key(workflow_id)
        
        # Delete both the stream and metadata
        deleted = await self.redis_client.delete(stream_key, meta_key)
        
        return deleted > 0
    
    async def close(self):
        """Close the Redis connection"""
        await self.redis_client.aclose()
