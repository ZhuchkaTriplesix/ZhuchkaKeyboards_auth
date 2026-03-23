"""Pydantic schemas for root router endpoints."""

from enum import Enum
from pydantic import BaseModel, Field


class HealthStatus(str, Enum):
    """Health status enum."""
    HEALTHY = "healthy"
    UNHEALTHY = "unhealthy"


class ServiceStatus(str, Enum):
    """Individual service status enum."""
    CONNECTED = "connected"
    DISCONNECTED = "disconnected"
    ERROR = "error"
    UNKNOWN = "unknown"


class HealthCheckResponse(BaseModel):
    """Health check response schema."""
    
    status: HealthStatus = Field(
        ...,
        description="Overall health status of the application"
    )
    database: str = Field(
        ...,
        description="Database connection status"
    )
    redis: str = Field(
        ...,
        description="Redis connection status"
    )
    
    class Config:
        json_schema_extra = {
            "example": {
                "status": "healthy",
                "database": "connected",
                "redis": "connected"
            }
        }

