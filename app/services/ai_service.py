"""
Hugging Face Inference Providers — powers the "Ask the AI plant doctor" box
on the troubleshooter page and the "AI garden plan" card on the matchmaker
page. Completely optional: without a token the AI boxes stay hidden and the
rule-based diagnosis / matching works exactly as before.

Talks to the OpenAI-compatible router (free HF account token, free tier
includes monthly inference credits — no paid plan needed):
    POST https://router.huggingface.co/v1/chat/completions
Docs: https://huggingface.co/docs/inference-providers
"""
import time

import requests
from flask import current_app

ROUTER_URL = "https://router.huggingface.co/v1/chat/completions"

# Tried in order until one answers. Widely-served small instruct models - the
# router instantly rejects models no provider hosts with HTTP 400 "not
# supported by any provider you have enabled" (niche variants like
# Qwen2.5-7B-Instruct-1M included), so when that happens we move on to the
# next candidate instead of failing the whole request.
DEFAULT_MODELS = (
    "Qwen/Qwen2.5-7B-Instruct",
    "Qwen/Qwen3-8B",
    "mistralai/Mistral-7B-Instruct-v0.3",
)
MAX_ANSWER_TOKENS = 500
TEMPERATURE = 0.4

SYSTEM_PROMPT = (
    "You are Hamara Bagh's plant doctor — a friendly, practical master gardener "
    "writing for home gardeners in Pakistan. "
    "Guidelines: reply in the same language mix the user writes in (English, "
    "Roman Urdu or Urdu); keep it short and actionable — name the most likely "
    "cause, then give 2-4 concrete steps as a numbered list; assume Pakistan's "
    "climate (45C summers, monsoon, Punjab smog, Karachi humidity, northern "
    "frost); prefer organic and low-cost fixes first; never recommend specific "
    "pesticide brands or exact chemical doses; if the question is not about "
    "plants or gardening, politely steer back to gardening; if you are not "
    "sure, say so honestly; do not use emojis."
)


class AIUnavailable(Exception):
    """No Hugging Face token configured — the AI box stays hidden."""


class AIServiceError(Exception):
    """Upstream call failed; the message is safe to show to the user."""


def is_enabled():
    return bool((current_app.config.get("HUGGINGFACE_API_TOKEN") or "").strip())


def _candidate_models():
    """The configured model first (when set), then the widely-served defaults."""
    candidates = []
    configured = (current_app.config.get("HF_MODEL") or "").strip()
    if configured:
        candidates.append(configured)
    for model in DEFAULT_MODELS:
        if model not in candidates:
            candidates.append(model)
    return candidates


def _error_detail(resp):
    """Best-effort human-readable message from an upstream error body."""
    try:
        data = resp.json()
    except ValueError:
        return ""
    error = data.get("error") if isinstance(data, dict) else None
    if isinstance(error, dict):
        return (error.get("message") or "").strip()
    if isinstance(error, str):
        return error.strip()
    return ""


def _build_messages(question, plant=None, symptoms=None, causes=None,
                    extra_context=None, system_prompt=None):
    """Ground the question in whatever we already know from the page."""
    lines = []
    if plant:
        lines.append("Plant: " + plant)
    if symptoms:
        lines.append("Symptoms the user ticked in the app: " + "; ".join(symptoms))
    if causes:
        unique = []
        for cause in causes:
            if cause not in unique:
                unique.append(cause)
        lines.append(
            "The app's rules engine ranked these likely causes (use them as "
            "hints, correct them if the question suggests otherwise): "
            + "; ".join(unique[:6])
        )
    if extra_context:
        lines.append(extra_context)

    content = question
    if lines:
        content = "Context:\n" + "\n".join(lines) + "\n\nQuestion: " + question

    return [
        {"role": "system", "content": system_prompt or SYSTEM_PROMPT},
        {"role": "user", "content": content},
    ]


def ask_ai(question, plant=None, symptoms=None, causes=None,
           extra_context=None, system_prompt=None, max_tokens=None):
    """Send the question (plus any diagnosis context) through the HF router.

    Walks the candidate models until one answers. Returns {"answer": str,
    "model": str}. Raises AIUnavailable when no token is configured and
    AIServiceError with a user-friendly message on failure.
    """
    token = (current_app.config.get("HUGGINGFACE_API_TOKEN") or "").strip()
    if not token:
        raise AIUnavailable()

    messages = _build_messages(question, plant, symptoms, causes, extra_context, system_prompt)

    for model in _candidate_models():
        payload = {
            "model": model,
            "messages": messages,
            "max_tokens": max_tokens or MAX_ANSWER_TOKENS,
            "temperature": TEMPERATURE,
            "stream": False,
        }

        resp = None
        for attempt in range(4):  # network paths to HF can reset mid-connection — retry
            try:
                resp = requests.post(
                    ROUTER_URL,
                    json=payload,
                    headers={
                        "Authorization": f"Bearer {token}",
                        "Content-Type": "application/json",
                    },
                    timeout=current_app.config["AI_TIMEOUT_SECONDS"],
                )
                break
            except requests.Timeout:
                raise AIServiceError(
                    "The AI is taking too long to answer — check your internet and try again."
                )
            except requests.RequestException:
                if attempt < 3:
                    time.sleep(2 ** attempt)  # back off 1s, then 2s, then 4s
        if resp is None:
            raise AIServiceError(
                "Could not reach Hugging Face — the connection kept dropping. "
                "Check your internet or VPN and try again in a moment."
            )

        if resp.status_code == 400:
            detail = _error_detail(resp)
            if "not supported by any provider" in detail.lower():
                continue  # this model has no provider - try the next candidate
            if detail:
                raise AIServiceError(f"The AI service had a problem (HTTP 400): {detail}")
            raise AIServiceError(
                "The AI service had a problem (HTTP 400) — try again in a bit."
            )
        if resp.status_code in (401, 403):
            raise AIServiceError(
                "Hugging Face rejected the token — check HUGGINGFACE_API_TOKEN in .env "
                "(it needs the 'Make calls to Inference Providers' permission)."
            )
        if resp.status_code == 402:
            raise AIServiceError(
                "Your free Hugging Face credits are used up for now — they reset next "
                "month, or set a different HF_MODEL."
            )
        if resp.status_code == 429:
            raise AIServiceError("The AI is rate-limited right now — wait a moment and ask again.")
        if resp.status_code == 503:
            raise AIServiceError("The model is waking up — give it a few seconds and ask again.")

        try:
            resp.raise_for_status()
            data = resp.json()
        except requests.RequestException:
            raise AIServiceError(
                f"The AI service had a problem (HTTP {resp.status_code}) — try again in a bit."
            )
        except ValueError:
            raise AIServiceError("The AI sent back something unreadable — try again in a bit.")

        choices = data.get("choices") or []
        message = (choices[0].get("message") or {}) if choices else {}
        answer = (message.get("content") or "").strip()
        if not answer:
            raise AIServiceError("The AI returned an empty answer — rephrase the question and try again.")

        return {"answer": answer, "model": data.get("model") or model}

    raise AIServiceError(
        "No available model could answer with this Hugging Face token. Check the "
        "provider settings for your account at hf.co/settings/inference-providers, "
        "or set a different HF_MODEL in .env."
    )
