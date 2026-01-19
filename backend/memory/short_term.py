import redis
import json
from typing import List, Dict, Any, Optional
from datetime import timedelta
from backend.config import settings


class ShortTermMemory:
    def __init__(self):
        try:
            self.redis_client = redis.from_url(settings.REDIS_URL, decode_responses=True)
            self.redis_client.ping()
            self.redis_available = True
        except (redis.ConnectionError, redis.RedisError):
            self.redis_client = None
            self.redis_available = False
            self._fallback_storage = {}
        self.default_ttl = 3600
    
    def _get_session_key(self, session_id: str) -> str:
        return f"session:{session_id}"
    
    def _get_context_key(self, session_id: str) -> str:
        return f"context:{session_id}"
    
    def save_message(self, session_id: str, role: str, content: str, metadata: Optional[Dict[str, Any]] = None):
        key = self._get_session_key(session_id)
        message = {
            "role": role,
            "content": content,
            "metadata": metadata or {}
        }
        
        if self.redis_available:
            self.redis_client.rpush(key, json.dumps(message))
            self.redis_client.expire(key, self.default_ttl)
        else:
            if key not in self._fallback_storage:
                self._fallback_storage[key] = []
            self._fallback_storage[key].append(message)
    
    def get_messages(self, session_id: str, limit: Optional[int] = None) -> List[Dict[str, Any]]:
        key = self._get_session_key(session_id)
        
        if self.redis_available:
            messages = self.redis_client.lrange(key, 0, -1)
            parsed_messages = [json.loads(msg) for msg in messages]
        else:
            parsed_messages = self._fallback_storage.get(key, [])
        
        if limit:
            return parsed_messages[-limit:]
        return parsed_messages
    
    def save_context(self, session_id: str, context: Dict[str, Any]):
        key = self._get_context_key(session_id)
        if self.redis_available:
            self.redis_client.set(key, json.dumps(context), ex=self.default_ttl)
        else:
            self._fallback_storage[key] = context
    
    def get_context(self, session_id: str) -> Dict[str, Any]:
        key = self._get_context_key(session_id)
        if self.redis_available:
            context = self.redis_client.get(key)
            return json.loads(context) if context else {}
        else:
            return self._fallback_storage.get(key, {})
    
    def update_context(self, session_id: str, updates: Dict[str, Any]):
        current_context = self.get_context(session_id)
        current_context.update(updates)
        self.save_context(session_id, current_context)
    
    def clear_session(self, session_id: str):
        if self.redis_available:
            self.redis_client.delete(self._get_session_key(session_id))
            self.redis_client.delete(self._get_context_key(session_id))
        else:
            self._fallback_storage.pop(self._get_session_key(session_id), None)
            self._fallback_storage.pop(self._get_context_key(session_id), None)
    
    def extend_session(self, session_id: str, ttl: Optional[int] = None):
        if self.redis_available:
            ttl = ttl or self.default_ttl
            self.redis_client.expire(self._get_session_key(session_id), ttl)
            self.redis_client.expire(self._get_context_key(session_id), ttl)
    
    def get_recent_topics(self, session_id: str, limit: int = 5) -> List[str]:
        messages = self.get_messages(session_id, limit=limit * 2)
        topics = []
        for msg in messages:
            if msg.get("metadata", {}).get("topic"):
                topics.append(msg["metadata"]["topic"])
        return list(set(topics))[-limit:]
