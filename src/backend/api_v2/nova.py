"""
Nova Voice Assistant — Backend API Endpoints.
Handles text chat and voice-transcribed commands for the Real Estate AVM UI.
"""
import json
import os
import asyncio
import shutil
import subprocess
import time
import uuid
import re
from datetime import datetime
from functools import lru_cache
from pathlib import Path
from typing import Any, Optional

from fastapi import APIRouter, Body, Depends, HTTPException, Request
from pydantic import BaseModel, Field
from sqlalchemy import text as sql_text

from src.backend.config import limiter
from src.backend.database import engine

# Auth gating cho thực thi tác vụ (agentic) — chỉ admin mới chạy được.
from src.backend.auth.dependencies import require_admin
from src.backend.auth.models import User as _AuthUser

# Environment configuration. Keys are read at request time; no key is embedded
# in source code and no key is returned in responses.
OPENAI_BASE_URL = os.environ.get("OPENAI_BASE_URL", "https://api.openai.com")
NOVA_TTS_VOICE = os.environ.get("NOVA_TTS_VOICE", "audeai")
TIMEOUT_SECONDS = min(int(os.environ.get("NOVA_TIMEOUT_SECONDS", "12")), 12)
PROJECT_ROOT = Path(__file__).resolve().parents[3]

router = APIRouter(prefix="/api/nova", tags=["nova"])


class NovaAttachment(BaseModel):
    id: Optional[str] = None
    kind: str = "file"
    name: str
    relativePath: Optional[str] = None
    mime: Optional[str] = None
    size: int = 0
    dataUrl: Optional[str] = None
    textPreview: Optional[str] = None


class ChatRequest(BaseModel):
    message: str
    context: Optional[dict] = None
    attachments: list[NovaAttachment] | None = Field(default_factory=list)


class VoiceRequest(BaseModel):
    text: str


class NovaExecuteRequest(BaseModel):
    """Yêu cầu thực thi tác vụ agentic do người dùng xác nhận từ chat."""
    action: str
    params: Optional[dict] = None


NovaAttachment.model_rebuild()
ChatRequest.model_rebuild()
VoiceRequest.model_rebuild()
NovaExecuteRequest.model_rebuild()


class NovaStatusResponse(BaseModel):
    status: str
    model: str
    provider: str
    api_key_configured: bool
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


@lru_cache(maxsize=1)
def _project_env() -> dict[str, str]:
    env_path = PROJECT_ROOT / ".env"
    values: dict[str, str] = {}
    try:
        for raw in env_path.read_text(encoding="utf-8-sig").splitlines():
            line = raw.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, value = line.split("=", 1)
            values[key.strip()] = value.strip().strip('"').strip("'")
    except Exception:
        pass
    return values


def _project_or_os(name: str) -> str:
    return _project_env().get(name) or os.environ.get(name, "")


@lru_cache(maxsize=1)
def _local_claude_env() -> dict[str, str]:
    """Read local Claude settings without printing or persisting any secret."""
    settings_path = Path.home() / ".claude" / "settings.json"
    try:
        data = json.loads(settings_path.read_text(encoding="utf-8"))
        env = data.get("env", {}) if isinstance(data, dict) else {}
        return {str(k): str(v) for k, v in env.items() if v is not None}
    except Exception:
        return {}


def _env_or_claude(name: str) -> str:
    return _project_env().get(name) or os.environ.get(name) or _local_claude_env().get(name, "")


def _anthropic_key() -> str:
    return _project_or_os("ANTHROPIC_API_KEY") or _env_or_claude("ANTHROPIC_AUTH_TOKEN")


def _anthropic_uses_bearer() -> bool:
    return bool(_env_or_claude("ANTHROPIC_AUTH_TOKEN") and not _project_or_os("ANTHROPIC_API_KEY"))


def _anthropic_base_url() -> str:
    if _project_or_os("ANTHROPIC_API_KEY"):
        return _project_or_os("ANTHROPIC_BASE_URL") or "https://api.anthropic.com"
    local_base = _local_claude_env().get("ANTHROPIC_BASE_URL")
    env_base = _project_or_os("ANTHROPIC_BASE_URL")
    if local_base and (not env_base or env_base == "https://api.anthropic.com"):
        return local_base
    return env_base or local_base or "https://api.anthropic.com"


def _openai_key() -> str:
    return _project_or_os("OPENAI_API_KEY")


def _claude_cli_available() -> bool:
    return bool(shutil.which("claude"))


def _claude_cli_enabled() -> bool:
    return _project_or_os("NOVA_ENABLE_CLAUDE_CLI_BRIDGE").lower() in {"1", "true", "yes"}


def _provider() -> str:
    if _anthropic_key():
        return "anthropic"
    if _openai_key():
        return "openai"
    if _claude_cli_enabled() and _claude_cli_available():
        return "claude_cli"
    return "offline"


def _model_name() -> str:
    provider = _provider()
    if provider in {"anthropic", "claude_cli"}:
        project_model = _project_env().get("NOVA_MODEL") or _project_env().get("ANTHROPIC_MODEL")
        if project_model:
            return project_model
        explicit_model = os.environ.get("NOVA_MODEL") or os.environ.get("ANTHROPIC_MODEL")
        local_opus = _env_or_claude("ANTHROPIC_DEFAULT_OPUS_MODEL")
        if explicit_model and explicit_model != "claude-sonnet-4-6":
            return explicit_model
        return local_opus or explicit_model or _env_or_claude("ANTHROPIC_DEFAULT_SONNET_MODEL") or "claude-opus-4-8"
    if provider == "openai":
        return os.environ.get("NOVA_MODEL") or os.environ.get("OPENAI_MODEL", "gpt-4o-mini")
    return "offline-project-context"


def _anthropic_model_candidates() -> list[str]:
    project_model = _project_env().get("NOVA_MODEL") or _project_env().get("ANTHROPIC_MODEL")
    if project_model:
        models = [project_model, _env_or_claude("ANTHROPIC_DEFAULT_HAIKU_MODEL")]
        seen: set[str] = set()
        return [m for m in models if m and not (m in seen or seen.add(m))]
    models = [
        _model_name(),
        _env_or_claude("ANTHROPIC_DEFAULT_SONNET_MODEL"),
        _env_or_claude("ANTHROPIC_DEFAULT_HAIKU_MODEL"),
    ]
    seen: set[str] = set()
    return [m for m in models if m and not (m in seen or seen.add(m))]


def _anthropic_image_model_candidates() -> list[str]:
    models = [
        _project_or_os("NOVA_VISION_MODEL"),
        _env_or_claude("ANTHROPIC_DEFAULT_OPUS_MODEL"),
        _model_name(),
        _env_or_claude("ANTHROPIC_DEFAULT_SONNET_MODEL"),
        _env_or_claude("ANTHROPIC_DEFAULT_HAIKU_MODEL"),
        "claude-opus-4-8",
    ]
    seen: set[str] = set()
    return [m for m in models if m and not (m in seen or seen.add(m))]


def _image_input_enabled() -> bool:
    return _project_or_os("NOVA_ENABLE_IMAGE_INPUT").lower() in {"1", "true", "yes"}


def _looks_like_image_refusal(text: str) -> bool:
    low = text.lower()
    return (
        "text-only model" in low
        or "cannot read attached files" in low
        or "cannot view" in low and ("image" in low or "attached" in low)
        or "can't view" in low and ("image" in low or "attached" in low)
    )


def _extract_anthropic_text(result: dict[str, Any]) -> str:
    parts: list[str] = []
    for block in result.get("content", []):
        if isinstance(block, dict):
            text = block.get("text") or block.get("content")
            if isinstance(text, str) and text.strip():
                parts.append(text.strip())
        elif isinstance(block, str) and block.strip():
            parts.append(block.strip())
    if parts:
        return "\n".join(parts)
    if isinstance(result.get("completion"), str):
        return result["completion"]
    raise HTTPException(status_code=502, detail="Anthropic API returned no text block")


@router.get("/status", response_model=NovaStatusResponse)
async def get_nova_status(request: Request):
    provider = _provider()
    capabilities = [
        "text_chat",
        "voice_input",
        "image_context",
        "folder_manifest_context",
        "project_context",
        "property_valuation_guidance",
        "data_query_guidance",
        "scenario_analysis",
    ]
    if _claude_cli_enabled():
        capabilities.append("claude_cli_bridge")
    return NovaStatusResponse(
        status="ready" if provider != "offline" else "offline_context",
        model=_model_name(),
        provider=provider,
        api_key_configured=provider != "offline",
        capabilities=capabilities,
        voice_enabled=check_speech_support(request),
        wake_word_enabled=True,
        timestamp=datetime.now().isoformat(),
    )


def check_speech_support(request: Request) -> bool:
    ua = request.headers.get("User-Agent", "").lower()
    return not ("firefox" in ua and "mobile" in ua)


@router.post("/chat", response_model=NovaChatResponse)
@limiter.limit("20/minute")
async def nova_chat(request: Request, req: ChatRequest = Body(...)):
    request_id = str(uuid.uuid4())[:8]
    message = req.message.strip()
    if not message:
        raise HTTPException(status_code=400, detail="Message is empty")

    system_prompt = build_nova_system_prompt()
    context = req.context or {}
    context["project_snapshot"] = get_project_snapshot()
    attachments = req.attachments or []
    context["attachments"] = attachment_context(attachments)

    try:
        fast_response = project_fast_response(message, context, attachments)
        if fast_response:
            return NovaChatResponse(
                text=fast_response,
                action=parse_nova_action(fast_response, message) or propose_nova_action(message, context),
                confidence=0.84,
                request_id=request_id,
                timestamp=datetime.now().isoformat(),
            )
        response = await call_llm(system_prompt, message, context, attachments)
        action = parse_nova_action(response, message) or propose_nova_action(message, context)
        response = strip_nova_actions(response)
        return NovaChatResponse(
            text=response,
            action=action,
            confidence=0.86 if _provider() != "offline" else 0.62,
            request_id=request_id,
            timestamp=datetime.now().isoformat(),
        )
    except HTTPException as exc:
        rescue = project_fast_response(message, context, attachments) or fallback_response(message, context, attachments, provider_failed=True)
        if rescue:
            return NovaChatResponse(
                text=rescue,
                action=parse_nova_action(rescue, message),
                confidence=0.72,
                request_id=request_id,
                timestamp=datetime.now().isoformat(),
            )
        if _provider() != "offline":
            detail = str(exc.detail)[:220] if getattr(exc, "detail", None) else "provider không phản hồi"
            response = (
                "Nova chưa kết nối được AI provider thật nên tôi không trả lời giả lập. "
                f"Kiểm tra ANTHROPIC_AUTH_TOKEN/ANTHROPIC_BASE_URL/NOVA_MODEL ở backend. Chi tiết kỹ thuật: {detail}"
            )
            return NovaChatResponse(
                text=response,
                action=None,
                confidence=0.15,
                request_id=request_id,
                timestamp=datetime.now().isoformat(),
            )
        response = fallback_response(message, context, attachments, provider_failed=True)
        return NovaChatResponse(
            text=response,
            action=None,
            confidence=0.58,
            request_id=request_id,
            timestamp=datetime.now().isoformat(),
        )
    except Exception as e:
        detail = str(e) or type(e).__name__
        return NovaChatResponse(
            text=f"Nova đang khởi động lại hoặc provider vừa ngắt giữa chừng. Thử gửi lại sau vài giây. Chi tiết: {detail}",
            action=None,
            confidence=0.1,
            request_id=request_id,
            timestamp=datetime.now().isoformat(),
        )


