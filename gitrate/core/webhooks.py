"""Webhook handlers for GitHub and GitLab event-driven audits."""

import logging
import hmac
import hashlib
from typing import Dict, Any, Optional
from datetime import datetime
from enum import Enum

from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)


class WebhookEventType(str, Enum):
    """Supported webhook event types."""
    PUSH = "push"
    PULL_REQUEST = "pull_request"
    RELEASE = "release"
    COMMIT_COMMENT = "commit_comment"


class GitHubWebhookPayload(BaseModel):
    """GitHub webhook payload model."""
    action: Optional[str] = None
    number: Optional[int] = None
    pull_request: Optional[Dict[str, Any]] = None
    repository: Dict[str, Any]
    pusher: Optional[Dict[str, Any]] = None
    ref: Optional[str] = None
    
    class Config:
        extra = "allow"


class GitLabWebhookPayload(BaseModel):
    """GitLab webhook payload model."""
    event_name: str
    action: Optional[str] = None
    project: Dict[str, Any]
    object_kind: str
    ref: Optional[str] = None
    
    class Config:
        extra = "allow"


class WebhookEvent(BaseModel):
    """Normalized webhook event."""
    event_type: WebhookEventType
    source: str  # "github" or "gitlab"
    owner: str
    repo: str
    ref: Optional[str] = None
    action: Optional[str] = None
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    payload: Dict[str, Any]


class WebhookValidator:
    """Validate webhook signatures."""
    
    @staticmethod
    def validate_github_signature(payload_bytes: bytes, 
                                  signature: str,
                                  secret: str) -> bool:
        """Validate GitHub webhook signature.
        
        Args:
            payload_bytes: Raw request body
            signature: X-Hub-Signature-256 header value
            secret: Webhook secret
        
        Returns:
            True if signature is valid
        """
        try:
            expected_signature = "sha256=" + hmac.new(
                secret.encode(),
                payload_bytes,
                hashlib.sha256
            ).hexdigest()
            
            # Constant-time comparison
            return hmac.compare_digest(signature, expected_signature)
        except Exception as e:
            logger.error(f"Signature validation error: {e}")
            return False
    
    @staticmethod
    def validate_gitlab_signature(payload_bytes: bytes,
                                 signature: str,
                                 secret: str) -> bool:
        """Validate GitLab webhook signature.
        
        Args:
            payload_bytes: Raw request body
            signature: X-Gitlab-Token header value
            secret: Webhook secret
        
        Returns:
            True if signature is valid
        """
        try:
            expected_signature = hmac.new(
                secret.encode(),
                payload_bytes,
                hashlib.sha256
            ).hexdigest()
            
            # Constant-time comparison
            return hmac.compare_digest(signature, expected_signature)
        except Exception as e:
            logger.error(f"Signature validation error: {e}")
            return False


class GitHubWebhookHandler:
    """Handle GitHub webhook events."""
    
    @staticmethod
    def parse_payload(payload: GitHubWebhookPayload) -> Optional[WebhookEvent]:
        """Parse GitHub webhook payload.
        
        Args:
            payload: GitHub webhook payload
        
        Returns:
            Normalized WebhookEvent or None if not relevant
        """
        try:
            repo_data = payload.repository
            owner = repo_data["owner"]["login"]
            repo = repo_data["name"]
            
            # Determine event type
            event_type = None
            ref = None
            action = None
            
            if payload.pull_request:
                event_type = WebhookEventType.PULL_REQUEST
                action = payload.action
                ref = payload.pull_request.get("head", {}).get("ref")
            
            elif "release" in payload.__fields_set__:
                event_type = WebhookEventType.RELEASE
                action = payload.action
            
            elif payload.ref:
                event_type = WebhookEventType.PUSH
                ref = payload.ref
            
            else:
                logger.debug(f"Unknown GitHub event type from {owner}/{repo}")
                return None
            
            logger.info(f"GitHub webhook: {event_type.value} on {owner}/{repo}")
            
            return WebhookEvent(
                event_type=event_type,
                source="github",
                owner=owner,
                repo=repo,
                ref=ref,
                action=action,
                payload=payload.dict()
            )
        
        except Exception as e:
            logger.error(f"Error parsing GitHub webhook: {e}", exc_info=True)
            return None


