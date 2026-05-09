import os
from datetime import datetime
from sqlalchemy.orm import Session

from app.models.user import User
from app.models.profile import UserProfile, Resume
from app.models.job import Job
from app.models.event import SystemEvent
from app.models.outcome import ApplicationOutcome
from app.core.logging import logger


class AccountService:
    @staticmethod
    def delete_all_user_data(db: Session, user_id: int) -> None:
        """GDPR-compliant permanent deletion of all user-associated data."""
        logger.warning(f"Permanently deleting all data for user_id={user_id}")

        db.query(ApplicationOutcome).filter(ApplicationOutcome.user_id == user_id).delete()
        db.query(SystemEvent).filter(SystemEvent.user_id == user_id).delete()

        # Resumes are owned via UserProfile — resolve profile first
        profile = db.query(UserProfile).filter(UserProfile.user_id == user_id).first()
        if profile:
            resumes = db.query(Resume).filter(Resume.profile_id == profile.id).all()
            for r in resumes:
                if r.file_path:
                    try:
                        os.remove(r.file_path)
                    except OSError:
                        pass
            db.query(Resume).filter(Resume.profile_id == profile.id).delete()
            db.query(UserProfile).filter(UserProfile.id == profile.id).delete()

        db.query(User).filter(User.id == user_id).delete()
        db.commit()
        logger.info(f"User {user_id} and all associated data purged.")

    @staticmethod
    def export_user_data(db: Session, user_id: int) -> dict:
        """Portable JSON export of all user data for data portability/transparency."""
        user = db.query(User).filter(User.id == user_id).first()
        profile = db.query(UserProfile).filter(UserProfile.user_id == user_id).first()
        resume_count = 0
        if profile:
            resume_count = db.query(Resume).filter(Resume.profile_id == profile.id).count()

        return {
            "account": {
                "email": user.email if user else None,
                "created_at": user.created_at.isoformat() if user else None,
            },
            "profile": {
                "full_name": profile.full_name if profile else None,
                "title": profile.title if profile else None,
                "skills": profile.skills if profile else [],
            },
            "resume_count": resume_count,
            "export_timestamp": datetime.now().isoformat(),
        }
