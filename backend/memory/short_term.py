import redis
import json
import logging
from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta
from threading import Lock
from backend.config import settings

logger = logging.getLogger(__name__)


class ShortTermMemory:
    def __init__(self):
        self._lock = Lock()
        try:
            self.redis_client = redis.from_url(settings.REDIS_URL, decode_responses=True)
            self.redis_client.ping()
            self.redis_available = True
            logger.info("Redis connection established successfully")
        except (redis.ConnectionError, redis.RedisError) as e:
            self.redis_client = None
            self.redis_available = False
            self._fallback_storage = {}
            self._fallback_expiry = {}
            logger.warning(f"Redis unavailable, using fallback storage: {str(e)}")
        self.default_ttl = 3600
    
    def _get_session_key(self, session_id: str) -> str:
        return f"session:{session_id}"
    
    def _get_context_key(self, session_id: str) -> str:
        return f"context:{session_id}"
    
    def _is_expired(self, key: str) -> bool:
        """Check if a fallback storage key has expired."""
        if key not in self._fallback_expiry:
            return False
        return datetime.now() > self._fallback_expiry[key]
    
    def _set_expiry(self, key: str, ttl: int):
        """Set expiry time for a fallback storage key."""
        self._fallback_expiry[key] = datetime.now() + timedelta(seconds=ttl)
    
    def _cleanup_expired(self):
        """Remove expired entries from fallback storage."""
        if not self.redis_available:
            expired_keys = [k for k in self._fallback_storage.keys() if self._is_expired(k)]
            for key in expired_keys:
                del self._fallback_storage[key]
                del self._fallback_expiry[key]
            if expired_keys:
                logger.debug(f"Cleaned up {len(expired_keys)} expired fallback entries")
    
    def save_message(self, session_id: str, role: str, content: str, metadata: Optional[Dict[str, Any]] = None):
        key = self._get_session_key(session_id)
        message = {
            "role": role,
            "content": content,
            "metadata": metadata or {},
            "timestamp": datetime.now().isoformat()
        }
        
        if self.redis_available:
            try:
                self.redis_client.rpush(key, json.dumps(message))
                self.redis_client.expire(key, self.default_ttl)
            except redis.RedisError as e:
                logger.error(f"Redis error while saving message: {e}")
                self._switch_to_fallback()
                self.save_message(session_id, role, content, metadata)
        else:
            with self._lock:
                self._cleanup_expired()
                if key not in self._fallback_storage:
                    self._fallback_storage[key] = []
                self._fallback_storage[key].append(message)
                self._set_expiry(key, self.default_ttl)
                logger.debug(f"Saved message to fallback storage for session {session_id}")
    
    def get_messages(self, session_id: str, limit: Optional[int] = None) -> List[Dict[str, Any]]:
        key = self._get_session_key(session_id)
        
        if self.redis_available:
            try:
                messages = self.redis_client.lrange(key, 0, -1)
                parsed_messages = [json.loads(msg) for msg in messages]
            except redis.RedisError as e:
                logger.error(f"Redis error while getting messages: {e}")
                self._switch_to_fallback()
                return self.get_messages(session_id, limit)
        else:
            with self._lock:
                self._cleanup_expired()
                if self._is_expired(key):
                    return []
                parsed_messages = self._fallback_storage.get(key, [])
        
        if limit:
            return parsed_messages[-limit:]
        return parsed_messages
    
    def save_context(self, session_id: str, context: Dict[str, Any]):
        key = self._get_context_key(session_id)
        context_with_meta = {
            **context,
            "_saved_at": datetime.now().isoformat()
        }
        
        if self.redis_available:
            try:
                self.redis_client.set(key, json.dumps(context_with_meta), ex=self.default_ttl)
            except redis.RedisError as e:
                logger.error(f"Redis error while saving context: {e}")
                self._switch_to_fallback()
                self.save_context(session_id, context)
        else:
            with self._lock:
                self._cleanup_expired()
                self._fallback_storage[key] = context_with_meta
                self._set_expiry(key, self.default_ttl)
    
    def get_context(self, session_id: str) -> Dict[str, Any]:
        key = self._get_context_key(session_id)
        
        if self.redis_available:
            try:
                context = self.redis_client.get(key)
                result = json.loads(context) if context else {}
            except redis.RedisError as e:
                logger.error(f"Redis error while getting context: {e}")
                self._switch_to_fallback()
                return self.get_context(session_id)
        else:
            with self._lock:
                self._cleanup_expired()
                if self._is_expired(key):
                    return {}
                result = self._fallback_storage.get(key, {})
        
        result.pop("_saved_at", None)
        return result
    
    def update_context(self, session_id: str, updates: Dict[str, Any]):
        current_context = self.get_context(session_id)
        current_context.update(updates)
        self.save_context(session_id, current_context)
    
    def clear_session(self, session_id: str):
        session_key = self._get_session_key(session_id)
        context_key = self._get_context_key(session_id)
        
        if self.redis_available:
            try:
                self.redis_client.delete(session_key, context_key)
                logger.info(f"Cleared session {session_id} from Redis")
            except redis.RedisError as e:
                logger.error(f"Redis error while clearing session: {e}")
                self._switch_to_fallback()
                self.clear_session(session_id)
        else:
            with self._lock:
                self._fallback_storage.pop(session_key, None)
                self._fallback_storage.pop(context_key, None)
                self._fallback_expiry.pop(session_key, None)
                self._fallback_expiry.pop(context_key, None)
                logger.info(f"Cleared session {session_id} from fallback storage")
    
    def extend_session(self, session_id: str, ttl: Optional[int] = None):
        ttl = ttl or self.default_ttl
        session_key = self._get_session_key(session_id)
        context_key = self._get_context_key(session_id)
        
        if self.redis_available:
            try:
                self.redis_client.expire(session_key, ttl)
                self.redis_client.expire(context_key, ttl)
            except redis.RedisError as e:
                logger.error(f"Redis error while extending session: {e}")
                self._switch_to_fallback()
                self.extend_session(session_id, ttl)
        else:
            with self._lock:
                if session_key in self._fallback_storage:
                    self._set_expiry(session_key, ttl)
                if context_key in self._fallback_storage:
                    self._set_expiry(context_key, ttl)
    
    def get_recent_topics(self, session_id: str, limit: int = 5) -> List[str]:
        messages = self.get_messages(session_id, limit=limit * 2)
        topics = []
        for msg in messages:
            if msg.get("metadata", {}).get("topic"):
                topics.append(msg["metadata"]["topic"])
        return list(set(topics))[-limit:]
    
    def _switch_to_fallback(self):
        """Switch from Redis to fallback storage mode."""
        if self.redis_available:
            logger.warning("Switching to fallback storage due to Redis errors")
            self.redis_available = False
            self.redis_client = None
            if not hasattr(self, '_fallback_storage'):
                self._fallback_storage = {}
                self._fallback_expiry = {}
    
    def get_storage_stats(self) -> Dict[str, Any]:
        """Get statistics about the current storage."""
        if self.redis_available:
            try:
                info = self.redis_client.info('memory')
                return {
                    "mode": "redis",
                    "available": True,
                    "memory_used": info.get('used_memory_human', 'N/A')
                }
            except redis.RedisError:
                self._switch_to_fallback()
                return self.get_storage_stats()
        else:
            with self._lock:
                self._cleanup_expired()
                return {
                    "mode": "fallback",
                    "available": False,
                    "active_sessions": len(set(k.split(':')[1] for k in self._fallback_storage.keys() if ':' in k)),
                    "total_keys": len(self._fallback_storage),
                    "expired_keys": sum(1 for k in self._fallback_storage.keys() if self._is_expired(k))
                }