class GitLabWebhookHandler:
    """Handle GitLab webhook events."""
    
    @staticmethod
    def parse_payload(payload: GitLabWebhookPayload) -> Optional[WebhookEvent]:
        """Parse GitLab webhook payload.
        
        Args:
            payload: GitLab webhook payload
        
        Returns:
            Normalized WebhookEvent or None if not relevant
        """
        try:
            project = payload.project
            owner = project.get("namespace", {}).get("name") or "unknown"
            repo = project.get("name", "unknown")
            
            # Map GitLab object_kind to event type
            event_type = None
            ref = payload.ref
            action = payload.action
            
            if payload.object_kind == "push":
                event_type = WebhookEventType.PUSH
            elif payload.object_kind == "merge_request":
                event_type = WebhookEventType.PULL_REQUEST
            elif payload.object_kind == "release":
                event_type = WebhookEventType.RELEASE
            else:
                logger.debug(f"Unsupported GitLab event: {payload.object_kind}")
                return None
            
            logger.info(f"GitLab webhook: {event_type.value} on {owner}/{repo}")
            
            return WebhookEvent(
                event_type=event_type,
                source="gitlab",
                owner=owner,
                repo=repo,
                ref=ref,
                action=action,
                payload=payload.dict()
            )
        
        except Exception as e:
            logger.error(f"Error parsing GitLab webhook: {e}", exc_info=True)
            return None


class WebhookEventQueue:
    """Queue webhook events for processing."""
    
    def __init__(self):
        """Initialize event queue."""
        self.events: list[Dict[str, Any]] = []
        self.processed: list[Dict[str, Any]] = []
    
    def enqueue(self, event: WebhookEvent) -> str:
        """Add event to queue.
        
        Args:
            event: Webhook event
        
        Returns:
            Event ID
        """
        event_id = f"webhook_{len(self.events):06d}"
        
        event_data = {
            "event_id": event_id,
            "event": event,
            "enqueued_at": datetime.utcnow(),
            "processed_at": None,
            "status": "PENDING",
        }
        
        self.events.append(event_data)
        logger.debug(f"Queued webhook event: {event_id}")
        
        return event_id
    
    def dequeue(self) -> Optional[WebhookEvent]:
        """Get next event from queue.
        
        Returns:
            Webhook event or None
        """
        if self.events:
            event_data = self.events.pop(0)
            return event_data["event"]
        return None
    
    def mark_processed(self, event_id: str, success: bool = True,
                      error: Optional[str] = None) -> None:
        """Mark event as processed.
        
        Args:
            event_id: Event ID
            success: Whether processing succeeded
            error: Optional error message
        """
        for event_data in self.events + self.processed:
            if event_data.get("event_id") == event_id:
                event_data["processed_at"] = datetime.utcnow()
                event_data["status"] = "SUCCESS" if success else "FAILED"
                event_data["error"] = error
                logger.info(f"Marked webhook event processed: {event_id}")
                return
    
    def get_pending_count(self) -> int:
        """Get number of pending events.
        
        Returns:
            Count
        """
        return len(self.events)
    
    def get_queue_status(self) -> Dict[str, Any]:
        """Get queue status.
        
        Returns:
            Status dict
        """
        return {
            "pending": len(self.events),
            "processed": len(self.processed),
            "events": [
                {
                    "event_id": e["event_id"],
                    "repository": f"{e['event'].owner}/{e['event'].repo}",
                    "event_type": e["event"].event_type.value,
                    "enqueued_at": e["enqueued_at"].isoformat(),
                }
                for e in self.events
            ]
        }


# Global webhook event queue
webhook_queue = WebhookEventQueue()
