import os
import json
from typing import Optional, List, Any, Dict
from dotenv import load_dotenv
import google.generativeai as genai

# --- 1. 환경 설정 ---
load_dotenv()
API_KEY = os.getenv("GOOGLE_API_KEY")

# 모델 목록 환경 변수
FAST_MODELS_STR = os.getenv("GEMINI_FAST_MODELS", "gemini-2.5-flash")
QUALITY_MODELS_STR = os.getenv("GEMINI_QUALITY_MODELS", "gemini-2.5-flash")

FAST_MODEL_LIST = [m.strip() for m in FAST_MODELS_STR.split(',') if m.strip()]
QUALITY_MODEL_LIST = [m.strip() for m in QUALITY_MODELS_STR.split(',') if m.strip()]

# --- 2. Gemini 모델 설정 ---
model_fast = None     # 빠른 피드백
model_quality = None  # 종합 요약

# ===== (A) 공통: 토큰/출력 최소화 설정 =====
BASE_GENERATION_CONFIG = {
    "temperature": 0.5,
    "top_p": 0.9,
    "top_k": 40,
    "candidate_count": 1,
    "response_mime_type": "application/json",
    "max_output_tokens": 256,   # 출력 길이 제한
}

# system instruction: 매 호출마다 장문 규칙을 넣지 않기 위해 고정
FAST_SYSTEM_INSTRUCTION = (
    "당신은 한국어로 답하는 AI 퍼스널 트레이너입니다. "
    "입력 JSON만 보고 핵심만 판단하며, 반드시 JSON으로만 응답하세요."
)

QUALITY_SYSTEM_INSTRUCTION = (
    "당신은 피트니스 전문가입니다. 입력 JSON(세트별 결과 요약)만 보고 "
    "200자 이내 한국어로 종합 피드백을 JSON으로만 응답하세요."
)

# 이 파일 내에서 동적으로 바꿔 끼울 전역 지시문
_SYSTEM_INSTRUCTION: str = ""

# [신규] 입력 축소 유틸: 숫자 반올림/긴 텍스트 자르기
def _round_num(v: Any, nd: int = 3) -> Any:
    if isinstance(v, float):
        return round(v, nd)
    if isinstance(v, list):
        return [_round_num(x, nd) for x in v]
    if isinstance(v, dict):
        return {k: _round_num(v[k], nd) for k in v}
    return v

def _truncate_str(s: Any, maxlen: int = 200) -> Any:
    if isinstance(s, str) and len(s) > maxlen:
        return s[:maxlen] + "…"
    return s

def _compact_set_item(item: Dict[str, Any]) -> Dict[str, Any]:
    """세트 결과에서 거대 필드 제거 및 최소 요약만 남김"""
    meta = item.get("meta") or {}
    stats = item.get("stats") or {}
    # accuracy/칼로리/시간 등만 남기고 숫자는 반올림
    compact_stats = {
        "accuracy": stats.get("accuracy"),
        "calories": stats.get("calories"),
        "avg_speed": stats.get("avg_speed"),
        "tempo": stats.get("tempo"),
    }
    compact_stats = _round_num(compact_stats, 3)

    # 길 수 있는 텍스트는 잘라줌
    ai_feedback = _truncate_str(item.get("aiFeedback", ""), 180)

    # 절대 금지: analysisData, landmarkHistory 같은 초대형 필드
    return {
        "meta": {
            "setIndex": meta.get("setIndex"),
            "totalSets": meta.get("totalSets"),
            "targetReps": meta.get("targetReps"),
            "exerciseId": meta.get("exerciseId"),
            "exerciseName": meta.get("exerciseName"),
        },
        "stats": compact_stats,
        "aiFeedback": ai_feedback,
        # 필요한 경우 간단한 규칙성 태그 정도만 유지할 수 있음
    }

