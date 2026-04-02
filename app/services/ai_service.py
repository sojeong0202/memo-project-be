import hashlib
import json

from openai import AsyncOpenAI

from app.core.config import settings

client = AsyncOpenAI(api_key=settings.openai_api_key)

_SUMMARY_SCHEMA = {
    "name": "memo_analysis",
    "strict": True,
    "schema": {
        "type": "object",
        "properties": {
            "summary": {
                "type": "string",
                "description": "입력 텍스트를 한 문장으로 요약한 내용",
            },
            "keywords": {
                "type": "array",
                "items": {"type": "string"},
                "description": "핵심 키워드 1~2개",
            },
        },
        "required": ["summary", "keywords"],
        "additionalProperties": False,
    },
}

_SYSTEM_PROMPT = (
    "당신은 메모 분석 도우미입니다. "
    "입력된 텍스트를 한 문장으로 요약하고, 핵심 키워드를 1~2개 추출하세요. "
    "키워드는 명사 위주로 간결하게 작성하세요."
)


async def analyze_text(text: str) -> tuple[str, list[str]]:
    """텍스트를 요약하고 키워드를 추출한다. (summary, keywords) 반환"""
    response = await client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {"role": "system", "content": _SYSTEM_PROMPT},
            {"role": "user", "content": text},
        ],
        response_format={
            "type": "json_schema",
            "json_schema": _SUMMARY_SCHEMA,
        },
    )
    result = json.loads(response.choices[0].message.content)
    return result["summary"], result["keywords"]


def keyword_to_color(keyword: str) -> str:
    """키워드를 해싱하여 HEX 색상을 반환한다. 동일 키워드 → 항상 동일 색상."""
    digest = hashlib.md5(keyword.encode()).hexdigest()
    # 채도/명도가 적당한 파스텔 계열이 되도록 상위 6자리 사용
    r = int(digest[0:2], 16)
    g = int(digest[2:4], 16)
    b = int(digest[4:6], 16)
    # 너무 어둡거나 밝지 않도록 130~210 범위로 조정
    r = 130 + int(r * 80 / 255)
    g = 130 + int(g * 80 / 255)
    b = 130 + int(b * 80 / 255)
    return f"#{r:02X}{g:02X}{b:02X}"


async def get_embedding(text: str) -> list[float]:
    """텍스트를 1536차원 벡터로 변환한다."""
    response = await client.embeddings.create(
        model="text-embedding-3-small",
        input=text,
    )
    return response.data[0].embedding
