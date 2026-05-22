"""Shared rate limiter for Real Estate AVM."""
from slowapi import Limiter
from slowapi.util import get_remote_address

# Single limiter instance — import this from all modules that need rate limiting
limiter = Limiter(key_func=get_remote_address, default_limits=["60/minute"])