def _compact_set_results(set_results: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    # 길면 최근 N개만, 또는 전부 얕게: 여기서는 전부 얕게 + 최대 12세트까지만
    MAX_SETS = 12
    compact = []
    for i, it in enumerate(set_results[:MAX_SETS]):
        compact.append(_compact_set_item(it))
    return compact

# [신규] 모델 초기화 헬퍼 (system_instruction 주입 + generation_config 사용)
def initialize_model_from_list(
    model_list: List[str],
    generation_config: dict,
    safety_settings: list
) -> Optional[genai.GenerativeModel]:
    if not API_KEY:
        print("[ERROR] GOOGLE_API_KEY가 .env 파일에 설정되지 않았습니다.")
        return None
    for model_name in model_list:
        try:
            model = genai.GenerativeModel(
                model_name,
                safety_settings=safety_settings,
                generation_config=generation_config,
                system_instruction=_SYSTEM_INSTRUCTION,  # 👈 고정 지시
            )
            print(f"[INFO] 모델 초기화 성공: {model_name}")
            return model
        except Exception as e:
            print(f"[WARN] 모델 초기화 실패: {model_name} (오류: {e}). 다음 모델을 시도합니다...")
    print(f"[ERROR] 목록에 있는 모델을 초기화하지 못했습니다: {model_list}")
    return None

# API 키 설정 및 모델 준비
if API_KEY:
    genai.configure(api_key=API_KEY)

    safety_settings = [
        {"category": "HARM_CATEGORY_HARASSMENT", "threshold": "BLOCK_NONE"},
        {"category": "HARM_CATEGORY_HATE_SPEECH", "threshold": "BLOCK_NONE"},
        {"category": "HARM_CATEGORY_SEXUALLY_EXPLICIT", "threshold": "BLOCK_NONE"},
        {"category": "HARM_CATEGORY_DANGEROUS_CONTENT", "threshold": "BLOCK_NONE"},
    ]

    # 빠른 피드백 모델
    print(f"[INFO] 빠른 피드백 모델 초기화 시도 (목록: {FAST_MODEL_LIST})...")
    _SYSTEM_INSTRUCTION = FAST_SYSTEM_INSTRUCTION
    model_fast = initialize_model_from_list(
        FAST_MODEL_LIST, BASE_GENERATION_CONFIG, safety_settings
    )

    # 종합 요약 모델
    print(f"[INFO] 종합 요약 모델 초기화 시도 (목록: {QUALITY_MODEL_LIST})...")
    _SYSTEM_INSTRUCTION = QUALITY_SYSTEM_INSTRUCTION
    model_quality = initialize_model_from_list(
        QUALITY_MODEL_LIST, BASE_GENERATION_CONFIG, safety_settings
    )
else:
    print("[ERROR] GOOGLE_API_KEY를 찾을 수 없습니다. .env 파일을 확인하세요.")


# --- 3. AI 피드백 생성 함수 ---

# (1) 빠른 피드백
async def get_conversational_feedback(
    exercise_name: str,
    rep_counter: int,
    stage: str,
    body_profile: Optional[dict] = None,
    real_time_analysis: Optional[dict] = None,
    angle: Optional[float] = None,
    history: Optional[List[str]] = None,
    extra_context: Optional[dict] = None,
) -> dict:
    """
    '빠른 피드백' 모델(model_fast)을 사용하여 정확도와 피드백을 JSON으로 요청합니다.
    """
    if not model_fast:
        return {"accuracy": 0, "feedback": "⚠️ Gemini 'FAST' 모델이 설정되지 않았습니다."}

    # ✅ 프롬프트를 장문 규칙 없이 '데이터 JSON'만 보내도록 축소
    disp = (extra_context or {}).get("exercise_display_name") or exercise_name
    payload = {
        "exercise_display_name": disp,
        "exercise_id": exercise_name,
        "stage": stage,
        "rep_counter": rep_counter,
        "target_reps": (extra_context or {}).get("target_reps"),
        "set": {
            "index": (extra_context or {}).get("set_index"),
            "total": (extra_context or {}).get("total_sets"),
        },
        # 큰 데이터는 슬림화
        "user_profile": _round_num(body_profile, 3) if body_profile else None,
        "realtime_summary": _round_num(real_time_analysis, 3) if real_time_analysis else None,
        "angle_sample": _round_num(angle, 3) if angle is not None else None,
        # 히스토리는 최근 N개만 (과도한 텍스트 방지)
        "history_tail": history[-20:] if history and len(history) > 20 else history,
    }

    # 공백 제거하여 토큰 절약
    prompt = json.dumps(payload, ensure_ascii=False, separators=(",", ":"))

    try:
        resp = await model_fast.generate_content_async(prompt)
        try:
            return json.loads(resp.text)
        except Exception:
            print(f"[WARN] Gemini 응답이 JSON 형식이 아님: {resp.text}")
            return {"accuracy": 0, "feedback": "⚠️ AI 응답 파싱 실패"}
    except Exception as e:
        print(f"--- GEMINI API ERROR (FAST) ---\nError: {e}\n--------------------------")
        if "resp" in locals() and hasattr(resp, "prompt_feedback"):
            print(f"Prompt Feedback: {resp.prompt_feedback}")
        return {"accuracy": 0, "feedback": "⚠️ AI 피드백 생성에 실패했습니다."}

# (2) 종합 피드백
async def get_overall_feedback(set_results: list[dict]) -> dict:
    """
    '종합 요약' 모델(model_quality)을 사용하여 운동 전체에 대한 요약/개선 포인트를 생성.
    """
    if not model_quality:
        return {"overall_feedback": "⚠️ Gemini 'QUALITY' 모델이 설정되지 않았습니다."}

    # ✅ 입력 축소: 거대 필드 제거 + 숫자 반올림 + 최근 N세트 제한
    compact_sets = _compact_set_results(set_results)

    payload = {
        "sets": compact_sets,
        # 평균 정확도(있으면) 프리컴퓨트해서 힌트 제공 → 모델 추론 부담 감소
        "avg_accuracy_hint": _round_num(
            sum([(s.get("stats") or {}).get("accuracy", 0) or 0 for s in compact_sets]) / max(len(compact_sets), 1), 2
        ) if compact_sets else 0.0
    }

    prompt = json.dumps(payload, ensure_ascii=False, separators=(",", ":"))

    try:
        resp = await model_quality.generate_content_async(prompt)
        return json.loads(resp.text)
    except Exception as e:
        print(f"--- GEMINI API ERROR (QUALITY) ---\nError: {e}\n--------------------------")
        if "resp" in locals() and hasattr(resp, "prompt_feedback"):
            print(f"Prompt Feedback: {resp.prompt_feedback}")
        return {"overall_feedback": "⚠️ 종합 피드백 생성 실패"}
