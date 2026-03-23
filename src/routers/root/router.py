from fastapi import APIRouter, Response, status

from src.database.dependencies import DbSession
from src.routers.root.actions import _health
from src.routers.root.schemas import HealthCheckResponse, HealthStatus

router = APIRouter()


@router.get(
    "/health",
    response_model=HealthCheckResponse,
    summary="Health Check",
    description="Check the health status of the application and its dependencies",
    responses={
        200: {
            "description": "Service is healthy",
            "content": {
                "application/json": {
                    "example": {
                        "status": "healthy",
                        "database": "connected",
                        "redis": "connected"
                    }
                }
            }
        },
        503: {
            "description": "Service is unhealthy",
            "content": {
                "application/json": {
                    "example": {
                        "status": "unhealthy",
                        "database": "error: connection failed",
                        "redis": "connected"
                    }
                }
            }
        }
    }
)
async def health(response: Response, session: DbSession) -> HealthCheckResponse:
    """
    Health check endpoint.
    
    Returns service health status including:
    - Overall application status
    - Database connectivity status
    - Redis cache connectivity status
    
    Returns 503 status code if any service is unhealthy.
    """
    result = await _health(session)
    
    # Set appropriate status code
    if result.status == HealthStatus.UNHEALTHY:
        response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE
    else:
        response.status_code = status.HTTP_200_OK
    
    return result
