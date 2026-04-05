#!/usr/bin/env python3
"""
API Router: Compliance Validation Endpoint
Provides /api/validate for farmer data validation

Rate limits: COMPUTE (20/min) for validation/calculation endpoints.
"""

from fastapi import APIRouter, HTTPException, Request
from typing import Dict, Any
from core.rate_limits import limiter, COMPUTE
from ml.compliance_validator import (
    ComplianceValidator,
    ValidationRequest,
    ValidationResponse,
)

router = APIRouter(tags=["validation"])


@router.post("/validate", response_model=ValidationResponse)
@limiter.limit(COMPUTE)
async def validate_farmer(request: Request, req: ValidationRequest) -> ValidationResponse:
    """
    Main validation endpoint.
    
    Runs 3-gate compliance check on farmer data:
    - GATE 1: Pasture load (NORMS_2024)
    - GATE 2: Subsidy conditions (NORMS_2026)
    - GATE 3: Mortality rate (NORMS_2015)
    
    Returns validation result with risk level and subsidy amount.
    
    **Example:**
    ```json
    {
        "animal_type": "КРС_молочное",
        "farm_area_hectares": 100,
        "livestock_count": 50,
        "production_kg_per_head": 220,
        "mortality_percent": 0.8
    }
    ```
    """
    try:
        result = ComplianceValidator.validate(req)
        return result
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Validation error")


@router.get("/norms")
@limiter.limit("30/minute")
async def get_norms(request: Request) -> Dict[str, Any]:
    """
    Get current norms used in validation.
    
    Returns all three norm systems:
    - NORMS_2024: Pasture load
    - NORMS_2026: Subsidy rates
    - NORMS_2015: Mortality rates
    """
    from ml.compliance_validator import (
        NORMS_2024_PASTURE,
        NORMS_2026_SUBSIDY,
        NORMS_2015_MORTALITY,
    )
    
    return {
        "norms_2024_pasture": NORMS_2024_PASTURE,
        "norms_2026_subsidy": NORMS_2026_SUBSIDY,
        "norms_2015_mortality": NORMS_2015_MORTALITY,
    }


@router.post("/calculate")
@limiter.limit(COMPUTE)
async def calculate_detail(request: Request, req: ValidationRequest) -> Dict[str, Any]:
    """
    Detailed calculation breakdown.
    
    Shows step-by-step calculations:
    - Pasture load vs norm
    - Subsidy rate lookup
    - Mortality penalty
    - Final subsidy amount
    """
    try:
        result = ComplianceValidator.validate(req)
        return {
            "input": req.dict(),
            "output": result.dict(),
            "detailed_checks": result.detailed_checks,
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail="Calculation error")
