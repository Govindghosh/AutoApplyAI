from sqlalchemy.orm import Session
from app.models.health import SelectorHealth
from app.core.database import SessionLocal
from datetime import datetime, timezone
from app.core.logging import logger

class HealthService:
    @staticmethod
    def record_success(platform: str, selector_name: str):
        db = SessionLocal()
        try:
            health = db.query(SelectorHealth).filter(
                SelectorHealth.platform == platform,
                SelectorHealth.selector_name == selector_name
            ).first()
            
            if not health:
                health = SelectorHealth(platform=platform, selector_name=selector_name)
                db.add(health)
            
            health.success_count += 1
            health.last_success = datetime.now(timezone.utc)
            total = health.success_count + health.failure_count
            health.success_rate = health.success_count / total
            db.commit()
        finally:
            db.close()

    @staticmethod
    def record_failure(platform: str, selector_name: str):
        db = SessionLocal()
        try:
            health = db.query(SelectorHealth).filter(
                SelectorHealth.platform == platform,
                SelectorHealth.selector_name == selector_name
            ).first()
            
            if not health:
                health = SelectorHealth(platform=platform, selector_name=selector_name)
                db.add(health)
            
            health.failure_count += 1
            health.last_failure = datetime.now(timezone.utc)
            total = health.success_count + health.failure_count
            health.success_rate = health.success_count / total
            db.commit()
            
            # If success rate drops below threshold, we flag for drift investigation
            if health.success_rate < 0.7 and total > 5:
                logger.warning(f"CRITICAL DRIFT DETECTED: {platform} -> {selector_name} (Rate: {health.success_rate:.2f})")
        finally:
            db.close()

    @staticmethod
    def get_platform_health(db: Session, platform: str):
        return db.query(SelectorHealth).filter(SelectorHealth.platform == platform).all()