@router.post("/voice")
@limiter.limit("20/minute")
async def nova_voice(request: Request, req: VoiceRequest = Body(...)):
    chat_req = ChatRequest(
        message=req.text,
        context={"input_mode": "voice", "wake_word": "hey nova"},
    )
    return await nova_chat(request, chat_req)


# Tác vụ an toàn (read-only / có thể đảo ngược) mà Nova được phép thực thi từ chat.
NOVA_SAFE_ACTIONS: dict[str, str] = {
    "mlops_drift": "Đo data drift (PSI) trực tiếp",
    "mlops_experiments": "Xem leaderboard các lần train",
    "mlops_registry": "Liệt kê model registry + version active",
    "mlops_monitor": "Health-check model đang phục vụ",
    "model_reload": "Reload cache model của backend",
}


def _nova_model_health() -> str:
    """Load model đang phục vụ + smoke predict (giống mlops monitor, chạy in-process)."""
    import pickle
    models_dir = PROJECT_ROOT / "models"
    active = _active_model_stamp()
    rows = _models_index()
    if active:
        model_file = f"model_{active}.pkl"
    elif rows:
        model_file = rows[0]["stamp"] and f"model_{rows[0]['stamp']}.pkl"
    else:
        return "HEALTH: FAIL — không có model nào."
    path = models_dir / model_file
    if not path.exists():
        return f"HEALTH: FAIL — không thấy {model_file}."
    try:
        with open(path, "rb") as f:
            data = pickle.load(f)
    except Exception as exc:
        return f"HEALTH: FAIL — không load được model: {exc}"
    model = data.get("model")
    feats = data.get("feature_names", [])
    if model is None or not feats:
        return "HEALTH: FAIL — bundle thiếu model/feature_names."
    try:
        import numpy as np
        n_in = int(getattr(model, "n_features_in_", 0) or 0) or len(feats)
        pred = model.predict(np.zeros((1, n_in), dtype=float))
        return (f"🩺 HEALTH OK — {model_file}\n"
                f"• Estimator: {type(model).__name__}, {n_in} features\n"
                f"• Smoke predict: {_fmt_billion(float(pred[0]))}\n"
                f"• Size: {path.stat().st_size / 1e6:.1f} MB")
    except Exception as exc:
        return f"HEALTH: FAIL — smoke predict lỗi: {exc}"


def _nova_run_action(action: str) -> str:
    """Thực thi in-process một tác vụ an toàn và trả text kết quả thật."""
    if action == "mlops_drift":
        summary = _quick_drift_summary()
        return f"📉 Kết quả drift vừa chạy: {summary}" if summary else "Chưa đủ dữ liệu để đo drift."
    if action == "mlops_monitor":
        return _nova_model_health()
    if action in ("mlops_experiments", "mlops_registry"):
        rows = _models_index()
        if not rows:
            return "Chưa có model nào trong registry."
        active = _active_model_stamp()
        lines = [f"📦 Registry — {len(rows)} version (active: {active or 'auto latest'}):"]
        for r in rows[:8]:
            r2 = f"{r['test_r2']:.3f}" if isinstance(r.get("test_r2"), (int, float)) else "—"
            mape = f"{r['test_mape']:.2f}%" if isinstance(r.get("test_mape"), (int, float)) else "—"
            mark = " ◀ active" if r["stamp"] == active else ""
            lines.append(f"• {r['stamp']} — {r['best_model']} MAPE={mape} R²={r2} MAE={_fmt_billion(r.get('test_mae'))}{mark}")
        return "\n".join(lines)
    if action == "model_reload":
        from src.backend.deps import clear_model_cache
        clear_model_cache()
        return "♻️ Đã xóa cache model. Lần predict tiếp theo sẽ nạp lại model mới nhất/đang pin."
    return "Hành động không được hỗ trợ."


@router.post("/execute")
@limiter.limit("12/minute")
async def nova_execute(
    request: Request,
    req: NovaExecuteRequest = Body(...),
    admin: _AuthUser = Depends(require_admin),
):
    """Thực thi tác vụ agentic an toàn (admin-only, server-side verified)."""
    action = (req.action or "").strip()
    if action not in NOVA_SAFE_ACTIONS:
        raise HTTPException(status_code=400, detail="Hành động này không được phép thực thi từ chat.")
    try:
        result_text = _nova_run_action(action)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Lỗi khi thực thi: {exc}")
    return {
        "ok": True,
        "action": action,
        "label": NOVA_SAFE_ACTIONS[action],
        "text": result_text,
        "executed_by": admin.username,
        "timestamp": datetime.now().isoformat(),
    }


async def call_llm(system_prompt: str, user_message: str, context: dict, attachments: list[NovaAttachment]) -> str:
    provider = _provider()
    if provider == "anthropic":
        try:
            return await call_anthropic(system_prompt, user_message, context, attachments)
        except HTTPException:
            if _claude_cli_enabled():
                return await call_claude_cli(system_prompt, user_message, context, attachments)
            raise
    if provider == "openai":
        try:
            return await call_openai(system_prompt, user_message, context, attachments)
        except HTTPException:
            if _claude_cli_enabled():
                return await call_claude_cli(system_prompt, user_message, context, attachments)
            raise
    if provider == "claude_cli":
        return await call_claude_cli(system_prompt, user_message, context, attachments)
    return fallback_response(user_message, context, attachments)


async def call_anthropic(system_prompt: str, user_message: str, context: dict, attachments: list[NovaAttachment]) -> str:
    import httpx

    enhanced_user = f"{user_message}\n\n[Project context JSON]\n{json.dumps(context, ensure_ascii=False)}"
    content: str | list[dict[str, Any]] = enhanced_user
    image_blocks = anthropic_image_blocks(attachments) if _image_input_enabled() else []
    if image_blocks:
        content = [{"type": "text", "text": enhanced_user}, *image_blocks]
    headers = {"anthropic-version": "2023-06-01", "content-type": "application/json"}
    if _anthropic_uses_bearer():
        headers["Authorization"] = f"Bearer {_anthropic_key()}"
    else:
        headers["x-api-key"] = _anthropic_key()

    last_error: HTTPException | None = None
    async with httpx.AsyncClient(timeout=TIMEOUT_SECONDS) as client:
        candidates = _anthropic_image_model_candidates() if image_blocks else _anthropic_model_candidates()
        for model in candidates:
            payload = {
                "model": model,
                "max_tokens": 650,
                "system": system_prompt,
                "messages": [{"role": "user", "content": content}],
            }
            try:
                response = await client.post(f"{_anthropic_base_url().rstrip('/')}/v1/messages", headers=headers, json=payload)
            except httpx.TimeoutException:
                last_error = HTTPException(status_code=504, detail=f"Anthropic API timeout on {model}")
                continue
            if response.status_code == 200:
                result = response.json()
                text = _extract_anthropic_text(result)
                if image_blocks and _looks_like_image_refusal(text):
                    last_error = HTTPException(status_code=502, detail=f"Anthropic image input refused on {model}")
                    continue
                return text
            last_error = HTTPException(
                status_code=response.status_code,
                detail=f"Anthropic API error on {model}: {response.text[:300]}",
            )
            if response.status_code in {401, 403}:
                break
    raise last_error or HTTPException(status_code=502, detail="Anthropic API did not return text")


async def call_openai(system_prompt: str, user_message: str, context: dict, attachments: list[NovaAttachment]) -> str:
    import httpx

    enhanced_user = f"{user_message}\n\n[Project context JSON]\n{json.dumps(context, ensure_ascii=False)}"
    input_content: str | list[dict[str, str]] = enhanced_user
    image_blocks = openai_image_blocks(attachments)
    if image_blocks:
        input_content = [{"type": "input_text", "text": enhanced_user}, *image_blocks]
    payload = {
        "model": _model_name(),
        "instructions": system_prompt,
        "input": [{"role": "user", "content": input_content}] if image_blocks else enhanced_user,
        "max_output_tokens": 1100,
    }
    headers = {
        "Authorization": f"Bearer {_openai_key()}",
        "content-type": "application/json",
    }

    async with httpx.AsyncClient(timeout=TIMEOUT_SECONDS) as client:
        response = await client.post(f"{OPENAI_BASE_URL}/v1/responses", headers=headers, json=payload)
    if response.status_code != 200:
        raise HTTPException(status_code=response.status_code, detail=f"OpenAI API error: {response.text[:300]}")
    result = response.json()
    if result.get("output_text"):
        return result["output_text"]

    parts: list[str] = []
    for item in result.get("output", []):
        for content in item.get("content", []):
            if content.get("text"):
                parts.append(content["text"])
    if parts:
        return "\n".join(parts)
    raise HTTPException(status_code=502, detail="OpenAI API did not return text output")


async def call_claude_cli(system_prompt: str, user_message: str, context: dict, attachments: list[NovaAttachment]) -> str:
    """Use the local Claude CLI auth as a secure bridge without exposing any key."""
    if not _claude_cli_available():
        raise HTTPException(status_code=503, detail="Claude CLI is not available")

    safe_context = dict(context)
    safe_context["attachments"] = attachment_context(attachments)
    prompt = (
        f"{system_prompt}\n\n"
        "Yêu cầu bắt buộc: trả lời như một trợ lý AI thật, linh hoạt, không lặp lại mẫu cố định. "
        "Nếu câu hỏi liên quan dự án, dựa vào Project context JSON; nếu thiếu dữ liệu thì hỏi ngắn gọn trường còn thiếu.\n\n"
        f"Người dùng: {user_message}\n\n"
        f"[Project context JSON]\n{json.dumps(safe_context, ensure_ascii=False)}"
    )
    command = [
        "claude",
        "-p",
        prompt,
        "--model",
        _model_name(),
        "--output-format",
        "text",
    ]
    max_budget = os.environ.get("NOVA_CLAUDE_CLI_MAX_BUDGET_USD")
    if max_budget:
        command.extend(["--max-budget-usd", max_budget])

    try:
        proc = await asyncio.create_subprocess_exec(
            *command,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
        stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=TIMEOUT_SECONDS + 20)
    except asyncio.TimeoutError as exc:
        raise HTTPException(status_code=504, detail="Claude CLI timeout") from exc
    except Exception as exc:
        raise HTTPException(status_code=503, detail=f"Claude CLI error: {type(exc).__name__}") from exc

    text = stdout.decode("utf-8", errors="replace").strip()
    if proc.returncode != 0 or not text:
        detail = stderr.decode("utf-8", errors="replace").strip()[:220] or "Claude CLI did not return text"
        raise HTTPException(status_code=502, detail=detail)
    return text


def parse_data_url(data_url: str | None) -> tuple[str, str] | None:
    if not data_url:
        return None
    match = re.match(r"^data:([^;]+);base64,(.+)$", data_url, re.DOTALL)
    if not match:
        return None
    media_type = match.group(1)
    payload = match.group(2)
    if media_type not in {"image/png", "image/jpeg", "image/webp", "image/gif"}:
        return None
    return media_type, payload


