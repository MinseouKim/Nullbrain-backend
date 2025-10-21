import uuid
from sqlalchemy import Column, Integer, DateTime, func, text
from sqlalchemy.dialects.postgresql import UUID, JSONB
from .db import Base

class Profile(Base):
    __tablename__ = "profiles"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    version = Column(Integer, nullable=False, default=1)

    body = Column(JSONB, nullable=False, server_default=text("'{}'::jsonb"))
    measures = Column(JSONB, nullable=False, server_default=text("'{}'::jsonb"))

    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)


class WorkoutResult(Base):
    __tablename__ = "workout_results"

    id = Column(PGUUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    exercise_name = Column(String, nullable=False)
    total_reps = Column(Integer, nullable=False)
    total_sets = Column(Integer, nullable=False)
    avg_accuracy = Column(Integer, nullable=False)
    total_calories = Column(Integer, nullable=False)
    final_feedback = Column(String, nullable=True)
    all_set_results = Column(JSON, nullable=False)  # 세트별 AI 결과 JSON 전체 저장
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)