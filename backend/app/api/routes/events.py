import asyncio
import json
from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Depends, Query
from sqlalchemy.orm import Session
from app.api.deps import get_current_user
from app.models.user import User
from app.services.event_service import redis_client
from app.core.logging import logger

router = APIRouter(prefix="/ws", tags=["events"])

class ConnectionManager:
    def __init__(self):
        self.active_connections: dict[int, list[WebSocket]] = {}

    async def add_to_active(self, websocket: WebSocket, user_id: int):
        if user_id not in self.active_connections:
            self.active_connections[user_id] = []
        self.active_connections[user_id].append(websocket)
        logger.info(f"User {user_id} added to telemetry stream. Total connections: {len(self.active_connections[user_id])}")

    def disconnect(self, websocket: WebSocket, user_id: int):
        if user_id in self.active_connections:
            self.active_connections[user_id].remove(websocket)
            if not self.active_connections[user_id]:
                del self.active_connections[user_id]
        logger.info(f"User {user_id} disconnected from telemetry stream.")

manager = ConnectionManager()

@router.websocket("/telemetry")
async def websocket_endpoint(
    websocket: WebSocket,
    token: str = Query(...)
):
    await websocket.accept()
    
    # Verify token manually
    from app.services.auth_service import AuthService
    from app.core.database import SessionLocal
    
    db = SessionLocal()
    try:
        user_id = AuthService.verify_access_token(token)
        if not user_id:
            logger.warning(f"WebSocket connection rejected: Invalid or missing token")
            await websocket.close(code=1008) # Policy Violation
            return
            
        await manager.add_to_active(websocket, int(user_id))
        
        # Start a listener for Redis Pub/Sub for this user
        pubsub = redis_client.pubsub()
        pubsub.subscribe(f"user_events:{user_id}", "system_events")
        
        try:
            while True:
                # Check for Redis messages
                message = pubsub.get_message(ignore_subscribe_messages=True)
                if message:
                    await websocket.send_text(message['data'])
                
                # Also keep the connection alive/check for client disconnect
                # Using wait_for to prevent blocking forever if no Redis messages
                try:
                    # We don't expect client messages, but this detects closed socket
                    await asyncio.wait_for(websocket.receive_text(), timeout=0.1)
                except asyncio.TimeoutError:
                    pass
                
        except WebSocketDisconnect:
            manager.disconnect(websocket, int(user_id))
        except Exception as e:
            logger.error(f"WebSocket error for user {user_id}: {e}")
            manager.disconnect(websocket, int(user_id))
        finally:
            pubsub.unsubscribe()
            pubsub.close()
            
    finally:
        db.close()

from app.models.event import SystemEvent
from app.core.database import get_db

@router.get("/history")
async def get_event_history(
    limit: int = 50,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    events = db.query(SystemEvent).filter(
        SystemEvent.user_id == current_user.id
    ).order_by(SystemEvent.timestamp.desc()).limit(limit).all()
    
    return [
        {
            "event_id": e.event_id,
            "type": e.event_type,
            "payload": e.payload,
            "resource_id": e.resource_id,
            "timestamp": e.timestamp.isoformat()
        } for e in events
    ]