def anthropic_image_blocks(attachments: list[NovaAttachment]) -> list[dict[str, Any]]:
    blocks: list[dict[str, Any]] = []
    for item in attachments[:4]:
        parsed = parse_data_url(item.dataUrl)
        if not parsed:
            continue
        media_type, payload = parsed
        blocks.append({
            "type": "image",
            "source": {
                "type": "base64",
                "media_type": media_type,
                "data": payload,
            },
        })
    return blocks


def openai_image_blocks(attachments: list[NovaAttachment]) -> list[dict[str, str]]:
    blocks: list[dict[str, str]] = []
    for item in attachments[:4]:
        parsed = parse_data_url(item.dataUrl)
        if not parsed:
            continue
        blocks.append({"type": "input_image", "image_url": item.dataUrl or ""})
    return blocks


def attachment_context(attachments: list[NovaAttachment]) -> list[dict[str, Any]]:
    safe: list[dict[str, Any]] = []
    for item in attachments[:80]:
        safe.append({
            "kind": item.kind,
            "name": item.name,
            "relative_path": item.relativePath,
            "mime": item.mime,
            "size": item.size,
            "has_image_payload": bool(parse_data_url(item.dataUrl)),
            "text_preview": (item.textPreview or "")[:1800],
        })
    return safe


def build_nova_system_prompt() -> str:
    return """Bạn là Nova — trợ lý AI thông minh trong ứng dụng Real Estate AVM.

Bối cảnh dự án chỉ dùng khi câu hỏi liên quan bất động sản hoặc cách chạy hệ thống:
 - Dự án định giá bất động sản bằng FastAPI + React/Vite + PostgreSQL/PostGIS + ML model.
- Scope dữ liệu chính: Hà Nội (Cầu Giấy, Thanh Xuân, Đống Đa) và TP.HCM (Quận 7, Bình Thạnh, Tân Bình).
- Output chính: market valuation, adjustment ledger, fit suitability, comparable reasoning.
- Với câu hỏi BĐS, ưu tiên dữ liệu và cấu hình trong Project context JSON được gửi kèm.
- Nếu người dùng gửi ảnh/file/thư mục, dùng attachment metadata, text_preview và ảnh hợp lệ để phân tích; không bịa nội dung ngoài dữ liệu nhận được.

Cách trả lời:
- Trả lời tiếng Việt tự nhiên, thông minh, đúng trọng tâm.
- Câu hỏi ngoài BĐS như toán, lập trình, giải thích khái niệm, trò chuyện thường: trả lời trực tiếp như một AI tổng quát; không kéo về Real Estate AVM.
- Không tự chèn đoạn giới thiệu, disclaimer, hoặc câu kiểu "tôi dùng database/không bịa số liệu" trừ khi người dùng hỏi về nguồn dữ liệu, độ tin cậy hoặc cách hệ thống hoạt động.
- Phân quyền theo Project context JSON:
  * auth_user.role = "admin": nói như cộng tác viên nội bộ, có thể phân tích sâu cấu trúc dữ liệu, model, thống kê toàn bộ scope và luồng kỹ thuật. Vẫn tuyệt đối không tiết lộ API key, token, secret hoặc nội dung .env thật.
  * auth_user.role khác "admin": nói như tư vấn viên cho khách hàng, chỉ dùng dữ liệu nội bộ để tư vấn; không in raw dataset, source_url, record list, cấu hình nhạy cảm, model internals chi tiết hoặc thống kê toàn bộ dự án ra chat.
- Ưu tiên 3-6 câu hoặc bullet ngắn; chỉ dùng bảng khi người dùng yêu cầu.
- Trò chuyện tự nhiên với câu hỏi bình thường; tuyệt đối không trả lời kiểu mẫu lặp lại.
- Nếu người dùng hỏi cách chạy app/env, nêu đúng biến môi trường cần set.
- Nếu hỏi định giá và thiếu dữ liệu, vẫn đưa nhận định sơ bộ theo dữ liệu có sẵn, rồi hỏi thêm các trường thiếu: tỉnh/thành, quận, loại BĐS, diện tích, mặt tiền, pháp lý, vị trí.
- Nếu người dùng hỏi "tìm", "so sánh", "xu hướng", hãy chủ động dùng dữ liệu project_snapshot để trả lời phần có thể biết ngay rồi hỏi thêm phần còn thiếu.
- Với ảnh nhà đất, nếu không đọc được ảnh trực tiếp nhưng tên file/metadata có khu vực, hãy trả lời theo khu vực đó và yêu cầu thêm diện tích, hẻm/mặt tiền, pháp lý.
- Không bịa số liệu ngoài dữ liệu dự án; nếu chưa có dữ liệu thì nói rõ.
- Không đưa lời khuyên tài chính tuyệt đối; chỉ phân tích dữ liệu và rủi ro.

Action tags khi cần UI thực hiện tác vụ:
[ACTION] valuation | district=X | property_type=Y | area=Z[/ACTION]
[ACTION] lookup | province=X | district=Y | metric=Z[/ACTION]
"""


@lru_cache(maxsize=1)
def get_project_snapshot() -> dict:
    snapshot = {
        "scope": ["Cầu Giấy", "Thanh Xuân", "Đống Đa", "Quận 7", "Bình Thạnh", "Tân Bình"],
        "database_dialect": engine.dialect.name,
    }
    try:
        with engine.connect() as conn:
            snapshot["property_count"] = conn.execute(sql_text("SELECT COUNT(*) FROM properties")).scalar_one()
            rows = conn.execute(
                sql_text(
                    """
                    SELECT province_city, district, COUNT(*)
                    FROM properties
                    GROUP BY province_city, district
                    ORDER BY COUNT(*) DESC
                    LIMIT 12
                    """
                )
            ).all()
            snapshot["top_districts"] = [
                {"province": row[0], "district": row[1], "records": row[2]}
                for row in rows
            ]
    except Exception as exc:
        snapshot["database_error"] = str(exc)

    models_dir = PROJECT_ROOT / "models"
    try:
        if models_dir.exists():
            latest_meta = sorted(models_dir.glob("metadata_*.json"), key=lambda p: p.stat().st_mtime, reverse=True)[:1]
            latest_model = sorted(models_dir.glob("model_*.pkl"), key=lambda p: p.stat().st_mtime, reverse=True)[:1]
            snapshot["latest_metadata"] = latest_meta[0].name if latest_meta else None
            snapshot["latest_model"] = latest_model[0].name if latest_model else None
    except Exception as exc:
        snapshot["model_error"] = str(exc)
    return snapshot


def parse_nova_action(response: str, original_message: str) -> Optional[dict]:
    import re

    action_match = re.search(r"\[ACTION\]\s*(\w+)\s*\|?\s*(.*?)\s*\[/ACTION\]", response)
    if not action_match:
        return None

    params = {}
    for pair in action_match.group(2).split("|"):
        if "=" in pair:
            key, value = pair.split("=", 1)
            params[key.strip()] = value.strip()
    return {"type": action_match.group(1), "params": params}


def strip_nova_actions(response: str) -> str:
    return re.sub(r"\[ACTION\].*?\[/ACTION\]", "", response, flags=re.DOTALL).strip()


def _auth_role(context: dict | None) -> str:
    if not isinstance(context, dict):
        return "user"
    auth_user = context.get("auth_user")
    if isinstance(auth_user, dict):
        return str(auth_user.get("role") or "user").lower()
    return str(context.get("user_role") or "user").lower()


def _is_admin_context(context: dict | None) -> bool:
    return _auth_role(context) == "admin"


def _asks_internal_data(text: str) -> bool:
    keys = [
        "nguồn dữ liệu", "nguon du lieu", "dataset", "database", "db",
        "in dữ liệu", "in du lieu", "xuất dữ liệu", "xuat du lieu", "dump",
        "full dữ liệu", "full du lieu", "100%", "toàn bộ dữ liệu", "toan bo du lieu",
        "record", "bản ghi", "ban ghi", "source_url", "raw_source", "schema",
        "model internals", "metadata", "training data", "dữ liệu dự án", "du lieu du an",
    ]
    return any(k in text for k in keys)


def _asks_secret(text: str) -> bool:
    keys = [
        "api key", "apikey", "secret", "token", ".env", "anthropic_auth_token",
        "anthropic_api_key", "openai_api_key", "jwt_secret", "mật khẩu", "mat khau",
        "key thật", "key that", "lộ key", "lo key",
    ]
    return any(k in text for k in keys)


def _compact_text(message: str, attachments: list[NovaAttachment] | None = None) -> str:
    text = message.lower()
    for item in attachments or []:
        text += " " + " ".join([
            (item.name or "").lower(),
            (item.relativePath or "").lower(),
            (item.textPreview or "").lower()[:300],
        ])
    replacements = {
        "-": " ", "_": " ", ".": " ", "/": " ",
        "quan 7": "quận 7", "q7": "quận 7", "cap 7": "quận 7", "cấp 7": "quận 7",
        "cau giay": "cầu giấy", "thanh xuan": "thanh xuân", "dong da": "đống đa",
        "binh thanh": "bình thạnh", "tan binh": "tân bình",
    }
    for old, new in replacements.items():
        text = text.replace(old, new)
    return re.sub(r"\s+", " ", text).strip()


def _infer_district(message: str, attachments: list[NovaAttachment] | None = None) -> str | None:
    text = _compact_text(message, attachments)
    aliases = {
        "Quận 7": ["quận 7"],
        "Quận Cầu Giấy": ["cầu giấy"],
        "Quận Thanh Xuân": ["thanh xuân"],
        "Quận Đống Đa": ["đống đa"],
        "Quận Bình Thạnh": ["bình thạnh"],
        "Quận Tân Bình": ["tân bình"],
    }
    for district, keys in aliases.items():
        if any(k in text for k in keys):
            return district
    return None


def _recent_user_text(context: dict | None) -> str:
    if not isinstance(context, dict):
        return ""
    history = context.get("recent_messages") or []
    parts = []
    for item in history:
        if not isinstance(item, dict) or item.get("role") != "user":
            continue
        parts.append(str(item.get("text") or ""))
        for att in item.get("attachments") or []:
            if isinstance(att, dict):
                parts.append(str(att.get("name") or ""))
                parts.append(str(att.get("relativePath") or ""))
    return " ".join(parts)


def _fmt_billion(value: float | int | None) -> str:
    if not value:
        return "chưa đủ dữ liệu"
    return f"{float(value) / 1_000_000_000:.2f} tỷ"


def _fmt_million(value: float | int | None) -> str:
    if not value:
        return "chưa đủ dữ liệu"
    millions = float(value) / 1_000_000
    return f"{millions:.1f} triệu/m²" if abs(millions - round(millions)) >= 0.05 else f"{millions:.0f} triệu/m²"


def _percentile(values: list[float], p: float) -> float | None:
    if not values:
        return None
    values = sorted(values)
    if len(values) == 1:
        return values[0]
    pos = (len(values) - 1) * p
    lo = int(pos)
    hi = min(lo + 1, len(values) - 1)
    frac = pos - lo
    return values[lo] * (1 - frac) + values[hi] * frac


