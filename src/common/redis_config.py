"""
Shared Redis Configuration Module

This module provides a centralized Redis configuration class that automatically
loads connection parameters from environment variables. This eliminates the need
for manual os.getenv() calls throught the codebase.

Environment Variables:
    REDIS_HOST: Redis hostname (default: localhost)
    REDIS_PORT: Redis port (default: 6379)

Example:
    # Automatically loads from environment variables
    config = RedisConfig()

    # Or override with explicit values
    config = RedisConfig(
        hostname="prod-redis.example.com",
        port=9999
    )
"""

import os
import logging
from dataclasses import dataclass

logger = logging.getLogger(__name__)

@dataclass
class RedisConfig:
    """
    Configuration for Redis Connection

    Automatically loads connection parameters from environment variables
    when instantiated with default values. Override by passing explicit values
    """

    hostname: str = "localhost"
    port: int = 6379

    def __post_init__(self):
        """ Load configuration from envrionment variables if available """
        self.hostname = os.getenv("REDIS_HOST", self.hostname)
        self.port = int(os.getenv("REDIS_PORT", self.port))