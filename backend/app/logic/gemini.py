import os
import json
from typing import Optional, List, Any, Dict
from dotenv import load_dotenv
import google.generativeai as genai

# --- 1. 환경 설정 ---
load_dotenv()
API_KEY = os.getenv("GOOGLE_API_KEY")

# [수정] 모델 목록 환경 변수 로드 (.env 파일에 정의된 대로)
FAST_MODELS_STR = os.getenv("GEMINI_FAST_MODELS", "gemini-2.5-flash")
QUALITY_MODELS_STR = os.getenv("GEMINI_QUALITY_MODELS", "gemini-2.5-flash")

# 콤마로 분리하여 리스트로 만듭니다.
FAST_MODEL_LIST = [m.strip() for m in FAST_MODELS_STR.split(',') if m.strip()]
QUALITY_MODEL_LIST = [m.strip() for m in QUALITY_MODELS_STR.split(',') if m.strip()]

# --- 2. Gemini 모델 설정 ---
model_fast = None     # 빠른 피드백용 모델 인스턴스
model_quality = None  # 종합 요약용 모델 인스턴스

# [신규] 공통: 응답을 무조건 dict로 강제
def _force_object(res: Any) -> Dict[str, Any]:
    """
    - dict면 그대로
    - list면 첫 dict를 선택(없으면 tips로 감싸기)
    - str면 JSON 파싱 시도, 실패 시 feedback으로 감싸기
    - 그 외 타입은 문자열화해 feedback으로 감싸기
    """
    if res is None:
        return {}
    if isinstance(res, dict):
        return res
    if isinstance(res, list):
        for item in res:
            if isinstance(item, dict):
                return item
        return {"feedback": "AI 피드백 생성 실패", "tips": res}
    if isinstance(res, str):
        try:
            parsed = json.loads(res)
            return _force_object(parsed)
        except Exception:
            return {"feedback": res}
    # 기타 타입
    return {"feedback": str(res)}

# [신규] 모델 초기화 헬퍼 함수
def initialize_model_from_list(
    model_list: List[str],
    generation_config: dict,
    safety_settings: list
) -> Optional[genai.GenerativeModel]:
    """
    제공된 모델 이름 목록을 순회하며
    가장 먼저 성공적으로 초기화되는 모델을 반환합니다.
    """
    if not API_KEY:
        print("[ERROR] GOOGLE_API_KEY가 .env 파일에 설정되지 않았습니다.")
        return None

    for model_name in model_list:
        try:
            model = genai.GenerativeModel(
                model_name,
                safety_settings=safety_settings,
                generation_config=generation_config,
            )
            print(f"[INFO] 모델 초기화 성공: {model_name}")
            return model
        except Exception as e:
            print(f"[WARN] 모델 초기화 실패: {model_name} (오류: {e}). 다음 모델을 시도합니다...")

    print(f"[ERROR] 목록에 있는 모델을 초기화하지 못했습니다: {model_list}")
    return None

# API 키가 있을 경우에만 모델 설정을 시도합니다.
if API_KEY:
    genai.configure(api_key=API_KEY)

    safety_settings = [
        {"category": "HARM_CATEGORY_HARASSMENT", "threshold": "BLOCK_NONE"},
        {"category": "HARM_CATEGORY_HATE_SPEECH", "threshold": "BLOCK_NONE"},
        {"category": "HARM_CATEGORY_SEXUALLY_EXPLICIT", "threshold": "BLOCK_NONE"},
        {"category": "HARM_CATEGORY_DANGEROUS_CONTENT", "threshold": "BLOCK_NONE"},
    ]

    # JSON 응답을 위한 공통 설정
    generation_config = {
        "temperature": 0.7,
        "response_mime_type": "application/json",
    }

    print(f"[INFO] 빠른 피드백 모델 초기화 시도 (목록: {FAST_MODEL_LIST})...")
    model_fast = initialize_model_from_list(
        FAST_MODEL_LIST, generation_config, safety_settings
    )

    print(f"[INFO] 종합 요약 모델 초기화 시도 (목록: {QUALITY_MODEL_LIST})...")
    model_quality = initialize_model_from_list(
        QUALITY_MODEL_LIST, generation_config, safety_settings
    )
else:
    print("[ERROR] GOOGLE_API_KEY를 찾을 수 없습니다. .env 파일을 확인하세요.")

# --- 3. AI 피드백 생성 함수 ---

