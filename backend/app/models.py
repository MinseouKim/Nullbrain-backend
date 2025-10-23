# app/models.py
import uuid
from sqlalchemy import Column, Integer, String, DateTime, func, text, JSON
from sqlalchemy.dialects.postgresql import UUID, JSONB
from app.db import Base  # ✅ db.py의 Base 사용

class Profile(Base):
    __tablename__ = "profiles"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(String(64), index=True, nullable=True)   # ✅ 추가: 사용자 식별자
    version = Column(Integer, nullable=False, default=1)

    body = Column(JSONB, nullable=False, server_default=text("'{}'::jsonb"))
    measures = Column(JSONB, nullable=False, server_default=text("'{}'::jsonb"))

    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)


class WorkoutResult(Base):
    __tablename__ = "workout_results"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    exercise_name = Column(String, nullable=False)
    total_reps = Column(Integer, nullable=False)
    total_sets = Column(Integer, nullable=False)
    avg_accuracy = Column(Integer, nullable=False)
    total_calories = Column(Integer, nullable=False)
    final_feedback = Column(String, nullable=True)
    all_set_results = Column(JSON, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    