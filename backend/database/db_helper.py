import os
import json
import re
import asyncpg
from typing import Optional, Any
from datetime import datetime

class DatabaseHelper:
    def __init__(self):
        self.pool: Optional[asyncpg.Pool] = None

    async def connect(self):
        if not self.pool:
            self.pool = await asyncpg.create_pool(
                host=os.getenv("POSTGRES_HOST", "localhost"),
                port=os.getenv("POSTGRES_PORT", "5432"),
                user=os.getenv("POSTGRES_USER", "postgres"),
                password=os.getenv("POSTGRES_PASSWORD"),
                database=os.getenv("POSTGRES_DATABASE", "security_db")
            )

    async def disconnect(self):
        if self.pool:
            await self.pool.close()
            self.pool = None

    def mask_sensitive_data(self, data: Any) -> Any:
        if isinstance(data, str):
            # Mask IPv4
            data = re.sub(r'\b(\d{1,3}\.\d{1,3}\.\d{1,3}\.)\d{1,3}\b', r'\1***', data)
            # Mask Email
            data = re.sub(r'\b([a-zA-Z0-9._%+-])[a-zA-Z0-9._%+-]*@([a-zA-Z0-9.-]+\.[a-zA-Z]{2,})\b', r'\1***@\2', data)
            # Mask API Keys (AIza)
            data = re.sub(r'(AIza[a-zA-Z0-9_-]{4})[a-zA-Z0-9_-]+', r'\1***', data)
            return data
        elif isinstance(data, dict):
            return {k: self.mask_sensitive_data(v) for k, v in data.items()}
        elif isinstance(data, list):
            return [self.mask_sensitive_data(v) for v in data]
        return data

    async def log_audit(self, username: str, action: str, request_data: Optional[dict] = None, response_summary: Optional[str] = None):
        if not self.pool:
            await self.connect()
        
        masked_request = self.mask_sensitive_data(request_data) if request_data else None
        masked_response = self.mask_sensitive_data(response_summary) if response_summary else None
        
        async with self.pool.acquire() as conn:
            await conn.execute(
                "INSERT INTO audit_logs (username, action, request_data, response_summary) VALUES ($1, $2, $3, $4)",
                username, action, json.dumps(masked_request) if masked_request else None, masked_response
            )

    async def get_cached_indicator(self, indicator: str) -> Optional[dict]:
        if not self.pool:
            await self.connect()
        
        async with self.pool.acquire() as conn:
            row = await conn.fetchrow(
                "SELECT cached_result FROM knowledge_cache WHERE indicator = $1 AND updated_at > NOW() - INTERVAL '24 hours'",
                indicator
            )
            return json.loads(row['cached_result']) if row else None

    async def cache_indicator(self, indicator: str, indicator_type: str, result: dict):
        if not self.pool:
            await self.connect()
        
        async with self.pool.acquire() as conn:
            await conn.execute(
                "INSERT INTO knowledge_cache (indicator, indicator_type, cached_result, updated_at) VALUES ($1, $2, $3, CURRENT_TIMESTAMP) "
                "ON CONFLICT (indicator) DO UPDATE SET cached_result = EXCLUDED.cached_result, updated_at = EXCLUDED.updated_at",
                indicator, indicator_type, json.dumps(result)
            )

    async def get_user_tabs(self, username: str):
        if not self.pool:
            await self.connect()
        
        async with self.pool.acquire() as conn:
            rows = await conn.fetch(
                "SELECT id, title, query_state, is_active FROM user_active_queries WHERE username = $1 AND is_active = TRUE ORDER BY created_at",
                username
            )
            return [dict(r) for r in rows]

    async def save_user_tab(self, username: str, title: str, query_state: dict, tab_id: Optional[str] = None):
        if not self.pool:
            await self.connect()
        
        async with self.pool.acquire() as conn:
            if tab_id:
                await conn.execute(
                    "UPDATE user_active_queries SET title = $1, query_state = $2 WHERE id = $3 AND username = $4",
                    title, json.dumps(query_state), tab_id, username
                )
                return tab_id
            else:
                row = await conn.fetchrow(
                    "INSERT INTO user_active_queries (username, title, query_state) VALUES ($1, $2, $3) RETURNING id",
                    username, title, json.dumps(query_state)
                )
                return str(row['id'])

    async def close_user_tab(self, username: str, tab_id: str):
        if not self.pool:
            await self.connect()
        
        async with self.pool.acquire() as conn:
            await conn.execute(
                "UPDATE user_active_queries SET is_active = FALSE WHERE id = $1 AND username = $2",
                tab_id, username
            )

# Global helper instance
db = DatabaseHelper()
