"""REST endpoints for AI-Assisted Firmware Security Assessment and Review."""

import json
from typing import List, Optional

from fastapi import APIRouter, BackgroundTasks, Depends, File, Form, Header, HTTPException, Query, UploadFile
from fastapi.security import OAuth2PasswordBearer
from starlette import status

from app.middlewares.auth import verify_token
from app.schemas.ota_security_assessment_schema import (
    AssessmentReanalyzeRequest,
    AssessmentReviewRequest,
    AssessmentSourceMetadata,
    SecurityAssessmentResponse,
)
from app.services.ota_firmware_release_service import FirmwareReleaseService
from app.services.ota_security_assessment_service import SecurityAssessmentService
from app.utils.config import SEMAR_API_TOKEN

router = APIRouter()
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")

credentials_exception = HTTPException(
    status_code=status.HTTP_401_UNAUTHORIZED,
    detail="Could not validate credentials",
    headers={"WWW-Authenticate": "Bearer"},
)


def _authorize_ci_or_jwt(authorization: str):
    token_type, _, token_str = authorization.partition(" ")
    if token_type.lower() != "bearer":
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token type")
    if token_str == SEMAR_API_TOKEN:
        return None
    try:
        return verify_token(token=token_str, credentials_exception=credentials_exception)
    except Exception:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid CI/CD or JWT token")


@router.post("/security-assessments", response_model=SecurityAssessmentResponse)
async def create_security_assessment(
    background_tasks: BackgroundTasks,
    metadata: str = Form(...),
    sbom_file: Optional[UploadFile] = File(None),
    cve_files: Optional[List[UploadFile]] = File(None),
    sarif_files: Optional[List[UploadFile]] = File(None),
    config_file: Optional[UploadFile] = File(None),
    run_ai: bool = Query(True),
    sync: bool = Query(False),
    authorization: str = Header(...),
):
    token_data = _authorize_ci_or_jwt(authorization)
    user_id = token_data.user_id if token_data else "cicd"

    try:
        meta_obj = AssessmentSourceMetadata(**json.loads(metadata))
    except Exception as exc:
        raise HTTPException(status_code=400, detail=f"Invalid metadata JSON: {exc}")

    assessment = await SecurityAssessmentService.ingest_and_assess(
        metadata=meta_obj,
        sbom_file=sbom_file,
        cve_files=cve_files,
        sarif_files=sarif_files,
        config_file=config_file,
        run_ai_sync=False,
        user_id=user_id or "cicd",
    )

    if sync:
        return await SecurityAssessmentService.run_ai_stage(
            str(assessment.id),
            None,
            None,
            run_ai,
        )

    background_tasks.add_task(
        SecurityAssessmentService.run_ai_stage,
        str(assessment.id),
        None,
        None,
        run_ai,
    )

    return assessment


@router.get("/security-assessments", response_model=List[SecurityAssessmentResponse])
async def list_security_assessments(
    target_version: Optional[str] = Query(None),
    platform_type: Optional[str] = Query(None),
    final_decision: Optional[str] = Query(None),
    workflow_state: Optional[str] = Query(None),
    token: str = Depends(oauth2_scheme),
):
    verify_token(token=token, credentials_exception=credentials_exception)
    return await SecurityAssessmentService.list_assessments(
        target_version=target_version,
        platform_type=platform_type,
        final_decision=final_decision,
        workflow_state=workflow_state,
    )


@router.get("/security-assessments/{assessment_id}", response_model=SecurityAssessmentResponse)
async def get_security_assessment(
    assessment_id: str,
    authorization: str = Header(...),
):
    _authorize_ci_or_jwt(authorization)
    return await SecurityAssessmentService.get_assessment(assessment_id)


@router.post("/security-assessments/{assessment_id}/review", response_model=SecurityAssessmentResponse)
async def review_security_assessment(
    assessment_id: str,
    review_req: AssessmentReviewRequest,
    token: str = Depends(oauth2_scheme),
):
    token_data = verify_token(token=token, credentials_exception=credentials_exception)
    return await SecurityAssessmentService.review_assessment(
        assessment_id=assessment_id,
        review_req=review_req,
        reviewer_username=token_data.username or token_data.user_id or "reviewer",
        reviewer_id=token_data.user_id or "reviewer",
    )


@router.post("/security-assessments/{assessment_id}/broadcast")
async def broadcast_from_security_assessment(
    assessment_id: str,
    token: str = Depends(oauth2_scheme),
):
    token_data = verify_token(token=token, credentials_exception=credentials_exception)
    assessment = await SecurityAssessmentService.get_assessment(assessment_id)
    return await FirmwareReleaseService.broadcast_firmware(
        target_version=assessment.target_version,
        platform_type=assessment.platform_type,
        user_id=token_data.user_id or "reviewer",
    )


@router.post("/security-assessments/{assessment_id}/reanalyze", response_model=SecurityAssessmentResponse)
async def reanalyze_security_assessment(
    assessment_id: str,
    req: AssessmentReanalyzeRequest,
    token: str = Depends(oauth2_scheme),
):
    verify_token(token=token, credentials_exception=credentials_exception)
    return await SecurityAssessmentService.run_ai_stage(
        assessment_id=assessment_id,
        model_override=req.model,
        profile_override=req.profile,
        run_ai=req.run_ai,
    )