# [수정] get_conversational_feedback 함수 (extra_context 포함)
async def get_conversational_feedback(
    exercise_name: str,
    rep_counter: int,
    stage: str,
    body_profile: Optional[dict] = None,
    real_time_analysis: Optional[dict] = None,
    angle: Optional[float] = None,
    history: Optional[List[str]] = None,
    extra_context: Optional[dict] = None,  # 👈 추가된 파라미터
) -> dict:
    """
    '빠른 피드백' 모델(model_fast)을 사용하여 정확도와 피드백을 JSON으로 요청합니다.
    (구조는 유지, 내부만 보강)
    """
    if not model_fast:
        return {"accuracy": 0, "feedback": "⚠️ Gemini 'FAST' 모델이 설정되지 않았습니다."}

    profile_section = f"* 사용자의 체형 분석 정보 (정적 데이터):\n{body_profile}\n" if body_profile else ""
    analysis_section = f"* 이번 세트의 실시간 움직임/히스토리 (동적 데이터):\n{real_time_analysis}\n" if real_time_analysis else ""
    extra_section = f"* 추가 맥락(표시명/세트/타깃):\n{extra_context}\n" if extra_context else ""

    # 표시용 한글 이름 우선 사용
    disp = (extra_context or {}).get("exercise_display_name") or exercise_name
    set_idx = (extra_context or {}).get("set_index")
    total_sets = (extra_context or {}).get("total_sets")
    target_reps = (extra_context or {}).get("target_reps")

    # ⚠️ 최상위는 "반드시 객체(Object)"로만, 키 제한을 강하게 명시
    prompt = f"""
당신은 한국어로 답하는 전문 AI 퍼스널 트레이너입니다.
아래의 정적/동적/추가 맥락을 참조하되, 그대로 복붙하지 말고 **종합 판단**을 제공하세요.

{profile_section}
{analysis_section}
{extra_section}

* 현재 운동 정보:
- 운동(표시명): {disp}
- 운동(내부ID): {exercise_name}
- 단계: {stage}
- 반복 횟수(실행): {rep_counter}
- 목표 반복수(세트당): {target_reps}
- 현재 세트/총 세트: {set_idx}/{total_sets}

* JSON 출력 규칙(최상위는 **반드시 객체(Object)로만**; 배열로 시작 금지):
{{
  "accuracy": <0~100 정수>,
  "feedback": "<70자 이내 한국어 핵심 문장>",
  "tips": ["짧은 팁1", "짧은 팁2"],
  "risk_level": "low" | "mid" | "high"
}}
키는 위 4개만 포함하고, 그 외 키는 생성하지 마세요.
"""

    try:
        resp = await model_fast.generate_content_async(prompt)
        raw = resp.text
        result = _force_object(raw)

        # 기본값/타입 정리
        result.setdefault("accuracy", 0)
        result.setdefault("feedback", "AI 피드백 생성 실패")
        result.setdefault("tips", [])
        result.setdefault("risk_level", "unknown")
        if isinstance(result["tips"], str):
            result["tips"] = [result["tips"]]

        return result

    except Exception as e:
        print(f"--- GEMINI API ERROR (FAST) ---\nError: {e}\n--------------------------")
        if "resp" in locals() and hasattr(resp, "prompt_feedback"):
            print(f"Prompt Feedback: {resp.prompt_feedback}")
        return {"accuracy": 0, "feedback": "⚠️ AI 피드백 생성에 실패했습니다.", "tips": [], "risk_level": "unknown"}


async def get_overall_feedback(set_results: list[dict]) -> dict:
    """
    '종합 요약' 모델(model_quality)을 사용하여
    전체적인 운동 품질, 자세 안정성, 향상 포인트를 종합적으로 평가.
    (구조는 유지, 내부만 보강)
    """
    if not model_quality:
        return {"overall_feedback": "⚠️ Gemini 'QUALITY' 모델이 설정되지 않았습니다.", "summary_accuracy": 0, "improvement_tips": []}

    prompt = f"""
당신은 피트니스 전문가 AI 트레이너입니다.
아래는 사용자의 각 세트별 운동 분석 결과입니다.
이 데이터를 기반으로 전체 운동에 대한 종합 피드백을 작성하세요.

데이터:
{json.dumps(set_results, ensure_ascii=False, indent=2)}

작성 규칙:
1. 전체적인 운동 수행 품질을 요약하세요 (정확도, 안정성, 피로도 등).
2. 사용자의 개선점 2~3가지를 짧고 명확하게 제시하세요.
3. 문장은 자연스러운 한국어로 작성하고, 200자 이내로 마무리하세요.
4. 최상위는 반드시 객체(Object) JSON으로만 출력하고, 아래 키만 포함하세요:
{{
  "overall_feedback": "문장",
  "summary_accuracy": <평균 정확도(숫자)>,
  "improvement_tips": ["tip1", "tip2"]
}}
"""

    try:
        resp = await model_quality.generate_content_async(prompt)
        raw = resp.text
        result = _force_object(raw)

        # 기본값/타입 정리
        result.setdefault("overall_feedback", "종합 피드백 생성 실패")
        result.setdefault("summary_accuracy", 0)
        result.setdefault("improvement_tips", [])
        if isinstance(result["improvement_tips"], str):
            result["improvement_tips"] = [result["improvement_tips"]]

        return result

    except Exception as e:
        print(f"--- GEMINI API ERROR (QUALITY) ---\nError: {e}\n--------------------------")
        if "resp" in locals() and hasattr(resp, "prompt_feedback"):
            print(f"Prompt Feedback: {resp.prompt_feedback}")
        return {"overall_feedback": "⚠️ 종합 피드백 생성 실패", "summary_accuracy": 0, "improvement_tips": []}
