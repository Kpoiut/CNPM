"""
Nova Voice Assistant — Backend API Endpoints.
Handles: STT → LLM → TTS pipeline for Nova.
"""
import os
import uuid
import time
import base64
from typing import Optional
from datetime import datetime

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import StreamingResponse, JSONResponse
from fastapi import Header as FastAPIHeader
from pydantic import BaseModel

# Environment configuration
ANTHROPIC_API_KEY = os.environ.get("ANTHROPIC_API_KEY", os.environ.get("ANTHROPIC_AUTH_TOKEN", ""))
ANTHROPIC_BASE_URL = os.environ.get("ANTHROPIC_BASE_URL", "https://api.anthropic.com")
NOVA_MODEL = os.environ.get("NOVA_MODEL", "claude-sonnet-4-6")
NOVA_TTS_VOICE = os.environ.get("NOVA_TTS_VOICE", "audeai")
TIMEOUT_SECONDS = 30

from src.backend.config import limiter

router = APIRouter(prefix="/api/nova", tags=["nova"])

# ============================================================
# Schemas
# ============================================================

class ChatRequest(BaseModel):
    message: str
    context: Optional[dict] = None

class VoiceRequest(BaseModel):
    text: str  # Already STTed by frontend

class NovaStatusResponse(BaseModel):
    status: str
    model: str
    capabilities: list[str]
    voice_enabled: bool
    wake_word_enabled: bool
    timestamp: str

class NovaChatResponse(BaseModel):
    text: str
    action: Optional[dict] = None
    confidence: float
    request_id: str
    timestamp: str

# ============================================================
# Health & Status
# ============================================================

@router.get("/status", response_model=NovaStatusResponse)
async def get_nova_status(request: Request):
    """Check Nova assistant status and capabilities."""
    return NovaStatusResponse(
        status="ready",
        model=NOVA_MODEL,
        capabilities=[
            "text_chat",
            "voice_input",
            "property_valuation",
            "data_query",
            "scenario_analysis",
        ],
        voice_enabled=check_speech_support(request),
        wake_word_enabled=True,
        timestamp=datetime.now().isoformat(),
    )

def check_speech_support(request: Request) -> bool:
    """Check if client supports Web Speech API."""
    ua = request.headers.get("User-Agent", "").lower()
    # Web Speech API supported in modern browsers
    return not ("firefox" in ua and "mobile" in ua)

# ============================================================
# Text Chat (Main LLM Interaction)
# ============================================================

@router.post("/chat", response_model=NovaChatResponse)
@limiter.limit("20/minute")
async def nova_chat(req: ChatRequest, request: Request):
    """
    Nova text chat — routes to Claude LLM with real-estate context.
    Features:
    - Property valuation queries
    - Market data lookups
    - Scenario analysis
    - Tool calling for API operations
    """
    start_time = time.perf_counter()
    request_id = str(uuid.uuid4())[:8]

    # Build context-aware prompt
    system_prompt = build_nova_system_prompt()

    try:
        # Route to LLM
        response = await call_llm(
            system_prompt=system_prompt,
            user_message=req.message,
            context=req.context or {},
        )

        # Parse response and determine action
        action = parse_nova_action(response, req.message)

        response_time_ms = (time.perf_counter() - start_time) * 1000

        return NovaChatResponse(
            text=response,
            action=action,
            confidence=0.85,  # Placeholder — could add confidence scoring
            request_id=request_id,
            timestamp=datetime.now().isoformat(),
        )

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Nova error: {str(e)}"
        )

# ============================================================
# Voice Input (STT already done on frontend)
# ============================================================

@router.post("/voice")
@limiter.limit("20/minute")
async def nova_voice(req: VoiceRequest, request: Request):
    """
    Handle voice input that's already been transcribed by frontend Web Speech API.
    This endpoint receives the transcribed text and routes it like a chat message.
    """
    # Forward to chat with voice context flag
    chat_req = ChatRequest(
        message=req.text,
        context={"input_mode": "voice", "wake_word": "hey nova"}
    )
    return await nova_chat(chat_req, request)

# ============================================================
# LLM Integration (Anthropic Claude)
# ============================================================

