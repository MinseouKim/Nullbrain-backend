# backend/app/logic/gemini.py
import os, asyncio
from dotenv import load_dotenv
import google.generativeai as genai

load_dotenv()

API_KEY = os.getenv("GOOGLE_API_KEY")
MODEL = os.getenv("GEMINI_MODEL", "models/gemini-2.5-flash")  # 'gemini-flash-latest' 도 호환됨
_NEW = None
ggenai = None


# 어떤 SDK가 설치돼 있는지 감지
_NEW = None
ggenai = None
try:
    # 신 SDK
    from google import genai as ggenai  # type: ignore
    _NEW = True
except Exception:
    try:
        # 구 SDK
        import google.generativeai as ggenai  # type: ignore
        _NEW = False
    except Exception:
        ggenai = None
        _NEW = None


_async_generate = None

if not API_KEY or ggenai is None:
    async def _async_generate(prompt: str) -> str:
        return "⚠️ Gemini API Key가 없어서 응답을 생성할 수 없습니다."
else:
    safety_settings = [
        {"category": "HARM_CATEGORY_HARASSMENT", "threshold": "BLOCK_NONE"},
        {"category": "HARM_CATEGORY_HATE_SPEECH", "threshold": "BLOCK_NONE"},
        {"category": "HARM_CATEGORY_SEXUALLY_EXPLICIT", "threshold": "BLOCK_NONE"},
        {"category": "HARM_CATEGORY_DANGEROUS_CONTENT", "threshold": "BLOCK_NONE"},
    ]
    generation_config = {
        "temperature": 0.7,
    }

    if _NEW:  # 신 SDK
        client = ggenai.Client(api_key=API_KEY)

        async def _async_generate(prompt: str) -> str:
            resp = await asyncio.to_thread(
                lambda: client.models.generate_content(
                    model=MODEL,
                    contents=prompt,
                    safety_settings=safety_settings,
                )
            )
            if getattr(resp, "text", None):
                return resp.text.strip()
            if getattr(resp, "candidates", None):
                for cand in resp.candidates:
                    if cand.content and cand.content.parts:
                        return cand.content.parts[0].text.strip()
            return "⚠️ AI가 응답을 생성하지 않았습니다."
    else:  # 구 SDK
        ggenai.configure(api_key=API_KEY)
        # 💡 중요: 모델 생성 시에는 config를 빼고, 안전 설정만 넣습니다.
        model = ggenai.GenerativeModel(
            MODEL,
            safety_settings=safety_settings,
        )

        async def _async_generate(prompt: str) -> str:
            # 💡 중요: API를 호출하는 이 시점에 generation_config를 직접 전달합니다.
            if hasattr(model, "generate_content_async"):
                resp = await model.generate_content_async(
                    prompt,
                    generation_config=generation_config
                )
            else:
                resp = await asyncio.to_thread(
                    model.generate_content,
                    prompt,
                    generation_config=generation_config
                )

            if getattr(resp, "text", None):
                return resp.text.strip()
            if getattr(resp, "candidates", None):
                for cand in resp.candidates:
                    if cand.content and cand.content.parts:
                        return cand.content.parts[0].text.strip()
            # 💡 상세한 오류 확인을 위해 응답 자체를 출력해볼 수 있습니다.
            print(f"Gemini 응답 없음. 전체 응답: {resp}")
            return "⚠️ AI가 응답을 생성하지 않았습니다."


async def get_conversational_feedback(
    exercise_name: str,
    angle: float | None,
    rep_counter: int, # 이 값은 참고용으로만 사용하도록 프롬프트를 수정합니다.
    stage: str,
    history: list,
    body_profile: dict | None = None,
) -> str:
    """
    체형 분석 정보를 바탕으로 명확한 판단과 구체적인 피드백을 요청합니다.
    """
    
    # 체형 정보가 있을 때만 프롬프트에 해당 섹션을 추가합니다.
    profile_section = ""
    if body_profile:
        profile_section = f"""
* 사용자의 체형 분석 정보:
{body_profile}
"""

    prompt = f"""
당신은 사용자의 체형 데이터를 기반으로 자세를 분석하는 전문 AI 퍼스널 트레이너입니다. 
주어진 정보를 바탕으로 사용자의 현재 운동 자세가 좋은지 나쁜지 명확하게 판단하고, 
구체적인 피드백을 딱 한 문장으로 제공하세요.

{profile_section}

* 현재 운동 정보:
- 운동 종류: {exercise_name}
- 현재 무릎 각도 (참고용): {int(angle) if angle is not None else 'N/A'}
- 현재 단계 (참고용): {stage}

* 피드백 생성 규칙:
1.  **가장 먼저 '자세가 좋습니다' 또는 '자세가 불안정합니다' 와 같이 명확한 판정으로 문장을 시작하세요.**
2.  왜 그렇게 판단했는지에 대한 **이유를 위 체형 분석 정보를 근거로** 간략하게 설명하세요. (예: "어깨 불균형 데이터에 따르면...")
3.  개선할 수 있는 **구체적이고 실행 가능한 팁**을 한 가지 제안하세요.
4.  전체 답변은 반드시 **한국어 한 문장, 70자 이내**로 매우 간결해야 합니다.
5.  '반복수'는 떨림 현상 때문에 부정확할 수 있으니 **절대 언급하지 마세요.**
6.  이모지, 마크다운, 줄바꿈을 사용하지 마세요.
"""
    try:
        return await _async_generate(prompt)
    except Exception as e:
        print("Gemini error:", e)
        return f"⚠️ Gemini 호출 실패: {e}"