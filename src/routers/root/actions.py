from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from src.redis_client.redis import RedisController
from src.routers.root.schemas import HealthCheckResponse, HealthStatus


async def _health(session: AsyncSession) -> HealthCheckResponse:
    """
    Health check endpoint to verify service status.

    Checks:
    - Database connectivity
    - Redis connectivity

    Args:
        session: Database session

    Returns:
        HealthCheckResponse with status of all services
    """
    status = HealthStatus.HEALTHY
    database_status = "unknown"
    redis_status = "unknown"

    # Check database connection
    try:
        await session.execute(text("SELECT 1"))
        database_status = "connected"
    except Exception as e:
        status = HealthStatus.UNHEALTHY
        database_status = f"error: {str(e)}"

    # Check Redis connection
    try:
        test_key = "_health_check"
        await RedisController.set(test_key, "ok", ttl=10)
        value = await RedisController.get(test_key)
        if value == "ok":
            redis_status = "connected"
            await RedisController.delete(test_key)
        else:
            status = HealthStatus.UNHEALTHY
            redis_status = "connection_failed"
    except Exception as e:
        status = HealthStatus.UNHEALTHY
        redis_status = f"error: {str(e)}"

    return HealthCheckResponse(status=status, database=database_status, redis=redis_status)
