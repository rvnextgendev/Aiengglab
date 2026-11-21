"""Redis-backed circuit breaker with atomic Lua state transitions.

Uses Redis server time for expiry and leases. Fail closed if Redis is unavailable.
Each provider has its own shared key; probe reservation is atomic.
"""
from __future__ import annotations
import os
import uuid
from redis import Redis
from app.reliability.resilience import CircuitOpen

_BEFORE = """
local now=tonumber(redis.call('TIME')[1])
local opened=tonumber(redis.call('HGET',KEYS[1],'opened') or '0')
local probe=redis.call('HGET',KEYS[1],'probe')
if opened>0 and now-opened<tonumber(ARGV[1]) then return 0 end
if opened>0 then
  if probe then return 0 end
  redis.call('HSET',KEYS[1],'probe',ARGV[2])
  redis.call('EXPIRE',KEYS[1],tonumber(ARGV[3]))
  return 2
end
return 1
"""
_SUCCESS = """
if ARGV[1] ~= '' and redis.call('HGET',KEYS[1],'probe') ~= ARGV[1] then return 0 end
redis.call('DEL',KEYS[1])
return 1
"""
_FAILURE = """
if ARGV[1] ~= '' and redis.call('HGET',KEYS[1],'probe') ~= ARGV[1] then return 0 end
local count=redis.call('HINCRBY',KEYS[1],'failures',1)
redis.call('HDEL',KEYS[1],'probe')
if count>=tonumber(ARGV[2]) then redis.call('HSET',KEYS[1],'opened',tonumber(redis.call('TIME')[1])) end
redis.call('EXPIRE',KEYS[1],tonumber(ARGV[3]))
return count
"""
_RELEASE = """
if redis.call('HGET',KEYS[1],'probe') == ARGV[1] then
 redis.call('HDEL',KEYS[1],'probe')
 return 1
end
return 0
"""

class SharedCircuitBreaker:
    def __init__(self, provider: str, *, redis_client=None, threshold=5, recovery_seconds=30):
        if provider not in ("ollama", "openai-compatible") or threshold < 1 or recovery_seconds < 1:
            raise ValueError("Invalid circuit breaker settings")
        self.redis = redis_client or Redis.from_url(os.getenv("REDIS_URL", "redis://localhost:6379/0"),
                                                     socket_connect_timeout=2, socket_timeout=2)
        self.key = "arinova:circuit:" + provider
        self.threshold = threshold
        self.recovery = int(recovery_seconds)
        self.ttl = max(60, self.recovery * 3)
        self._token = ""

    def before_call(self):
        token = uuid.uuid4().hex
        outcome = int(self.redis.eval(_BEFORE, 1, self.key, self.recovery, token, self.ttl))
        if outcome == 0:
            raise CircuitOpen("Shared provider circuit open")
        self._token = token if outcome == 2 else ""

    def success(self):
        self.redis.eval(_SUCCESS, 1, self.key, self._token)
        self._token = ""

    def failure(self):
        self.redis.eval(_FAILURE, 1, self.key, self._token, self.threshold, self.ttl)
        self._token = ""

    def release_probe(self):
        if self._token:
            self.redis.eval(_RELEASE, 1, self.key, self._token)
            self._token = ""
