# backend/app/logic/gemini.py
import os, asyncio
from dotenv import load_dotenv

load_dotenv()

API_KEY = os.getenv("GOOGLE_API_KEY")
MODEL  = os.getenv("GEMINI_MODEL", "gemini-1.5-flash")  # 'gemini-flash-latest' 도 호환됨

# 어떤 SDK가 설치돼 있는지 감지
_NEW = None
ggenai = None
try:
    # 신 SDK (google-genai; 2024 하반기~)
    from google import genai as ggenai  # type: ignore
    _NEW = True
except Exception:
    try:
        # 구 SDK (google-generativeai)
        import google.generativeai as ggenai  # type: ignore
        _NEW = False
    except Exception:
        ggenai = None
        _NEW = None


def _fallback_feedback(exercise: str, angle, rep: int, stage: str) -> str:
    # API 키 없거나 SDK 문제 시 한 문장 피드백
    if exercise == "squat":
        if angle is None:
            return "무릎과 발끝을 같은 방향으로, 가슴을 펴고 중심은 뒤꿈치에 두세요."
        if stage == "down" and angle < 90:
            return "좋아요! 깊이는 충분해요. 무릎이 안쪽으로 모이지 않게 주의하세요."
        if angle > 160:
            return "너무 펴졌어요. 천천히 내려가며 코어에 힘 주세요."
        return "정면을 보고 가슴을 열고, 무릎-발끝 정렬을 유지하세요."
    if exercise == "pushup":
        if angle is None:
            return "머리·몸통·발목이 일직선이 되도록 코어에 힘 주세요."
        if stage == "down" and angle < 90:
            return "잘하고 있어요! 팔꿈치는 45° 정도 유지하며 가슴을 더 가까이 내려보세요."
        if angle > 160:
            return "팔이 과하게 펴졌어요. 다음 반복 준비해요."
        return "어깨를 내려 긴 목을 만들고, 몸통은 일직선 유지!"
    return "호흡을 고르고 정렬을 우선하세요."

# 신/구 SDK 각각 generate 함수 래핑
_async_generate = None

if not API_KEY or ggenai is None:
    # 키 없거나 SDK 자체가 없는 경우
    async def _async_generate(prompt: str) -> str:
        return ""
else:
    if _NEW:  # 신 SDK: from google import genai
        client = ggenai.Client(api_key=API_KEY)

        async def _async_generate(prompt: str) -> str:
            # 신 SDK는 동기 호출이므로 스레드로 우회
            resp = await asyncio.to_thread(
                lambda: client.models.generate_content(model=MODEL, contents=prompt)
            )
            # resp.text 가 없을 수 있어 안전하게 추출
            if getattr(resp, "text", None):
                return resp.text
            if getattr(resp, "candidates", None):
                try:
                    return resp.candidates[0].content.parts[0].text  # type: ignore
                except Exception:
                    pass
            return ""
    else:     # 구 SDK: import google.generativeai as genai
        ggenai.configure(api_key=API_KEY)
        # GenerationConfig 클래스를 안 써도 dict로 넣으면 동작(버전차 안전)
        model = ggenai.GenerativeModel(MODEL, generation_config={"max_output_tokens": 50})

        async def _async_generate(prompt: str) -> str:
            # 버전에 따라 async 메서드가 없을 수 있음 → 안전 처리
            if hasattr(model, "generate_content_async"):
                resp = await model.generate_content_async(prompt)  # type: ignore
            else:
                resp = await asyncio.to_thread(model.generate_content, prompt)
            return getattr(resp, "text", "") or ""


async def get_conversational_feedback(
    exercise_name: str,
    angle: float | None,
    rep_counter: int,
    stage: str,
    history: list,
) -> str:
    """단 한 문장의 한국어 코칭 문장 반환(에러/무키 시에도 안전)."""
    if not API_KEY or _NEW is None:
        # 키 없거나 SDK 미탑재
        return _fallback_feedback(exercise_name, angle, rep_counter, stage)

    # 매우 짧고 명확한 한 문장만 요청
    prompt = f"""
당신은 한국어 AI 트레이너입니다. 아래 정보를 바탕으로 격려 한 문장만 짧게 말하세요.
- 운동: {exercise_name}
- 반복수: {rep_counter}
- 단계: {stage}
- 각도/지표: {int(angle) if angle is not None else 'N/A'}
- 최근 대화 요약: {history[-6:] if history else []}

규칙:
- 한국어 한 문장, 60자 이내.
- 구체적이고 실행 가능한 팁 1개 포함.
- 이모지/마크다운/줄바꿈 금지.
예) 좋습니다! 무릎이 안으로 모이지 않게 발끝 방향 유지하세요.
"""

    try:
        text = await _async_generate(prompt)
        text = (text or "").strip()
        if not text:
            return _fallback_feedback(exercise_name, angle, rep_counter, stage)
        # 혹시 길면 한 문장으로 다듬기
        if "。" in text or "!" in text or "?" in text or "." in text:
            # 첫 문장만
            for sep in ["。", "!", "?", "."]:
                if sep in text:
                    text = text.split(sep)[0] + sep
                    break
        return text
    except Exception as e:
        print("Gemini error:", e)
        return _fallback_feedback(exercise_name, angle, rep_counter, stage)
