"""
rate_limit.py — single shared slowapi Limiter instance.

Lives in its own module (rather than in main.py) purely to avoid a circular
import: main.py imports the routers, and routers need the limiter too.
"""

from slowapi import Limiter
from slowapi.util import get_remote_address

limiter = Limiter(key_func=get_remote_address)