@lru_cache(maxsize=1)
def _market_stats() -> dict[str, Any]:
    stats: dict[str, Any] = {"districts": {}, "total": 0}
    try:
        with engine.connect() as conn:
            rows = conn.execute(
                sql_text(
                    """
                SELECT province_city, district, property_type, area_m2, price, price_per_m2
                FROM properties
                WHERE record_status != 'archived'
                  AND price IS NOT NULL AND price > 0
                  AND area_m2 IS NOT NULL AND area_m2 > 0
                  AND price_per_m2 IS NOT NULL AND price_per_m2 > 0
                    """
                )
            ).mappings().all()
    except Exception:
        return stats

    stats["total"] = len(rows)
    by_district: dict[str, list[dict[str, Any]]] = {}
    for row in rows:
        by_district.setdefault(str(row["district"] or "Không rõ"), []).append(row)

    for district, items in by_district.items():
        prices = [float(r["price_per_m2"]) for r in items if r["price_per_m2"]]
        totals = [float(r["price"]) for r in items if r["price"]]
        type_counts: dict[str, int] = {}
        for r in items:
            ptype = str(r["property_type"] or "khác")
            type_counts[ptype] = type_counts.get(ptype, 0) + 1
        stats["districts"][district] = {
            "province": items[0]["province_city"] if items else "",
            "count": len(items),
            "avg_ppm": sum(prices) / len(prices) if prices else None,
            "p25_ppm": _percentile(prices, 0.25),
            "median_ppm": _percentile(prices, 0.5),
            "p75_ppm": _percentile(prices, 0.75),
            "median_total": _percentile(totals, 0.5),
            "types": type_counts,
        }
    return stats


def _district_stats(district: str | None) -> dict[str, Any] | None:
    if not district:
        return None
    target = district.replace("Quận ", "").lower()
    for name, data in _market_stats().get("districts", {}).items():
        if target in name.lower() or name.lower() in district.lower():
            return {"name": name, **data}
    return None


def _advisor_recent_stats(district: str | None) -> dict[str, Any] | None:
    data = _district_stats(district)
    if not data:
        return data
    sample_cap = max(3, int((data.get("count") or 0) * 0.05))
    sample_cap = min(sample_cap, data.get("count") or sample_cap)
    try:
        with engine.connect() as conn:
            rows = conn.execute(
                sql_text(
                    """
                SELECT id, property_type, area_m2, price, price_per_m2, listing_date, source_collected_at
                FROM properties
                WHERE record_status != 'archived'
                  AND lower(district) = lower(:district)
                  AND price IS NOT NULL AND price > 0
                  AND area_m2 IS NOT NULL AND area_m2 > 0
                  AND price_per_m2 IS NOT NULL AND price_per_m2 > 0
                ORDER BY id DESC
                LIMIT :limit
                    """
                ),
                {"district": data["name"], "limit": sample_cap},
            ).mappings().all()
    except Exception:
        return data
    prices = [float(r["price_per_m2"]) for r in rows if r["price_per_m2"]]
    totals = [float(r["price"]) for r in rows if r["price"]]
    if not prices:
        return data
    return {
        **data,
        "advisor_count": len(rows),
        "advisor_ppm": _percentile(prices, 0.5),
        "advisor_p25_ppm": _percentile(prices, 0.25),
        "advisor_p75_ppm": _percentile(prices, 0.75),
        "advisor_median_total": _percentile(totals, 0.5),
    }


def _market_comparison_response(context: dict | None = None) -> str:
    stats = _market_stats()
    districts = sorted(
        stats.get("districts", {}).items(),
        key=lambda item: (item[1].get("median_ppm") or 0),
        reverse=True,
    )
    if not districts:
        return "Nova chưa đọc được dữ liệu thị trường từ PostgreSQL. Hãy kiểm tra DATABASE_URL và Alembic migration."

    advisor = []
    for name, _ in districts:
        recent = _advisor_recent_stats(name)
        if recent and recent.get("advisor_ppm"):
            advisor.append((name, recent))
    ranked = sorted(advisor, key=lambda item: item[1].get("advisor_ppm") or 0, reverse=True) or districts
    leader = ranked[0][0]
    affordable = sorted(ranked, key=lambda item: item[1].get("advisor_ppm") or item[1].get("median_ppm") or 0)[:2]
    affordable_text = ", ".join(name for name, _ in affordable)
    return (
        "Mình nhìn thị trường theo kiểu tư vấn nhanh, không đọc báo cáo khô nhé. 😊\n\n"
        f"📌 Khu đang căng giá hơn: {leader}.\n"
        f"💰 Nếu ưu tiên ngân sách dễ thở hơn, nên soi kỹ {affordable_text}.\n"
        "🏠 Nếu mua để ở, mình sẽ ưu tiên pháp lý sạch, hẻm/đường dễ đi và thanh khoản ổn hơn là chỉ nhìn giá rẻ.\n\n"
        "Bạn đưa ngân sách + mục tiêu ở hay đầu tư, mình sẽ thu hẹp còn vài hướng đáng xem nhất."
    )


def _trend_response(context: dict | None = None) -> str:
    stats = _market_stats()
    districts = sorted(
        stats.get("districts", {}).items(),
        key=lambda item: (item[1].get("median_ppm") or 0),
        reverse=True,
    )
    if not districts:
        return "Mình chưa đọc được dữ liệu để xem xu hướng."
    advisor = []
    for name, _ in districts:
        recent = _advisor_recent_stats(name)
        if recent and recent.get("advisor_ppm"):
            advisor.append((name, recent))
    ranked = sorted(advisor, key=lambda item: item[1].get("advisor_ppm") or 0, reverse=True) or districts
    expensive = ranked[:2]
    accessible = ranked[-2:]
    return (
        "Mình đọc xu hướng như một nhịp khảo giá nhanh, không biến nó thành bảng thống kê dài. 📈\n\n"
        f"🔥 Nhóm giữ giá mạnh: {', '.join(name for name, _ in expensive)}.\n"
        f"💰 Nhóm còn dễ vào tiền hơn: {', '.join(name for name, _ in accessible)}.\n"
        "👀 Điểm nên theo dõi: pháp lý sạch, hẻm đủ rộng, gần trục di chuyển và khu có nhu cầu thuê.\n\n"
        "Nếu bạn nói ngân sách và mục tiêu ở/đầu tư, mình sẽ khoanh 1-2 khu đáng xem thay vì chỉ nói xu hướng chung."
    )


def _district_price_response(district: str, from_image: bool = False, context: dict | None = None) -> str:
    data = _district_stats(district)
    if not data:
        return (
            f"Mình nhận diện khu vực là {district}, nhưng chưa thấy đủ mẫu trong PostgreSQL. "
            "Bạn gửi thêm diện tích, loại tài sản và pháp lý để mình chuyển sang hướng ước tính theo scope gần nhất."
        )
    recent = _advisor_recent_stats(data["name"]) or data
    median = recent.get("advisor_ppm") or data.get("median_ppm")
    p25 = recent.get("advisor_p25_ppm") or data.get("p25_ppm")
    p75 = recent.get("advisor_p75_ppm") or data.get("p75_ppm")
    intro = f"Mình xem nhanh {data['name']} theo góc tư vấn mua/bán nhé."
    if from_image:
        intro = f"Nhìn theo tên file/ảnh, mình tạm đặt bối cảnh ở {data['name']} rồi tư vấn như sau."
    return (
        f"{intro}\n\n"
        f"💰 Mặt bằng nhóm gần nhất: khoảng {_fmt_million(median)}.\n"
        f"📉 Nhóm dễ vào tiền hơn: quanh {_fmt_million(p25)}.\n"
        f"📈 Nhóm vị trí/đặc điểm tốt hơn: quanh {_fmt_million(p75)}.\n\n"
        "Nếu bạn đang mua thật, mình sẽ không chốt bằng một con số tròn. Gửi thêm diện tích, mặt tiền/hẻm, tình trạng nhà và pháp lý; mình sẽ phân tích theo hướng nên xem, cần ép giá hay nên bỏ qua."
    )


def _parse_budget_vnd(text: str) -> int | None:
    normalized = (
        text.lower()
        .replace(",", ".")
        .replace("tỉ", "tỷ")
        .replace("ty", "tỷ")
        .replace("ti", "tỷ")
    )
    match = re.search(r"(\d+(?:\.\d+)?)\s*tỷ(?:\s*(\d{1,3}))?", normalized)
    if not match:
        return None
    billions = float(match.group(1))
    tail = match.group(2)
    if tail and "." not in match.group(1):
        # "2 tỷ 2" is common shorthand for 2.2 billion, "2 tỷ 250" for 2.25 billion.
        if len(tail) == 1:
            billions += int(tail) / 10
        else:
            billions += int(tail) / 1000
    return int(billions * 1_000_000_000)


def _property_type_vi(value: str | None) -> str:
    mapping = {
        "house": "nhà phố",
        "townhouse": "nhà phố",
        "apartment": "căn hộ",
        "land": "đất",
        "villa": "biệt thự",
    }
    key = (value or "").strip().lower()
    return mapping.get(key, value or "BĐS")


def _legal_vi(value: str | None) -> str:
    mapping = {
        "ownership_certificate": "sổ/hồ sơ sở hữu",
        "full_ownership": "sở hữu đầy đủ",
        "land_use_right": "quyền sử dụng đất",
        "pending": "đang hoàn thiện",
    }
    key = (value or "").strip().lower()
    return mapping.get(key, value or "")


def _display_location(district: str, ward: str | None) -> str:
    if not ward or ward == district:
        return district
    q7_wards = {
        "phường tân thuận đông", "phường tân thuận tây", "phường tân kiểng",
        "phường tân hưng", "phường bình thuận", "phường tân quy",
        "phường phú thuận", "phường phú mỹ", "phường tân phú", "phường tân phong",
    }
    if district.lower() == "quận 7" and ward.lower() not in q7_wards:
        return district
    return ward


def _first_image_url(item: dict[str, Any]) -> str | None:
    direct = str(item.get("image_url") or "").strip()
    if direct:
        return direct
    raw = item.get("image_urls")
    if not raw:
        return None
    if isinstance(raw, list):
        return next((str(url).strip() for url in raw if str(url).strip()), None)
    text = str(raw).strip()
    if not text:
        return None
    try:
        parsed = json.loads(text)
        if isinstance(parsed, list):
            return next((str(url).strip() for url in parsed if str(url).strip()), None)
        if isinstance(parsed, str) and parsed.strip():
            return parsed.strip()
    except Exception:
        pass
    if text.startswith("http"):
        return text
    return None


def _clean_location_piece(value: str | None) -> str:
    text = str(value or "").strip()
    if not text:
        return ""
    text = text.replace("Hồ Chí Minh (cũ)", "Hồ Chí Minh")
    text = re.sub(r"\s+", " ", text)
    lowered = text.lower()
    if lowered.startswith("hồ chí minh đường") or lowered.startswith("hồ chí minh phường") or lowered.startswith("hồ chí minh quận"):
        text = text[len("Hồ Chí Minh "):]
    text = re.sub(r"^Hồ Chí Minh\s+(?=Đường|Phường|Quận)", "", text, flags=re.IGNORECASE)
    text = re.sub(r"\s*,\s*", ", ", text)
    text = re.sub(r"(,\s*){2,}", ", ", text)
    return text.strip(" ,;-")


