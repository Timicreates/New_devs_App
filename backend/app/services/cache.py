import json
import redis.asyncio as redis
from typing import Dict, Any
import os

# Initialize Redis (would typically be in a config file)
# Using localhost default for simplicity in this challenge
redis_client = redis.Redis.from_url(os.getenv("REDIS_URL", "redis://localhost:6379/0"))

async def get_revenue_summary(property_id: str, tenant_id: str) -> Dict[str, Any]:
    """
    Fetches revenue summary, utilizing caching to improve performance.
    """
    # FIX: Include tenant_id in cache key to prevent data leakage between tenants
    cache_key = f"revenue:{property_id}:{tenant_id}"
    
    # Try to get from cache
    cached = await redis_client.get(cache_key)
    if cached:
        return json.loads(cached)
    
    # Simulate DB Fetch (Mocking the DB call here for the service file isolation)
    # In the full implementation this calls the reservation service
    from app.services.reservations import calculate_total_revenue
    
    # Calculate revenue
    result = await calculate_total_revenue(property_id, tenant_id)
    
    # Cache the result for 5 minutes
    await redis_client.setex(cache_key, 300, json.dumps(result))
    
    return result
