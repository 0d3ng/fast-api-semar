from fastapi import APIRouter, HTTPException, Depends
from fastapi.security import OAuth2PasswordBearer
from starlette import status

from app.middlewares.auth import verify_token
from app.schemas.dashboard_schema import DashboardSummaryResponse
from app.services.dashboard_service import DashboardService
from app.utils.logger import get_logger

logger = get_logger(__name__)
router = APIRouter()
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")
credentials_exception = HTTPException(
    status_code=status.HTTP_401_UNAUTHORIZED,
    detail="Could not validate credentials",
    headers={"WWW-Authenticate": "Bearer"}
)


@router.get("/dashboard/summary", response_model=DashboardSummaryResponse)
async def get_dashboard_summary(token: str = Depends(oauth2_scheme)):
    try:
        verify_token(token=token, credentials_exception=credentials_exception)
        return await DashboardService.get_summary()
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))
