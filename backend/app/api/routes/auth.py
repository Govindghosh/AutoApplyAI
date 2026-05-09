from fastapi import APIRouter, Depends, status, Response
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.schemas.user import UserCreate, UserLogin, UserResponse, TokenResponse, TokenRefresh
from app.services.auth_service import AuthService
from app.api.deps import get_db, get_current_user
from app.models.user import User

router = APIRouter(prefix="/auth", tags=["auth"])

@router.post("/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
def register(user_in: UserCreate, db: Session = Depends(get_db)):
    return AuthService.register_user(db, user_in)

@router.post("/login", response_model=TokenResponse)
def login(user_in: UserLogin, db: Session = Depends(get_db)):
    return AuthService.authenticate_user(db, user_in)

@router.get("/me", response_model=UserResponse)
def read_user_me(current_user: User = Depends(get_current_user)):
    return current_user

@router.post("/refresh", response_model=TokenResponse)
def refresh_token(token_in: TokenRefresh, db: Session = Depends(get_db)):
    return AuthService.refresh_token(db, token_in.refresh_token)

@router.post("/logout")
def logout():
    # In a pure JWT setup without blacklisting, logout is mostly a frontend action.
    # This endpoint exists as a hook for future blacklisting or cookie clearing.
    return {"message": "Successfully logged out"}

from app.services.account_service import AccountService

@router.get("/export")
async def export_data(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Generate a portable JSON export of all user data.
    """
    return AccountService.export_user_data(db, current_user.id)

@router.delete("/purge")
async def purge_account(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Permanently delete the user account and all associated data.
    """
    AccountService.delete_all_user_data(db, current_user.id)
    return {"status": "purged"}