def _candidate_location(item: dict[str, Any], district: str) -> str:
    parts: list[str] = []
    street = _clean_location_piece(item.get("street_or_project"))
    ward = _clean_location_piece(_display_location(district, item.get("ward")))
    if street and street.lower() not in {"không rõ", "unknown", "none"}:
        if district.lower() in street.lower():
            return street
        parts.append(street)
    if ward and ward not in parts:
        parts.append(ward)
    return ", ".join(parts) or district


def _budget_candidate_rows(district: str, budget: int) -> list[dict[str, Any]]:
    target = district.lower()
    try:
        with engine.connect() as conn:
            rows = conn.execute(
                sql_text(
                    """
                SELECT id, property_type, district, ward, street_or_project,
                       area_m2, bedrooms, floor_count, frontage_m,
                       legal_status, price, price_per_m2,
                       image_url, image_urls
                FROM properties
                WHERE record_status != 'archived'
                  AND price IS NOT NULL AND price > 0 AND price <= :budget
                  AND area_m2 IS NOT NULL AND area_m2 > 0
                  AND lower(district) = :district
                ORDER BY
                  CASE
                    WHEN legal_status ILIKE '%sổ%' OR legal_status ILIKE '%ownership%' THEN 0
                    WHEN legal_status IS NOT NULL AND legal_status != '' THEN 1
                    ELSE 2
                  END,
                  price DESC,
                  area_m2 DESC
                LIMIT 5
                    """
                ),
                {"budget": budget, "district": target},
            ).mappings().all()
    except Exception:
        return []
    return [dict(row) for row in rows]


def _budget_response(text: str, district: str | None = None) -> str:
    budget = _parse_budget_vnd(text)
    target = district or "Quận 7"
    data = _district_stats(target)
    if not budget or not data or not data.get("median_ppm"):
        return (
            "Mình tư vấn được, nhưng cần thêm một chút để lọc đúng hàng.\n\n"
            "📍 Khu vực bạn muốn mua là quận/phường nào?\n"
            "🏠 Bạn ưu tiên căn hộ, nhà phố hay đất?\n"
            "💰 Ngân sách tối đa khoảng bao nhiêu?\n\n"
            "Bạn có thể nhắn kiểu: 2 tỷ, Quận 7, ưu tiên căn hộ dễ bán lại."
        )
    median_ppm = float(data["median_ppm"])
    area_at_median = budget / median_ppm
    area_at_p25 = budget / max(float(data.get("p25_ppm") or median_ppm), 1)
    budget_text = _fmt_billion(budget)
    candidates = _budget_candidate_rows(data["name"], budget)
    if candidates:
        rows = []
        for idx, item in enumerate(candidates, 1):
            location = _candidate_location(item, data["name"])
            legal = _legal_vi(item.get("legal_status"))
            fit_note = "đáng xem trước" if idx == 1 else "có thể cân nhắc"
            image_url = _first_image_url(item)
            specs = []
            if item.get("bedrooms"):
                specs.append(f"{int(item.get('bedrooms'))} PN")
            if item.get("floor_count"):
                specs.append(f"{float(item.get('floor_count')):g} tầng")
            if item.get("frontage_m"):
                specs.append(f"mặt tiền {float(item.get('frontage_m')):g}m")
            rows.append(
                f"{idx}. {_property_type_vi(item.get('property_type')).capitalize()}\n"
                f"   Vị trí/khu vực: {location}\n"
                f"   Giá: {_fmt_billion(item.get('price'))} • Diện tích: {float(item.get('area_m2') or 0):.1f}m² • {_fmt_million(item.get('price_per_m2'))}\n"
                f"   Nhận xét: {fit_note}"
                + (f" • Pháp lý: {legal}" if legal else "")
                + (f" • {' • '.join(specs)}" if specs else "")
                + (f"\n   Ảnh mẫu: {image_url}" if image_url else "\n   Ảnh mẫu: bản ghi này chưa có ảnh công khai")
            )
        return (
            f"Được, với khoảng {budget_text} ở {data['name']}, mình sẽ tư vấn thực tế một chút: đừng nhắm nhà phố rộng, hãy ưu tiên căn nhỏ, căn hộ hoặc nhà hẻm sâu có pháp lý rõ. 👍\n\n"
            "🏡 Gợi ý đáng xem\n"
            + "\n\n".join(rows)
            + "\n\n📌 Mặt bằng khu vực\n"
            f"- Trung vị đang khoảng {_fmt_million(median_ppm)}.\n"
            f"- Ngân sách này tương đương khoảng {area_at_median:.1f}m² nếu mua theo mặt bằng trung vị, hoặc {area_at_p25:.1f}m² nếu săn nhóm giá thấp.\n\n"
            "🎯 Chốt tư vấn: nếu muốn ở thật, mình nghiêng về căn hộ/nhà nhỏ pháp lý sạch; nếu muốn đầu tư, nên lọc tiếp theo khả năng cho thuê và thanh khoản."
        )
    return (
        f"Với khoảng {budget_text} tại {data['name']}, mình sẽ đặt kỳ vọng như sau:\n\n"
        f"📌 Trung vị khu vực: {_fmt_million(median_ppm)}.\n"
        f"📐 Diện tích hợp lý theo trung vị: khoảng {area_at_median:.1f}m².\n"
        f"🔎 Nếu săn nhóm giá thấp: có thể lên khoảng {area_at_p25:.1f}m².\n\n"
        "Tư vấn nhanh: nhà phố hoàn chỉnh sẽ khá căng; hướng sáng hơn là căn hộ nhỏ, nhà hẻm sâu hoặc tài sản diện tích nhỏ nhưng pháp lý rõ."
    )


def _buy_where_response() -> str:
    stats = _market_stats().get("districts", {})
    if not stats:
        return "Chưa đọc được DB để gợi ý khu vực mua."
    ranked_by_price = sorted(stats.items(), key=lambda item: item[1].get("median_ppm") or 0)
    affordable = ranked_by_price[:3]
    liquid = sorted(stats.items(), key=lambda item: item[1].get("count") or 0, reverse=True)[:3]
    affordable_text = ", ".join(f"{n} ({_fmt_million(d.get('median_ppm'))})" for n, d in affordable)
    liquid_text = ", ".join(f"{n} ({d.get('count')} mẫu)" for n, d in liquid)
    return (
        "Nếu hỏi mơ hồ 'nên mua ở đâu', Nova sẽ tách theo mục tiêu:\n"
        f"- Ưu tiên giá dễ tiếp cận: {affordable_text}.\n"
        f"- Ưu tiên tín hiệu dữ liệu/so sánh ổn định: {liquid_text}.\n"
        "- Ở thực tại TP.HCM: Quận 7 hợp hạ tầng/khu dân cư, Bình Thạnh hợp gần trung tâm, Tân Bình hợp di chuyển.\n"
        "- Đầu tư/cho thuê tại Hà Nội: Cầu Giấy mạnh về văn phòng và nhu cầu thuê, nhưng mặt bằng giá cao.\n"
        "Bạn đưa ngân sách và mục tiêu ở/đầu tư, mình sẽ lọc còn 1-2 lựa chọn."
    )


def _example_response(district: str | None = None) -> str:
    target = district or "Quận 7"
    data = _district_stats(target)
    ppm = data.get("median_ppm") if data else 120_000_000
    area = 50
    estimated = ppm * area
    return (
        "Mình lấy một tình huống dễ hình dung nhé:\n\n"
        f"🏠 Tài sản: nhà phố {target}, {area}m², hẻm 4m, 2 tầng, sổ hồng.\n"
        f"💰 Mốc tham chiếu: khoảng {_fmt_million(ppm)}.\n"
        f"📊 Giá sơ bộ: khoảng {_fmt_billion(estimated)} trước khi điều chỉnh.\n\n"
        "Nếu hẻm nhỏ, nhà xuống cấp hoặc pháp lý chưa sạch thì nên trừ giá. Nếu nhà mới, vị trí thoáng hoặc góc hai mặt tiền thì có thể cộng thêm."
    )


def _greeting_response() -> str:
    return (
        "Chào bạn, mình là Nova. Bạn cứ hỏi tự nhiên: tính toán, giải thích, viết nội dung, hoặc hỏi về bất động sản đều được. "
        "Nếu bạn hỏi về nhà đất, mình sẽ tự kéo dữ liệu dự án để phân tích sát hơn."
    )


def _identity_response() -> str:
    return (
        "Mình là Nova, trợ lý tư vấn trong ứng dụng này. 😊\n\n"
        "Bạn có thể hỏi mình như một AI bình thường: giải toán, đọc ảnh, tóm tắt tài liệu, viết nội dung hoặc phân tích dữ liệu.\n\n"
        "Riêng khi nói về nhà đất, mình sẽ chuyển sang vai trò tư vấn viên: xem ngân sách, khu vực, pháp lý, thanh khoản và dữ liệu giá để đưa ra hướng chọn thực tế hơn."
    )


def _project_overview_response(context: dict | None = None) -> str:
    snapshot = (context or {}).get("project_snapshot", {}) if isinstance(context, dict) else {}
    stats = _market_stats()
    count = snapshot.get("property_count") or stats.get("total") or "nhiều"
    scope = snapshot.get("scope") or sorted(stats.get("districts", {}).keys())
    scope_text = ", ".join(scope[:6]) if scope else "các quận trọng điểm ở Hà Nội và TP.HCM"
    latest_model = snapshot.get("latest_model") or "model active được pin trong model registry"
    return (
        "Dự án này là một hệ thống AVM production cho định giá bất động sản, không chỉ là form dự đoán đơn lẻ.\n\n"
        f"Nó dùng FastAPI, React/Vite, PostgreSQL/PostGIS và ML pipeline để xử lý khoảng {count} bản ghi trong scope {scope_text}. "
        f"Luồng chính là: người dùng nhập tài sản -> backend chuẩn hóa input -> engine so comparable, adjustment ledger, SDEV/market signal và confidence -> lưu lại `valuation_runs` để audit, feedback giá thật và retraining. "
        f"Model đang tham chiếu qua registry là {latest_model}.\n\n"
        "Nói ngắn gọn: bản chất dự án là một nền tảng định giá có lineage, account history, model registry và dữ liệu phản hồi quay lại training, chứ không phải demo UI tĩnh."
    )


def _natural_general_response(message: str, attachment_note: str = "") -> str:
    text = _compact_text(message)
    if any(k in text for k in ["cảm ơn", "cam on", "thanks", "thank you"]):
        return "Không có gì. Bạn cứ đưa tiếp dữ liệu hoặc câu hỏi, mình sẽ bám sát ngữ cảnh đang mở." + attachment_note
    if any(k in text for k in ["giúp gì", "giup gi", "làm được gì", "lam duoc gi", "help"]):
        return (
            "Mình giúp tốt nhất ở ba việc: giải thích kết quả định giá, soi dữ liệu/model của dự án, và hướng dẫn thao tác trong app. "
            "Bạn cũng có thể hỏi tự nhiên hơn, ví dụ: 'vì sao kết quả này thấp?', 'khu nào hợp 2 tỷ?', hoặc 'kiểm tra model active cho tôi'."
            + attachment_note
        )
    if len(text.split()) <= 4:
        return (
            "Mình đang nghe đây. Bạn nói thêm một chút mục tiêu nhé: muốn phân tích bất động sản, kiểm tra hệ thống, hay nhờ mình giải thích một phần cụ thể?"
            + attachment_note
        )
    return (
        "Mình hiểu hướng bạn đang hỏi, nhưng để trả lời sắc hơn mình cần thêm mục tiêu hoặc dữ liệu kèm theo. "
        "Nếu liên quan AVM, mình có thể bám ngay vào PostgreSQL, model registry, lịch sử dự đoán và kết quả định giá hiện tại."
        + attachment_note
    )


