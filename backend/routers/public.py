#!/usr/bin/env python3
"""
Public API Router - Read-only access to data (no authentication required)
Allows anyone to view project data without Supabase credentials

Rate limit: PUBLIC (30/min) — open endpoints, moderate protection.
"""

from fastapi import APIRouter, HTTPException, Request
from typing import Dict, Any, List
from core.rate_limits import limiter, PUBLIC
from services.supabase_service import _get_admin_client  # Use admin for backend reads (anon blocked by RLS)

router = APIRouter(prefix="/public", tags=["public"])


@router.get("/health")
@limiter.limit(PUBLIC)
async def health_check(request: Request) -> Dict[str, str]:
    """Health check - verify backend is running"""
    return {"status": "ok", "message": "Backend is running"}


@router.get("/producers")
@limiter.limit(PUBLIC)
async def get_public_producers(request: Request, limit: int = 100) -> Dict[str, Any]:
    """
    Get list of producers (public read-only access).
    
    **No authentication required**
    
    Args:
        limit: Maximum number of producers to return (default: 100)
    
    Returns:
        List of producers with basic info
    """
    try:
        
        
        client = _get_admin_client()
        response = client.table("producers").select(
            "producer_id, region, direction, total_applications, completion_rate"
        ).limit(limit).execute()
        
        return {
            "count": len(response.data or []),
            "data": response.data or [],
            "limit": limit
        }
    except Exception as e:
        error_msg = str(e).lower()
        if "invalid api key" in error_msg or "unauthorized" in error_msg:
            raise HTTPException(
                status_code=503,
                detail="Database temporarily unavailable. Please verify SUPABASE_ANON_KEY in .env"
            )
        raise HTTPException(
            status_code=500,
            detail=f"Failed to fetch producers: {str(e)}"
        )


@router.get("/scores")
@limiter.limit(PUBLIC)
async def get_public_scores(request: Request, limit: int = 100) -> Dict[str, Any]:
    """
    Get ML scores and rankings (public read-only access).
    
    **No authentication required**
    
    Args:
        limit: Maximum number of scores to return (default: 100)
    
    Returns:
        List of scores with ML rankings
    """
    try:
        
        
        client = _get_admin_client()
        response = client.table("scores").select(
            "producer_id, ml_score, ml_rank, fcfs_rank, delta, hidden_talent"
        ).limit(limit).execute()
        
        return {
            "count": len(response.data or []),
            "data": response.data or [],
            "limit": limit
        }
    except Exception as e:
        error_msg = str(e).lower()
        if "invalid api key" in error_msg or "unauthorized" in error_msg:
            raise HTTPException(
                status_code=503,
                detail="Database temporarily unavailable. Please verify SUPABASE_ANON_KEY in .env"
            )
        raise HTTPException(
            status_code=500,
            detail=f"Failed to fetch scores: {str(e)}"
        )


@router.get("/data")
@limiter.limit(PUBLIC)
async def get_public_combined_data(request: Request, limit: int = 50) -> Dict[str, Any]:
    """
    Get combined producers + scores data (public read-only access).
    
    **No authentication required**
    
    This is a convenience endpoint that joins producers and scores tables.
    
    Args:
        limit: Maximum number of records to return (default: 50)
    
    Returns:
        Combined data with producer info and ML scores
    """
    try:
        
        
        client = _get_admin_client()
        
        # Get scores
        scores_response = client.table("scores").select(
            "producer_id, ml_score, ml_rank, fcfs_rank, delta, hidden_talent"
        ).limit(limit).execute()
        scores = scores_response.data or []
        
        if not scores:
            return {
                "count": 0,
                "data": [],
                "message": "No data available"
            }
        
        # Get producer IDs
        producer_ids = [s["producer_id"] for s in scores]
        
        # Get producer data
        producers_response = client.table("producers").select(
            "producer_id, region, direction, total_applications, completion_rate"
        ).in_("producer_id", producer_ids).execute()
        producers_map = {p["producer_id"]: p for p in (producers_response.data or [])}
        
        # Combine data
        combined = []
        for score in scores:
            producer = producers_map.get(score["producer_id"], {})
            combined.append({
                "producer_id": score["producer_id"],
                "ml_score": score.get("ml_score"),
                "ml_rank": score.get("ml_rank"),
                "fcfs_rank": score.get("fcfs_rank"),
                "delta": score.get("delta"),
                "hidden_talent": score.get("hidden_talent"),
                "region": producer.get("region"),
                "direction": producer.get("direction"),
                "total_applications": producer.get("total_applications"),
                "completion_rate": producer.get("completion_rate"),
            })
        
        return {
            "count": len(combined),
            "data": combined,
            "limit": limit
        }
    except Exception as e:
        error_msg = str(e).lower()
        if "invalid api key" in error_msg or "unauthorized" in error_msg:
            raise HTTPException(
                status_code=503,
                detail="Database temporarily unavailable. Please verify SUPABASE_ANON_KEY in .env"
            )
        raise HTTPException(
            status_code=500,
            detail=f"Failed to fetch combined data: {str(e)}"
        )


@router.get("/metrics")
@limiter.limit(PUBLIC)
async def get_public_metrics(request: Request) -> Dict[str, Any]:
    """
    Get model metrics and statistics (public read-only access).
    
    **No authentication required**
    
    Returns:
        Model performance metrics and system statistics
    """
    try:
        
        
        client = _get_admin_client()
        response = client.table("model_metrics").select("*").limit(1).execute()
        
        if response.data:
            return {
                "status": "ok",
                "metrics": response.data[0]
            }
        else:
            return {
                "status": "no_data",
                "message": "Model metrics not available"
            }
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to fetch metrics: {str(e)}"
        )


@router.get("/stats")
@limiter.limit(PUBLIC)
async def get_public_stats(request: Request) -> Dict[str, Any]:
    """
    Get summary statistics (public read-only access).
    
    **No authentication required**
    
    Returns:
        Summary stats about producers, scores, and system
    """
    try:
        
        
        client = _get_admin_client()
        
        # Get counts
        producers_count = client.table("producers").select("producer_id", count="exact").execute()
        scores_count = client.table("scores").select("producer_id", count="exact").execute()
        
        # Get top regions
        top_regions = client.table("producers").select(
            "region"
        ).limit(1000).execute()
        
        region_counts = {}
        for p in (top_regions.data or []):
            region = p.get("region", "Unknown")
            region_counts[region] = region_counts.get(region, 0) + 1
        
        return {
            "total_producers": producers_count.count or 0,
            "total_scores": scores_count.count or 0,
            "regions": region_counts,
            "top_regions": sorted(
                region_counts.items(),
                key=lambda x: x[1],
                reverse=True
            )[:10]
        }
    except Exception as e:
        error_msg = str(e).lower()
        if "invalid api key" in error_msg or "unauthorized" in error_msg:
            raise HTTPException(
                status_code=503,
                detail="Database temporarily unavailable. Please verify SUPABASE_ANON_KEY in .env"
            )
        raise HTTPException(
            status_code=500,
            detail=f"Failed to fetch statistics: {str(e)}"
        )
