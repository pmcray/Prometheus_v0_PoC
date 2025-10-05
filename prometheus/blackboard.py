"""
Blackboard System for Asynchronous Agent Communication
Implements the dynamic event-driven mesh architecture from v0.45
"""

import asyncio
import threading
import time
import uuid
from typing import Dict, List, Any, Optional, Callable, Set
from dataclasses import dataclass, field
from collections import defaultdict
import json
import logging
from concurrent.futures import ThreadPoolExecutor

from .schemas.communication import AgentMessage, MessageType

@dataclass
class BlackboardObject:
    """Structured data object stored on the blackboard"""
    object_id: str
    object_type: str
    data: Dict[str, Any]
    timestamp: float
    created_by: str
    tags: Set[str] = field(default_factory=set)
    dependencies: List[str] = field(default_factory=list)

class EventSubscription:
    """Event subscription for agent listeners"""
    def __init__(self, subscriber_id: str, pattern: str, callback: Callable):
        self.subscriber_id = subscriber_id
        self.pattern = pattern
        self.callback = callback
        self.active = True

class BlackboardSystem:
    """
    Thread-safe, asynchronous blackboard system for agent communication.
    Implements the dynamic mesh architecture from the v0.45 workplan.
    """

    def __init__(self):
        self.objects: Dict[str, BlackboardObject] = {}
        self.subscriptions: Dict[str, List[EventSubscription]] = defaultdict(list)
        self.agent_states: Dict[str, str] = {}
        self.message_history: List[AgentMessage] = []

        # Thread safety
        self.lock = threading.RLock()
        self.executor = ThreadPoolExecutor(max_workers=10)

        # Event loop for async operations
        self.event_loop = None
        self.running = False

        logging.info("BlackboardSystem initialized")

    async def start(self):
        """Start the blackboard event system"""
        self.running = True
        self.event_loop = asyncio.get_event_loop()
        logging.info("BlackboardSystem started")

    async def stop(self):
        """Stop the blackboard system"""
        self.running = False
        self.executor.shutdown(wait=True)
        logging.info("BlackboardSystem stopped")

    def post_object(self, object_type: str, data: Dict[str, Any],
                   created_by: str, tags: Set[str] = None,
                   dependencies: List[str] = None) -> str:
        """
        Post a new object to the blackboard.
        This triggers event notifications to subscribed agents.
        """
        object_id = str(uuid.uuid4())

        with self.lock:
            obj = BlackboardObject(
                object_id=object_id,
                object_type=object_type,
                data=data,
                timestamp=time.time(),
                created_by=created_by,
                tags=tags or set(),
                dependencies=dependencies or []
            )

            self.objects[object_id] = obj

        # Trigger event notifications
        self._notify_subscribers(obj)

        logging.info(f"Object posted: {object_type} by {created_by}")
        return object_id

    def get_object(self, object_id: str) -> Optional[BlackboardObject]:
        """Retrieve object by ID"""
        with self.lock:
            return self.objects.get(object_id)

    def query_objects(self, object_type: str = None, created_by: str = None,
                     tags: Set[str] = None, since: float = None) -> List[BlackboardObject]:
        """Query objects with filters"""
        with self.lock:
            results = []
            for obj in self.objects.values():
                if object_type and obj.object_type != object_type:
                    continue
                if created_by and obj.created_by != created_by:
                    continue
                if tags and not tags.intersection(obj.tags):
                    continue
                if since and obj.timestamp < since:
                    continue
                results.append(obj)

            # Sort by timestamp (newest first)
            results.sort(key=lambda x: x.timestamp, reverse=True)
            return results

    def get_latest_object(self, object_type: str) -> Optional[BlackboardObject]:
        """Get the most recent object of a specific type"""
        objects = self.query_objects(object_type=object_type)
        return objects[0] if objects else None

    def subscribe(self, subscriber_id: str, pattern: str, callback: Callable):
        """
        Subscribe to blackboard events.
        Pattern can be:
        - object_type (e.g., "new_refactoring_task")
        - "new_code_submission"
        - "performance_profile"
        """
        subscription = EventSubscription(subscriber_id, pattern, callback)

        with self.lock:
            self.subscriptions[pattern].append(subscription)

        logging.info(f"Agent {subscriber_id} subscribed to {pattern}")

    def unsubscribe(self, subscriber_id: str, pattern: str = None):
        """Unsubscribe from events"""
        with self.lock:
            if pattern:
                self.subscriptions[pattern] = [
                    sub for sub in self.subscriptions[pattern]
                    if sub.subscriber_id != subscriber_id
                ]
            else:
                # Unsubscribe from all patterns
                for pattern_subs in self.subscriptions.values():
                    pattern_subs[:] = [
                        sub for sub in pattern_subs
                        if sub.subscriber_id != subscriber_id
                    ]

        logging.info(f"Agent {subscriber_id} unsubscribed from {pattern or 'all'}")

    def update_agent_state(self, agent_id: str, state: str):
        """Update agent state (for monitoring)"""
        with self.lock:
            self.agent_states[agent_id] = state

    def get_agent_states(self) -> Dict[str, str]:
        """Get current states of all agents"""
        with self.lock:
            return self.agent_states.copy()

    def post_message(self, message: AgentMessage):
        """Post an agent message to the blackboard"""
        with self.lock:
            self.message_history.append(message)

        # Convert message to blackboard object
        self.post_object(
            object_type=f"message_{message.message_type.value}",
            data=message.payload,
            created_by=message.sender,
            tags={message.recipient, "message"}
        )

    def get_message_history(self, sender: str = None,
                          recipient: str = None,
                          message_type: MessageType = None,
                          limit: int = 100) -> List[AgentMessage]:
        """Get filtered message history"""
        with self.lock:
            filtered = []
            for msg in reversed(self.message_history[-limit:]):
                if sender and msg.sender != sender:
                    continue
                if recipient and msg.recipient != recipient:
                    continue
                if message_type and msg.message_type != message_type:
                    continue
                filtered.append(msg)
            return filtered

    def get_complete_trace(self, run_id: str) -> List[BlackboardObject]:
        """Get complete reasoning trace for a run"""
        return self.query_objects(tags={run_id})

    def _notify_subscribers(self, obj: BlackboardObject):
        """Notify subscribers about new object"""
        if not self.running:
            return

        # Find matching subscriptions
        matching_subs = []

        with self.lock:
            for pattern, subs in self.subscriptions.items():
                if self._pattern_matches(pattern, obj):
                    matching_subs.extend([s for s in subs if s.active])

        # Execute callbacks asynchronously
        for subscription in matching_subs:
            self.executor.submit(self._safe_callback, subscription, obj)

    def _pattern_matches(self, pattern: str, obj: BlackboardObject) -> bool:
        """Check if object matches subscription pattern"""
        # Direct object type match
        if pattern == obj.object_type:
            return True

        # Tag-based matching
        if pattern in obj.tags:
            return True

        # Special patterns
        if pattern == "all":
            return True

        return False

    def _safe_callback(self, subscription: EventSubscription, obj: BlackboardObject):
        """Safely execute subscription callback"""
        try:
            subscription.callback(obj)
        except Exception as e:
            logging.error(f"Error in subscription callback for {subscription.subscriber_id}: {e}")
            # Deactivate problematic subscription
            subscription.active = False

    def get_system_metrics(self) -> Dict[str, Any]:
        """Get blackboard system metrics"""
        with self.lock:
            return {
                "total_objects": len(self.objects),
                "active_agents": len(self.agent_states),
                "total_subscriptions": sum(len(subs) for subs in self.subscriptions.values()),
                "message_count": len(self.message_history),
                "object_types": list(set(obj.object_type for obj in self.objects.values())),
                "uptime_seconds": time.time() - (min(obj.timestamp for obj in self.objects.values()) if self.objects else time.time())
            }

    def export_state(self) -> Dict[str, Any]:
        """Export current blackboard state (for debugging/analysis)"""
        with self.lock:
            return {
                "objects": {
                    obj_id: {
                        "object_type": obj.object_type,
                        "data": obj.data,
                        "timestamp": obj.timestamp,
                        "created_by": obj.created_by,
                        "tags": list(obj.tags)
                    } for obj_id, obj in self.objects.items()
                },
                "agent_states": self.agent_states.copy(),
                "metrics": self.get_system_metrics()
            }

