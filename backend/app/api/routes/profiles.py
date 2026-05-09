from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List

from app.core.database import get_db
from app.api.deps import get_current_user
from app.models.user import User
from app.services.profile_service import ProfileService
from app.schemas.profile import UserProfileCreate, UserProfileUpdate, UserProfileResponse, ResumeCreate, ResumeResponse

router = APIRouter(prefix="/profiles", tags=["profiles"])

from app.services.currency_service import CurrencyService

@router.get("/me", response_model=UserProfileResponse | None)
async def read_my_profile(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    profile = ProfileService.get_profile(db, current_user.id)
    if profile and profile.salary_expectation:
        # Inject multi-currency data based on preferred currency
        salary_data = await CurrencyService.get_salary_in_multiple_currencies(
            profile.salary_expectation, 
            profile.preferred_currency or "USD"
        )
        # Convert to Pydantic model and add the extra field
        response_data = UserProfileResponse.from_orm(profile)
        response_data.salary_multi_currency = salary_data
        return response_data
    return profile

@router.post("/", response_model=UserProfileResponse)
def create_my_profile(
    profile_in: UserProfileCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    existing = ProfileService.get_profile(db, current_user.id)
    if existing:
        raise HTTPException(status_code=400, detail="Profile already exists")
    return ProfileService.create_profile(db, current_user.id, profile_in)

@router.patch("/", response_model=UserProfileResponse)
def update_my_profile(
    profile_in: UserProfileUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    profile = ProfileService.update_profile(db, current_user.id, profile_in)
    if not profile:
        raise HTTPException(status_code=404, detail="Profile not found")
    return profile

@router.post("/resumes", response_model=ResumeResponse)
def add_resume(
    resume_in: ResumeCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    profile = ProfileService.get_profile(db, current_user.id)
    if not profile:
        raise HTTPException(status_code=404, detail="Please create a profile first")
    return ProfileService.add_resume(db, profile.id, resume_in)
