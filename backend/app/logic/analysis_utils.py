# app/logic/analysis_utils.py
from typing import Optional
from sqlalchemy import select, desc
from sqlalchemy.orm import Session
from app.models import Profile

def get_latest_profile(db: Session, user_id: Optional[str]) -> Optional[dict]:
    """
    해당 user_id의 가장 최근 Profile.measures(체형분석 baseline)를 반환.
    user_id가 None이면 전체 중 최신 1건을 반환.
    """
    stmt = select(Profile)
    if user_id:
        stmt = stmt.where(Profile.user_id == user_id)
    stmt = stmt.order_by(desc(Profile.created_at)).limit(1)

    obj = db.execute(stmt).scalars().first()
    return obj.measures if obj else None
