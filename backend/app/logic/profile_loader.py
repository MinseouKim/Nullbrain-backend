from sqlalchemy.orm import Session
from app import models

def load_profile_from_db(db: Session, profile_id: str | None = None):
    """
    DB에서 사용자의 체형 분석(Profile)을 불러옵니다.
    profile_id가 주어지면 해당 사용자 데이터만,
    없으면 가장 최근 Profile을 반환합니다.
    """
    query = db.query(models.Profile)
    if profile_id:
        profile = query.filter(models.Profile.id == profile_id).first()
    else:
        profile = query.order_by(models.Profile.created_at.desc()).first()
    
    if not profile:
        raise ValueError("체형 분석 데이터가 존재하지 않습니다.")
    
    return {
        "id": str(profile.id),
        "version": profile.version,
        "body": profile.body,
        "measures": profile.measures,
    }