# Global blackboard instance
blackboard = BlackboardSystem()

class AgentBase:
    """
    Base class for agents using the blackboard system.
    Provides common functionality for event-driven operation.
    """

    def __init__(self, agent_id: str):
        self.agent_id = agent_id
        self.blackboard = blackboard
        self.subscriptions: List[str] = []

    def subscribe_to_events(self, patterns: List[str]):
        """Subscribe to blackboard events"""
        for pattern in patterns:
            self.blackboard.subscribe(self.agent_id, pattern, self._handle_event)
            self.subscriptions.append(pattern)

    def _handle_event(self, obj: BlackboardObject):
        """Handle blackboard events (to be overridden by subclasses)"""
        self.blackboard.update_agent_state(self.agent_id, f"processing_{obj.object_type}")

        try:
            result = self.process_event(obj)
            if result:
                self.blackboard.post_object(**result)
        except Exception as e:
            logging.error(f"Error processing event in {self.agent_id}: {e}")
        finally:
            self.blackboard.update_agent_state(self.agent_id, "idle")

    def process_event(self, obj: BlackboardObject) -> Optional[Dict[str, Any]]:
        """Process blackboard event (to be implemented by subclasses)"""
        raise NotImplementedError

    def cleanup(self):
        """Clean up agent subscriptions"""
        for pattern in self.subscriptions:
            self.blackboard.unsubscribe(self.agent_id, pattern)