def _legal_response(district: str | None = None) -> str:
    target = _district_stats(district) if district else None
    area_note = f"\n\n📍 Nếu căn nằm ở {target['name']}, mình sẽ ưu tiên so với nhóm tài sản cùng khu vực." if target else ""
    return (
        "Pháp lý là phần mình sẽ soi rất kỹ trước khi khuyên mua. 🧾\n\n"
        "✅ Nên hỏi ngay:\n"
        "- Có sổ riêng hay sổ chung?\n"
        "- Có dính quy hoạch/lộ giới/tranh chấp không?\n"
        "- Sang tên được ngay hay đang chờ hoàn công, thừa kế, tách thửa?\n\n"
        "🎯 Cách tư vấn của mình: pháp lý sạch thì giữ giá tốt hơn; pháp lý lấn cấn thì phải chiết khấu, dù nhà nhìn có vẻ rẻ."
        f"{area_note}"
    )


def _advisor_sensitive_response() -> str:
    return (
        "Mình hiểu bạn muốn xem sâu để kiểm chứng, nhưng phần dữ liệu nội bộ/raw record/cấu hình dự án không phù hợp để xuất trực tiếp ở chế độ người dùng. "
        "Mình sẽ không đổ danh sách record, source URL, schema chi tiết hay thông tin nhạy cảm ra chat.\n\n"
        "Mình vẫn có thể giúp theo hướng an toàn hơn:\n"
        "• Tóm tắt xu hướng thị trường ở mức tư vấn\n"
        "• Lọc vài lựa chọn phù hợp theo ngân sách bằng nhóm mẫu gần nhất tối đa 5%\n"
        "• Giải thích vì sao nên/không nên mua một khu vực\n"
        "• Nêu các rủi ro pháp lý cần hỏi lại bên bán"
    )


def _admin_internal_data_response() -> str:
    stats = _market_stats()
    districts = sorted(
        stats.get("districts", {}).items(),
        key=lambda item: item[1].get("count") or 0,
        reverse=True,
    )
    lines = [
        "Chế độ cộng tác viên nội bộ: mình có thể in thống kê dự án ở mức tổng hợp, nhưng vẫn không tiết lộ API key/token/secret. 🛠️",
        "",
        f"Tổng mẫu hợp lệ đang đọc được: {stats.get('total', 0)}.",
    ]
    for name, data in districts[:10]:
        lines.append(
            f"- {name}: {data.get('count')} mẫu, median {_fmt_million(data.get('median_ppm'))}, "
            f"IQR {_fmt_million(data.get('p25_ppm'))} - {_fmt_million(data.get('p75_ppm'))}."
        )
    return "\n".join(lines)


def _simple_arithmetic_response(message: str) -> str | None:
    text = message.strip().lower()
    if not re.search(r"\d\s*[\+\-\*\/x×]\s*\d", text):
        return None
    expr_match = re.search(r"([0-9\.\s\+\-\*\/x×\(\)]+)", text)
    if not expr_match:
        return None
    expr = expr_match.group(1).replace("x", "*").replace("×", "*")
    expr = re.sub(r"\s+", "", expr)
    if not expr or len(expr) > 80 or not re.fullmatch(r"[0-9\.\+\-\*\/\(\)]+", expr):
        return None
    try:
        value = eval(expr, {"__builtins__": {}}, {})
    except Exception:
        return None
    if isinstance(value, float) and value.is_integer():
        value = int(value)
    return f"{expr.replace('*', '×')} = {value}"


_PAGE_HINTS = {
    "/": "Trang Định giá — người dùng đang nhập biểu mẫu hoặc xem kết quả định giá.",
    "/prediction": "Trang Định giá — biểu mẫu + kết quả AVM v2.",
    "/research-lab": "Research Lab — admin chạy test/train/MLOps thật (experiment, drift, registry, health-check).",
    "/dashboard": "Dashboard tổng quan dữ liệu + biểu đồ chất lượng.",
    "/collection": "Collection Dashboard — quản lý thu thập dữ liệu.",
    "/provenance-tracker": "Provenance — truy vết nguồn gốc bản ghi.",
    "/data-sources": "Nguồn dữ liệu đã duyệt.",
    "/self-collected": "Dữ liệu tự thu thập.",
}


def _models_index() -> list[dict]:
    """Đọc mọi metadata_*.json -> list version + metrics thật (không bịa)."""
    models_dir = PROJECT_ROOT / "models"
    rows: list[dict] = []
    if not models_dir.exists():
        return rows
    for meta_path in sorted(models_dir.glob("metadata_*.json")):
        try:
            meta = json.loads(meta_path.read_text(encoding="utf-8"))
        except Exception:
            continue
        stamp = meta_path.stem.replace("metadata_", "")
        best = meta.get("best_model", "?")
        res = meta.get("all_results", {}).get(best, {})
        rows.append({
            "stamp": stamp,
            "best_model": best,
            "test_r2": res.get("test_r2", res.get("r2")),
            "test_mae": res.get("test_mae", res.get("mae")),
            "test_mape": res.get("test_mape"),
            "trained_at": meta.get("trained_at"),
            "n_features": meta.get("n_features"),
            "train_size": meta.get("train_size"),
            "has_pkl": (models_dir / f"model_{stamp}.pkl").exists(),
        })
    rows.sort(key=lambda r: r["stamp"], reverse=True)
    return rows


def _active_model_stamp() -> str | None:
    pointer = PROJECT_ROOT / "models" / "ACTIVE_MODEL.json"
    if pointer.exists():
        try:
            return json.loads(pointer.read_text(encoding="utf-8")).get("stamp")
        except Exception:
            return None
    return None


def _quick_drift_summary() -> str | None:
    """PSI nhanh trên price_per_m2 + price (nửa cũ vs nửa mới theo id)."""
    try:
        import numpy as np
        with engine.connect() as conn:
            rows = conn.execute(
                sql_text(
                    """
                SELECT id, price, area_m2, price_per_m2 FROM properties
                WHERE record_status != 'archived' AND price > 0 AND area_m2 > 0
                  AND price_per_m2 > 0 ORDER BY id
                    """
                )
            ).mappings().all()
    except Exception:
        return None
    if len(rows) < 60:
        return None
    half = len(rows) // 2
    ref, cur = rows[:half], rows[half:]

    def psi(expected, actual, bins=10):
        import numpy as np
        e = np.asarray(expected, float); a = np.asarray(actual, float)
        edges = np.unique(np.percentile(e, np.linspace(0, 100, bins + 1)))
        if len(edges) < 3:
            return 0.0
        eh, _ = np.histogram(e, edges); ah, _ = np.histogram(a, edges)
        ep = np.clip(eh / max(eh.sum(), 1), 1e-4, None)
        ap = np.clip(ah / max(ah.sum(), 1), 1e-4, None)
        return float(np.sum((ap - ep) * np.log(ap / ep)))

    ppm = psi([r["price_per_m2"] for r in ref], [r["price_per_m2"] for r in cur])
    pr = psi([r["price"] for r in ref], [r["price"] for r in cur])
    worst = max(ppm, pr)
    verdict = "ổn định, chưa cần retrain" if worst < 0.1 else (
        "drift nhẹ, nên theo dõi" if worst < 0.25 else "DRIFT MẠNH — nên retrain")
    return (f"PSI giá/m² = {ppm:.3f}, PSI tổng giá = {pr:.3f} "
            f"(so {len(ref)} bản ghi cũ vs {len(cur)} mới). Kết luận: {verdict}.")


def _system_intel_response(text: str, context: dict | None) -> str | None:
    """Grounding cho câu hỏi về model / MLOps / drift / dataset — số liệu thật."""
    admin = _is_admin_context(context)
    page_ctx = (context or {}).get("page_context") or {}
    cur_val = page_ctx.get("current_valuation") if isinstance(page_ctx, dict) else None

    # --- Giải thích kết quả định giá đang hiển thị trên màn hình ---
    if cur_val and isinstance(cur_val, dict) and any(k in text for k in [
        "giải thích", "giai thich", "kết quả này", "ket qua nay", "con số này", "con so nay",
        "tại sao", "tai sao", "vì sao", "vi sao", "kết quả trên", "ket qua tren", "định giá này", "dinh gia nay",
    ]):
        parts = ["🔎 Giải thích kết quả định giá đang hiển thị:"]
        if cur_val.get("fair_value_text") or cur_val.get("fair_value"):
            parts.append(f"• Giá hợp lý: {cur_val.get('fair_value_text') or _fmt_billion(cur_val.get('fair_value'))}.")
        if cur_val.get("property_type") or cur_val.get("district") or cur_val.get("area"):
            parts.append(f"• Tài sản: {cur_val.get('property_type','?')} · {cur_val.get('district','?')} · {cur_val.get('area','?')} m².")
        if cur_val.get("confidence_grade") or cur_val.get("confidence"):
            parts.append(f"• Độ tin cậy: {cur_val.get('confidence_grade','?')} ({cur_val.get('confidence','?')}).")
        if cur_val.get("top_factors"):
            tf = cur_val["top_factors"]
            if isinstance(tf, list) and tf:
                parts.append("• Yếu tố ảnh hưởng mạnh nhất: " + ", ".join(str(x) for x in tf[:4]) + ".")
        parts.append("Muốn mình đi sâu yếu tố nào (pháp lý, vị trí, diện tích, comparable) thì nói nhé.")
        return "\n".join(parts)

    # --- Data drift ---
    if any(k in text for k in ["drift", "trôi dữ liệu", "troi du lieu", "psi", "lệch phân phối", "lech phan phoi"]):
        summary = _quick_drift_summary()
        if not summary:
            return "Mình chưa đủ dữ liệu để đo drift (cần ≥60 bản ghi hợp lệ trong DB)."
        extra = " Bạn có thể chạy chi tiết trong Research Lab → MLOps → Data drift (PSI)." if admin else ""
        return f"📉 Data drift hiện tại: {summary}{extra}"

    # --- Experiments / leaderboard / accuracy ---
    if any(k in text for k in ["experiment", "leaderboard", "độ chính xác", "do chinh xac",
                                "r2", "r²", "mae", "model nào tốt", "model nao tot",
                                "lịch sử train", "lich su train", "bao nhiêu model", "bao nhieu model"]):
        rows = _models_index()
        if not rows:
            return "Chưa có metadata model nào trong thư mục models/."
        scored = [r for r in rows if isinstance(r.get("test_r2"), (int, float))]
        with_mape = [r for r in rows if isinstance(r.get("test_mape"), (int, float))]
        best = min(with_mape, key=lambda r: r["test_mape"]) if with_mape else (
            max(scored, key=lambda r: r["test_r2"]) if scored else rows[0]
        )
        latest = rows[0]
        active = _active_model_stamp()
        lines = [f"🧪 Có {len(rows)} lần train trong registry."]
        if best.get("test_mape") is not None:
            best_r2 = best["test_r2"] if isinstance(best.get("test_r2"), (int, float)) else 0
            lines.append(f"🏆 Tốt nhất theo official test MAPE: {best['stamp']} ({best['best_model']}) "
                         f"MAPE={best['test_mape']:.2f}%, R²={best_r2:.3f}, "
                         f"MAE={_fmt_billion(best['test_mae'])}.")
        elif best.get("test_r2") is not None:
            lines.append(f"🏆 Tốt nhất theo test R²: {best['stamp']} ({best['best_model']}) "
                         f"R²={best['test_r2']:.3f}, MAE={_fmt_billion(best['test_mae'])}.")
        if latest and latest["stamp"] != best["stamp"]:
            latest_mape = f"{latest['test_mape']:.2f}%" if isinstance(latest.get("test_mape"), (int, float)) else "—"
            gap = (
                latest["test_mape"] - best["test_mape"]
                if isinstance(latest.get("test_mape"), (int, float)) and isinstance(best.get("test_mape"), (int, float))
                else None
            )
            gap_text = f" — lệch +{gap:.2f} điểm %" if gap is not None else ""
            lines.append(f"⚠️ Mới nhất là {latest['stamp']} với MAPE={latest_mape}{gap_text}; đây không phải bản tốt nhất.")
        lines.append(f"📦 Version đang phục vụ: {active or 'chưa pin ACTIVE_MODEL.json; serving phải fail closed'}.")
        if admin:
            lines.append("Mở Research Lab → MLOps để xem leaderboard đầy đủ hoặc rollback version.")
        return "\n".join(lines)

    # --- Model status / health ---
    if any(k in text for k in ["model", "mô hình", "mo hinh"]) and any(
        k in text for k in ["trạng thái", "trang thai", "health", "sức khỏe", "suc khoe",
                              "đang dùng", "dang dung", "version", "phiên bản", "phien ban", "active"]):
        rows = _models_index()
        if not rows:
            return "Chưa có model nào được train."
        active = _active_model_stamp()
        serving = active or rows[0]["stamp"]
        cur = next((r for r in rows if r["stamp"] == serving), rows[0])
        r2 = f"{cur['test_r2']:.3f}" if isinstance(cur.get("test_r2"), (int, float)) else "—"
        mape = f"{cur['test_mape']:.2f}%" if isinstance(cur.get("test_mape"), (int, float)) else "—"
        return (f"🤖 Model đang phục vụ: {serving} — {cur['best_model']}\n"
                f"• official test MAPE={mape}, R²={r2}, MAE={_fmt_billion(cur.get('test_mae'))}\n"
                f"• {cur.get('n_features')} features, train trên {cur.get('train_size')} bản ghi\n"
                f"• Pin active: {'có' if active else 'không (auto latest)'}.")

    # --- Dataset / DB overview ---
    if any(k in text for k in ["bao nhiêu bản ghi", "bao nhieu ban ghi", "tổng dữ liệu", "tong du lieu",
                                "dataset", "dữ liệu hiện có", "du lieu hien co", "quy mô dữ liệu", "quy mo du lieu"]):
        snap = get_project_snapshot()
        n = snap.get("property_count")
        scope = ", ".join(snap.get("scope", []))
        if n is None:
            return "Mình chưa đọc được DB. Kiểm tra DATABASE_URL và trạng thái PostgreSQL."
        return (f"📊 Dataset hiện có {n:,} bản ghi trong 6 quận scope ({scope}). "
                f"Model mới nhất: {snap.get('latest_model') or 'chưa có'}.").replace(",", ".")
    return None


