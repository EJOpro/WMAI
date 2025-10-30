"""API 라우터 패키지"""

from . import ingest_routes, trends_routes, community_routes, ga4_routes, stats_routes, popular_routes, analytics_routes

__all__ = [
    "ingest_routes",
    "trends_routes", 
    "community_routes",
    "ga4_routes",
    "stats_routes",
    "popular_routes",
    "analytics_routes"
]
