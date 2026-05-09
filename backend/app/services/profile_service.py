from sqlalchemy.orm import Session
from app.models.profile import UserProfile, Resume
from app.schemas.profile import UserProfileCreate, UserProfileUpdate, ResumeCreate
from app.core.logging import logger

class ProfileService:
    @staticmethod
    def get_profile(db: Session, user_id: int):
        return db.query(UserProfile).filter(UserProfile.user_id == user_id).first()

    @staticmethod
    def create_profile(db: Session, user_id: int, profile_in: UserProfileCreate):
        db_profile = UserProfile(user_id=user_id, **profile_in.model_dump())
        db.add(db_profile)
        db.commit()
        db.refresh(db_profile)
        logger.info(f"Profile created for user {user_id}")
        return db_profile

    @staticmethod
    def update_profile(db: Session, user_id: int, profile_in: UserProfileUpdate):
        db_profile = ProfileService.get_profile(db, user_id)
        if not db_profile:
            return None
        
        update_data = profile_in.model_dump(exclude_unset=True)
        for key, value in update_data.items():
            setattr(db_profile, key, value)
            
        db.add(db_profile)
        db.commit()
        db.refresh(db_profile)
        logger.info(f"Profile updated for user {user_id}")
        return db_profile

    @staticmethod
    def add_resume(db: Session, profile_id: int, resume_in: ResumeCreate):
        # If this is the base resume, unset other base resumes
        if resume_in.is_base:
            db.query(Resume).filter(Resume.profile_id == profile_id).update({"is_base": False})
            
        db_resume = Resume(profile_id=profile_id, **resume_in.model_dump())
        db.add(db_resume)
        db.commit()
        db.refresh(db_resume)
        logger.info(f"Resume added to profile {profile_id}")
        return db_resume

    @staticmethod
    def get_base_resume(db: Session, profile_id: int):
        return db.query(Resume).filter(Resume.profile_id == profile_id, Resume.is_base == True).first()