def project_fast_response(
    message: str,
    context: dict,
    attachments: list[NovaAttachment] | None = None,
) -> str | None:
    attachments = attachments or []
    text = _compact_text(message, attachments)
    history_text = _compact_text(_recent_user_text(context))
    thread_text = f"{history_text} {text}".strip()
    has_attachment = bool(attachments)
    district = _infer_district(message, attachments) or _infer_district(history_text)

    if _asks_secret(text):
        return (
            "Phần key/token/secret thì mình không thể in ra chat, kể cả ở chế độ quản lý. "
            "Mình có thể kiểm tra trạng thái đã cấu hình hay chưa, nhưng không hiển thị giá trị thật."
        )

    if _asks_internal_data(text):
        if _is_admin_context(context):
            return _admin_internal_data_response()
        return _advisor_sensitive_response()

    # System / MLOps grounding — model, drift, experiments, dataset (số liệu thật)
    system_intel = _system_intel_response(text, context)
    if system_intel:
        return system_intel

    asks_project_overview = any(k in text for k in ["dự án", "du an", "project", "avm", "real estate"]) and any(
        k in text
        for k in [
            "là gì",
            "la gi",
            "đang làm gì",
            "dang lam gi",
            "bản chất",
            "ban chat",
            "mục tiêu",
            "muc tieu",
            "giải thích",
            "giai thich",
        ]
    )
    if asks_project_overview:
        return _project_overview_response(context)

    arithmetic = _simple_arithmetic_response(message)
    if arithmetic and not any(k in text for k in ["giá", "định giá", "nhà", "đất", "bđs", "quận"]):
        return arithmetic

    if text in {"hi", "hello", "chào", "xin chào", "chao", "xin chao"}:
        return _greeting_response()

    if any(k in text for k in ["bạn là ai", "ban la ai", "who are you", "nova là ai", "nova la ai", "tự giới thiệu", "tu gioi thieu", "giới thiệu bản thân", "gioi thieu ban than"]):
        return _identity_response()

    if any(k in text for k in ["pháp lý", "phap ly", "sổ đỏ", "so do", "sổ hồng", "so hong", "quy hoạch", "quy hoach", "tranh chấp", "tranh chap"]):
        return _legal_response(district)

    if _parse_budget_vnd(message) or any(k in text for k in ["ngân sách", "ngan sach", "mua được", "mua duoc", "khả năng mua", "kha nang mua"]):
        return _budget_response(message, district)

    if any(k in text for k in ["vị trí", "vi tri", "hình ảnh", "hinh anh", "ảnh mẫu", "anh mau", "ảnh đâu", "anh dau"]):
        if any(k in thread_text for k in ["tỷ", "ngân sách", "ngan sach", "mua được", "mua duoc", "khả năng mua", "kha nang mua"]):
            return _budget_response(thread_text, district)

    if any(k in text for k in ["ví dụ", "vi du"]) or text in {"mẫu", "mau", "cho tôi mẫu", "cho toi mau"}:
        return _example_response(district)

    if any(k in text for k in ["nên mua", "nen mua", "mua ở đâu", "mua o dau", "đầu tư đâu", "dau tu dau"]):
        return _buy_where_response()

    if any(k in text for k in ["xu hướng", "xu huong"]):
        return _trend_response(context)

    if any(k in text for k in ["so sánh thị trường", "so sanh thi truong", "thị trường", "thi truong"]):
        return _market_comparison_response(context)

    image_terms = ["ảnh", "hình", "image", "photo", "file"]
    price_terms = ["giá", "định giá", "tìm", "tra", "nhà", "đất"]
    image_task_terms = ["giải", "giai", "bài toán", "bai toan", "đọc", "doc", "phân tích", "phan tich", "tóm tắt", "tom tat", "nội dung", "noi dung"]
    if has_attachment and any(k in text for k in image_task_terms) and not district:
        return None
    if has_attachment and any(k in text for k in image_terms + price_terms):
        if district:
            return _district_price_response(district, from_image=True, context=context)
        return _attachment_general_response(attachments)

    return None


def propose_nova_action(message: str, context: dict | None) -> dict | None:
    """Đề xuất action có nút xác nhận cho người dùng (agentic).

    - execute: chỉ đề xuất cho admin (endpoint /execute gate server-side bằng JWT admin).
    - navigate: đề xuất cho mọi người.
    """
    text = _compact_text(message)
    admin = _is_admin_context(context)
    has_verb = any(v in text for v in [
        "chạy", "chay", "thực thi", "thuc thi", "run", "kiểm tra", "kiem tra",
        "đo", "do ", "xem", "mở", "mo ", "làm mới", "lam moi", "nạp lại", "nap lai",
        "reload", "refresh", "ngay", "giúp", "giup", "hãy", "hay ",
    ])

    if admin and has_verb:
        if any(k in text for k in ["drift", "psi", "trôi dữ liệu", "troi du lieu", "lệch phân phối"]):
            return {"type": "execute", "op": "mlops_drift",
                    "label": "Chạy đo data drift (PSI) ngay", "requires_confirmation": True}
        if any(k in text for k in ["sức khỏe", "suc khoe", "health", "còn chạy", "con chay", "sống không", "song khong"]) \
                and any(k in text for k in ["model", "mô hình", "mo hinh"]):
            return {"type": "execute", "op": "mlops_monitor",
                    "label": "Health-check model đang phục vụ", "requires_confirmation": True}
        if any(k in text for k in ["leaderboard", "registry", "danh sách model", "danh sach model", "các model", "cac model", "lịch sử train", "lich su train"]):
            return {"type": "execute", "op": "mlops_experiments",
                    "label": "Xem leaderboard / registry model", "requires_confirmation": True}
        if any(k in text for k in ["reload", "nạp lại", "nap lai", "làm mới cache", "lam moi cache", "refresh model", "cache model"]):
            return {"type": "execute", "op": "model_reload",
                    "label": "Reload cache model backend", "requires_confirmation": True}

    # Navigation cho mọi người
    if any(k in text for k in ["research lab", "phòng lab", "phong lab", "mlops"]) and any(k in text for k in ["mở", "mo ", "vào", "vao", "tới", "toi", "đến", "den"]):
        return {"type": "navigate", "to": "/research-lab", "label": "Mở Research Lab"}
    if any(k in text for k in ["dashboard", "tổng quan", "tong quan"]) and any(k in text for k in ["mở", "mo ", "vào", "vao"]):
        return {"type": "navigate", "to": "/dashboard", "label": "Mở Dashboard"}
    if any(k in text for k in ["định giá", "dinh gia", "dự đoán", "du doan"]) and any(k in text for k in ["mở", "mo ", "vào", "vao", "trang"]):
        return {"type": "navigate", "to": "/", "label": "Mở trang Định giá"}
    return None


def _attachment_general_response(attachments: list[NovaAttachment]) -> str:
    names = ", ".join((item.relativePath or item.name) for item in attachments[:5])
    image_count = sum(1 for item in attachments if (item.mime or "").startswith("image/") or parse_data_url(item.dataUrl))
    folder_count = sum(1 for item in attachments if item.kind == "folder")
    file_count = len(attachments)
    parts = [f"Mình đã nhận {file_count} mục gửi kèm"]
    if image_count:
        parts.append(f"{image_count} ảnh")
    if folder_count:
        parts.append(f"{folder_count} thư mục")
    summary = ", ".join(parts)
    return (
        f"{summary}: {names}. "
        "Bạn có thể hỏi thẳng mình muốn làm gì với ảnh/tệp này: tóm tắt nội dung, đọc thông tin nhà đất, ước tính giá, "
        "so sánh khu vực hoặc kiểm tra rủi ro pháp lý. Nếu ảnh không có khu vực/diện tích trong metadata, mình sẽ hỏi thêm thay vì tự đoán."
    )