async def call_llm(system_prompt: str, user_message: str, context: dict) -> str:
    """Call Anthropic Claude API with error handling."""

    if not ANTHROPIC_API_KEY:
        # Fallback mode for development without API key
        return fallback_response(user_message, context)

    import json
    import httpx

    headers = {
        "x-api-key": ANTHROPIC_API_KEY,
        "anthropic-version": "2023-06-01",
        "content-type": "application/json",
    }

    # Build conversation with real-estate context
    messages = [
        {"role": "user", "content": user_message}
    ]

    # Add context-aware instructions
    enhanced_user = f"{user_message}\n\n[Context: {json.dumps(context, ensure_ascii=True)}]"

    payload = {
        "model": NOVA_MODEL,
        "max_tokens": 1024,
        "system": system_prompt,
        "messages": [{"role": "user", "content": enhanced_user}],
    }

    async with httpx.AsyncClient(timeout=TIMEOUT_SECONDS) as client:
        response = await client.post(
            f"{ANTHROPIC_BASE_URL}/v1/messages",
            headers=headers,
            json=payload,
        )

        if response.status_code != 200:
            error_detail = response.text[:200]
            raise HTTPException(
                status_code=response.status_code,
                detail=f"LLM error: {error_detail}"
            )

        result = response.json()
        return result["content"][0]["text"]

def build_nova_system_prompt() -> str:
    """Build system prompt for Nova voice assistant."""
    return """Bạn là Nova — trợ lý AI cho hệ thống Real Estate AVM (Automated Valuation Model).

## Khả năng:
- Trả lời câu hỏi về giá bất động sản tại 6 khu vực: Cầu Giấy, Thanh Xuân, Đống Đa (Hà Nội) | Q7, Bình Thạnh, Tân Bình (HCM)
- Tư vấn mua/bán/nạp đầu tư bất động sản
- Phân tích thị trường và xu hướng giá
- Giải thích kết quả valuation model

## Phong cách:
- Thân thiện, chuyên nghiệp
- Dùng tiếng Việt, có thể dùng tiếng Anh khi cần
- Trả lời ngắn gọn, đi thẳng vào vấn đề
- Có thể đọc lại yêu cầu để xác nhận trước khi thực hiện

## Giới hạn:
- Chỉ hỗ trợ 6 khu vực trên
- Không đưa ra lời khuyên tài chính cụ thể (chỉ phân tích dữ liệu)
- Nếu không biết, nói rõ "Tôi không có thông tin về..."

## Tool calling:
Khi người dùng yêu cầu valuation/crawl data, trả lời với format:
```
[ACTION] valuation | district=X | property_type=Y | area=Z[/ACTION]
```
hoặc
```
[ACTION] lookup | province=X | district=Y | metric=Z[/ACTION]
```
"""

def parse_nova_action(response: str, original_message: str) -> Optional[dict]:
    """Parse action tags from LLM response."""
    import re

    # Look for [ACTION] tags
    action_match = re.search(r'\[ACTION\]\s*(\w+)\s*\|?\s*(.*?)\s*\[/ACTION\]', response)
    if action_match:
        action_type = action_match.group(1)
        params_str = action_match.group(2)

        # Parse key=value pairs
        params = {}
        for pair in params_str.split('|'):
            if '=' in pair:
                key, value = pair.split('=', 1)
                params[key.strip()] = value.strip()

        return {"type": action_type, "params": params}

    return None

def fallback_response(message: str, context: dict) -> str:
    """Fallback responses when no API key available."""
    msg_lower = message.lower()

    if any(kw in msg_lower for kw in ["giá", "valuation", "định giá", "price"]):
        return "Tôi có thể giúp bạn định giá bất động sản. Để valuation, tôi cần biết: khu vực, loại nhà đất, diện tích. Bạn muốn bắt đầu với thông tin nào?"

    if any(kw in msg_lower for kw in ["thị trường", "market", "xu hướng"]):
        return "Thị trường BĐS 6 khu vực đang có xu hướng tăng nhẹ. Bạn muốn xem chi tiết khu vực nào?"

    if any(kw in msg_lower for kw in ["chào", "hello", "hi"]):
        return "Xin chào! Tôi là Nova, trợ lý AVM. Tôi có thể giúp bạn định giá nhà đất tại Hà Nội và HCM. Bạn cần hỗ trợ gì?"

    return "Tôi hiểu bạn muốn hỏi về: " + message[:50] + "... Để tôi hỗ trợ chính xác hơn, bạn có thể nói rõ khu vực và loại bất động sản không?"

# ============================================================
# Error Handling
# ============================================================

@router.get("/health")
async def nova_health():
    """Lightweight health check."""
    return {
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "api_key_configured": bool(ANTHROPIC_API_KEY),
    }