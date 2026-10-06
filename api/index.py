"""
Serverless entry point for Vercel / Cloud Functions / ASGI hosting.
"""

from vessel_system.server import app

# Vercel and ASGI runners will consume 'app'
__all__ = ["app"]