def _attachment_task_fallback(message: str, attachments: list[NovaAttachment]) -> str:
    names = ", ".join((item.relativePath or item.name) for item in attachments[:3])
    text = message.lower()
    if any(k in text for k in ["giải", "giai", "bài toán", "bai toan"]):
        return (
            f"Mình đã nhận ảnh {names}, nhưng lần đọc ảnh này chưa trích được nội dung bài toán đủ rõ để giải chắc tay.\n\n"
            "📌 Bạn làm nhanh một trong hai cách nhé:\n"
            "- Dán lại ảnh rõ hơn, chụp sát phần đề và tránh bị mờ.\n"
            "- Hoặc gõ/copy phần đề vào chat, mình sẽ giải từng bước ngay.\n\n"
            "Mình giữ ảnh trong hội thoại, nên bạn có thể gửi tiếp: 'giải dòng 1' hoặc 'đề là...' là mình xử lý tiếp."
        )
    if any(k in text for k in ["phân tích", "phan tich", "đọc", "doc", "tóm tắt", "tom tat"]):
        return (
            f"Mình đã nhận ảnh {names}. Nội dung ảnh chưa được trích xuất đủ rõ trong lần đọc này, nên mình sẽ không đoán bừa.\n\n"
            "Bạn gửi thêm một dòng yêu cầu cụ thể hoặc ảnh rõ hơn nhé: cần đọc chữ, tóm tắt nội dung, hay phân tích nhà đất trong ảnh?"
        )
    return _attachment_general_response(attachments)


def fallback_response(
    message: str,
    context: dict,
    attachments: list[NovaAttachment] | None = None,
    provider_failed: bool = False,
) -> str:
    msg_lower = message.lower()
    snapshot = context.get("project_snapshot", {})
    history = context.get("recent_messages") or []
    history_text = " ".join(
        str(m.get("text", ""))
        for m in history
        if isinstance(m, dict) and m.get("role") == "user"
    ).lower()
    short_followup = len(msg_lower.split()) <= 3 and any(
        kw in msg_lower for kw in ["tìm", "tra", "tiếp", "nữa", "đi", "ví dụ", "mẫu"]
    )
    intent_text = f"{history_text} {msg_lower}".strip() if short_followup else msg_lower
    count = snapshot.get("property_count")
    latest_model = snapshot.get("latest_model") or "model trong thư mục models"
    districts = ", ".join(snapshot.get("scope", []))
    top = snapshot.get("top_districts") or []
    attachments = attachments or []
    attachment_note = ""
    if attachments:
        samples = ", ".join((a.relativePath or a.name) for a in attachments[:5])
        attachment_note = f" Tôi đã nhận {len(attachments)} tệp/thành phần gửi kèm ({samples})."

    if attachments and any(kw in msg_lower for kw in ["ảnh", "hình", "file", "tệp", "thư mục", "folder", "gửi", "giải", "bài toán", "phân tích", "đọc"]):
        return _attachment_task_fallback(message, attachments)

    project_terms = [
        "bất động sản", "bđs", "định giá", "valuation", "giá", "nhà", "đất", "dự án",
        "database", "dataset", "model", "thuật toán", "pipeline", "cầu giấy", "thanh xuân",
        "đống đa", "quận 7", "bình thạnh", "tân bình", "hà nội", "hcm", "api", "env",
        "frontend", "backend", "nova", "shap", "comparable", "sdev", "pháp lý",
        "sổ đỏ", "sổ hồng", "quy hoạch", "giấy tờ", "ví dụ", "mẫu", "tỷ", "ngân sách",
    ]
    is_project_question = any(term in intent_text for term in project_terms) or msg_lower.strip() in {"tìm", "tìm đi", "tra", "tra đi"}
    project_prefix = ""

    district_aliases = {
        "quận 7": ["quận 7", "quan 7", "q7", "q.7", "cấp 7", "cap 7"],
        "quận cầu giấy": ["cầu giấy", "cau giay"],
        "quận thanh xuân": ["thanh xuân", "thanh xuan"],
        "quận đống đa": ["đống đa", "dong da"],
        "quận bình thạnh": ["bình thạnh", "binh thanh"],
        "quận tân bình": ["tân bình", "tan binh"],
    }
    target_district = None
    for canonical, aliases in district_aliases.items():
        if any(alias in intent_text for alias in aliases):
            target_district = canonical
            break
    district_row = None
    if target_district:
        for item in top:
            if target_district.replace("quận ", "") in str(item.get("district", "")).lower():
                district_row = item
                break

    asks_project_overview = any(k in msg_lower for k in ["dự án", "du an", "project", "avm", "real estate"]) and any(
        k in msg_lower
        for k in [
            "là gì",
            "la gi",
            "đang làm gì",
            "dang lam gi",
            "bản chất",
            "ban chat",
            "mục tiêu",
            "muc tieu",
            "giải thích",
            "giai thich",
        ]
    )
    if asks_project_overview:
        return _project_overview_response(context) + attachment_note

    if any(kw in msg_lower for kw in ["env", "môi trường", "jwt", "api key", "key", "chạy", "run", "cài"]):
        return (
            project_prefix
            + "Để chạy backend: set JWT_SECRET_KEY, DATABASE_URL=postgresql+psycopg://..., "
            + "RESEARCH_LAB_ACCESS_CODE, CORS_ORIGINS. Để Nova dùng LLM thật, backend sẽ tự đọc ANTHROPIC_API_KEY/ANTHROPIC_AUTH_TOKEN "
            + "hoặc Claude CLI local; có thể chọn NOVA_MODEL. Frontend cần VITE_API_PROXY_TARGET trỏ đúng port backend."
            + attachment_note
        )

    if any(kw in msg_lower for kw in ["ví dụ", "vi du", "mẫu", "mau"]):
        return (
            "Bạn cứ đưa mình một tình huống mua thật: ngân sách, quận, loại tài sản, diện tích mong muốn và pháp lý. "
            "Mình sẽ lọc theo nhóm mẫu gần nhất rồi tư vấn hướng nào đáng xem, hướng nào nên tránh."
            + attachment_note
        )

    if any(kw in msg_lower for kw in ["pháp lý", "sổ đỏ", "sổ hồng", "quy hoạch", "giấy tờ"]):
        return (
            "Về pháp lý, Nova sẽ xem các điểm ảnh hưởng trực tiếp tới định giá: tình trạng sổ, quy hoạch, tranh chấp, "
            "khả năng sang tên, loại đất và mức hoàn thiện hồ sơ. Nếu bạn gửi khu vực + loại tài sản + tình trạng sổ, "
            "mình sẽ gắn rủi ro pháp lý vào adjustment ledger thay vì chỉ trả lời chung chung."
            + attachment_note
        )

    wants_search = any(kw in intent_text for kw in ["giá", "valuation", "định giá", "price", "nhà", "đất", "tìm", "tra", "tỷ", "ngân sách"])
    if wants_search:
        if any(kw in msg_lower for kw in ["2 tỷ", "2 ti", "2ty", "2 tỉ"]):
            return (
                "Với ngân sách khoảng 2 tỷ, mình cần biết thành phố/quận trước vì scope dự án khác nhau rất mạnh. "
                "Nếu chọn Quận 7 hoặc Bình Thạnh thì nhà phố hoàn chỉnh thường khó khớp 2 tỷ; hướng hợp lý hơn là căn hộ nhỏ, "
                "đất/nhà diện tích rất nhỏ hoặc hẻm sâu. Bạn gửi quận + loại tài sản + diện tích dự kiến, mình sẽ lọc theo comparable trong dataset."
                + attachment_note
            )
        if target_district:
            record_text = f"{district_row.get('records')} bản ghi" if district_row else "có dữ liệu trong scope"
            return (
                f"Mình tìm theo dữ liệu dự án cho {target_district.title()}. Khu vực này {record_text}. "
                "Để ra giá cụ thể mình cần thêm tối thiểu diện tích và loại tài sản. "
                "Nếu bạn chỉ hỏi xu hướng nhanh, mình sẽ lấy nhóm comparable cùng quận rồi so theo mặt tiền/hẻm, pháp lý và phường."
                + attachment_note
            )
        return (
            f"Mình có thể tìm giá theo dữ liệu dự án, nhưng bạn cần cho mình khu vực cụ thể trong scope: {districts}. "
            f"Dữ liệu hiện có khoảng {count or 'nhiều'} bản ghi. "
            "Bạn gửi dạng: 'nhà phố Quận 7, 80m², hẻm 5m, pháp lý rõ' là mình sẽ hướng dẫn định giá sát hơn."
            + attachment_note
        )

    if any(kw in msg_lower for kw in ["thị trường", "market", "xu hướng", "dữ liệu", "dataset"]):
        top_text = "; ".join(f"{x.get('district')} ({x.get('records')} bản ghi)" for x in top[:5])
        if top_text:
            return (
                project_prefix
                + f"Dataset hiện có khoảng {count or 'nhiều'} bản ghi, model mới nhất là {latest_model}. "
                + f"Scope tập trung vào {districts}. Nhóm nhiều bản ghi: {top_text}. "
                + "Thuật toán đi qua pipeline định giá gồm comparable matching, adjustment ledger, SDEV/market signal và fit suitability."
                + attachment_note
            )
        return (
            project_prefix
            + f"Dataset hiện có khoảng {count or 'nhiều'} bản ghi, model mới nhất là {latest_model}. Scope tập trung vào {districts}. "
            + "Thuật toán chính là pipeline định giá kết hợp comparable matching, adjustment ledger, SDEV/market signal và fit suitability."
            + attachment_note
        )

    if any(kw in msg_lower for kw in ["chào", "hello", "hi"]):
        return "Xin chào, tôi là Nova. Bạn cứ hỏi tự nhiên; nếu câu hỏi liên quan dự án AVM, tôi sẽ bám theo dữ liệu 3.560 bản ghi, scope 6 quận và pipeline định giá của hệ thống." + attachment_note

    if any(kw in msg_lower for kw in ["bạn là ai", "ban la ai", "who are you", "nova là ai", "nova la ai"]):
        return (
            "Tôi là Nova, trợ lý AI của Real Estate AVM. Tôi có hai lớp trả lời: chat tự nhiên qua AI provider khi provider ổn định, "
            "và lớp dữ liệu nội bộ PostgreSQL để trả lời ngay các câu hỏi BĐS bằng model, comparable matching, pháp lý và adjustment ledger. "
            "Vì vậy khi bạn hỏi giá, khu vực, ảnh nhà đất hoặc thị trường, tôi sẽ ưu tiên dữ liệu dự án trước thay vì trả lời chung chung."
            + attachment_note
        )

    if not is_project_question:
        return _natural_general_response(message, attachment_note)

    return (
        project_prefix
        + "Câu hỏi của bạn cần thêm ngữ cảnh. Nếu hỏi về BĐS, hãy cho tôi khu vực, loại tài sản, diện tích và mục tiêu cần phân tích. "
        + "Tôi vẫn có thể trả lời tiếp bằng dữ liệu nội bộ: scope gồm Cầu Giấy, Thanh Xuân, Đống Đa, Quận 7, Bình Thạnh và Tân Bình."
        + attachment_note
    )

@router.get("/health")
async def nova_health():
    provider = _provider()
    return {
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "provider": provider,
        "model": _model_name(),
        "api_key_configured": provider != "offline",
        "project_snapshot": get_project_snapshot(),
    }
