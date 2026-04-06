import asyncio
from typing import List, Optional
from pathlib import Path
from datetime import datetime, timedelta
from app.config import settings
from app.security.guardrails import validate_ai_response
from app.services.embedding_service import search as embedding_search, build_index
from app.services.log_service import get_logs_by_ids, get_logs_for_embedding, get_user_log_ids
from app.models.user import ChatMessage

from llama_cpp import Llama

_llm: Llama = None


def _load_model() -> None:
    global _llm
    if _llm is not None:
        return
    import os
    n_threads = int(os.cpu_count() or 4)
    _llm = Llama(
        model_path=settings.gguf_model_path,
        n_ctx=4096,
        n_threads=n_threads,
        n_batch=512,
        verbose=False,
    )


def generate_text(prompt, max_new_tokens: int = 150) -> str:
    _load_model()
    if isinstance(prompt, dict):
        messages = [{"role": "system", "content": prompt["system"]}]
        messages.extend(prompt["messages"])
        out = _llm.create_chat_completion(
            messages=messages,
            max_tokens=max_new_tokens,
            temperature=0.3,
            top_p=0.9,
            repeat_penalty=1.2,
        )
        text = out["choices"][0]["message"]["content"].strip()
        finish = out["choices"][0].get("finish_reason", "")
        # If truncated by length, clean up and add follow-up
        if finish == "length" and text:
            # Trim to last complete sentence
            for end in ['. ', '! ', '? ', '.\n', '!\n', '?\n']:
                idx = text.rfind(end)
                if idx > len(text) // 3:
                    text = text[:idx + 1]
                    break
            text += "\n\nWould you like me to go into more detail on this?"
        return text
    else:
        out = _llm(
            prompt,
            max_tokens=max_new_tokens,
            temperature=0.3,
            top_p=0.9,
            repeat_penalty=1.2,
            stop=["Question:", "User:"],
            echo=False,
        )
        return out["choices"][0]["text"].strip()


def _format_log_context(logs: List[dict], max_logs: int = 20) -> str:
    lines = []
    for i, log in enumerate(logs[:max_logs]):
        ts = log.get("timestamp", "")
        if hasattr(ts, "isoformat"):
            ts = ts.isoformat()[:19]
        desc = log.get("description") or ""
        meta = log.get("metadata", {})
        meta_str = ", ".join(f"{k}={v}" for k, v in meta.items()) if meta else ""
        parts = [
            f"  Time: {ts}",
            f"  Module: {log.get('module', '')}",
            f"  Action: {log.get('action', '')}",
            f"  Category: {log.get('category', '')}",
        ]
        if log.get("entity"):
            parts.append(f"  Entity: {log['entity']}")
        if desc:
            parts.append(f"  Description: {desc}")
        if meta_str:
            parts.append(f"  Details: {meta_str}")
        lines.append(f"Entry {i+1}:\n" + "\n".join(parts))
    return "\n\n".join(lines)


def _format_conversation_history(messages: List[ChatMessage]) -> str:
    lines = []
    for msg in messages:
        prefix = "User" if msg.role == "user" else "Assistant"
        lines.append(f"{prefix}: {msg.content}")
    return "\n".join(lines)


async def _rebuild_index_in_background() -> None:
    log_docs = await get_logs_for_embedding(user_id=None)
    await asyncio.to_thread(build_index, log_docs)


async def query_logs_with_ai(
    query: str,
    user_id: str,
    top_k: int = 10,
    conversation_history: Optional[List[ChatMessage]] = None,
) -> str:
    allowed_ids = await get_user_log_ids(user_id)

    if not allowed_ids:
        return "No activity logs found for this account yet. Once you start using the app, your actions will be recorded and I can help you analyse them."

    # Enrich vague follow-ups with recent conversation context so the
    # embedding search retrieves relevant logs instead of random ones.
    search_query = query
    if conversation_history:
        recent = conversation_history[-4:]
        context_parts = [m.content for m in recent]
        search_query = " ".join(context_parts) + " " + query

    results = embedding_search(search_query, top_k=top_k, allowed_log_ids=allowed_ids)

    if not results:
        # FAISS index may be empty or stale — fall back to the most recent logs
        # directly from MongoDB so the AI can still answer the question.
        matched_logs = await get_logs_for_embedding(user_id=user_id)
        if not matched_logs:
            return (
                "No log entries matched your query. Try rephrasing or asking about specific "
                "modules (e.g. 'auth', 'bucketlist'), actions, or time periods."
            )
        matched_logs = matched_logs[:top_k]
        # Rebuild FAISS in the background so future queries use semantic search
        asyncio.create_task(_rebuild_index_in_background())
    else:
        matched_ids = [log_id for log_id, _ in results]
        matched_logs = await get_logs_by_ids(matched_ids)
        score_map = {log_id: score for log_id, score in results}
        matched_logs.sort(key=lambda l: score_map.get(l["log_id"], 0), reverse=True)

    context = _format_log_context(matched_logs, max_logs=10)

    system_msg = (
        "You are a helpful AI assistant for a user named after their account. "
        "You can answer general knowledge questions using your training data. "
        "When the user asks about their activity, actions, or history, use the activity logs below to give specific answers with dates, times, and details. "
        "Format dates in a human-readable way (e.g. March 31, 2026 at 10:15 AM). "
        "Use the conversation history to understand follow-up questions. "
        "RULES: "
        "1) Keep answers SHORT — use 3-5 bullet points max, no long lists. "
        "2) ALWAYS end your response with a question like 'Would you like to know more?' or 'Do you have any other questions?'\n\n"
        f"Activity Logs:\n{context}"
    )

    messages = []
    if conversation_history:
        last = conversation_history[-6:] if len(conversation_history) > 6 else conversation_history
        for msg in last:
            messages.append({"role": msg.role, "content": msg.content})
    messages.append({"role": "user", "content": query})

    prompt = {"system": system_msg, "messages": messages}

    raw_response = await asyncio.to_thread(generate_text, prompt, 700)
    return validate_ai_response(raw_response)


async def generate_summary(
    user_id: str,
    days: int = 7,
    module: Optional[str] = None,
) -> str:
    logs = await get_logs_for_embedding(user_id=user_id)

    if module:
        logs = [l for l in logs if l.get("module") == module]

    if not logs:
        return "No activity logs found for this user."

    cutoff = datetime.utcnow() - timedelta(days=days)
    recent = []
    for l in logs:
        ts = l.get("timestamp")
        if ts is None:
            continue
        if isinstance(ts, str):
            try:
                ts = datetime.fromisoformat(ts)
            except Exception:
                continue
        if isinstance(ts, datetime) and ts >= cutoff:
            recent.append(l)

    if not recent:
        return f"No activity found in the last {days} day(s) for this user."

    # Build stats for structured summary
    modules = {}
    categories = {}
    errors = []
    for l in recent:
        mod = l.get("module", "unknown")
        cat = l.get("category", "unknown")
        modules[mod] = modules.get(mod, 0) + 1
        categories[cat] = categories.get(cat, 0) + 1
        if cat == "ERROR":
            errors.append(l)

    context = _format_log_context(recent, max_logs=25)

    mod_summary = ", ".join(f"{k} ({v} events)" for k, v in sorted(modules.items(), key=lambda x: -x[1]))
    cat_summary = ", ".join(f"{k} ({v})" for k, v in sorted(categories.items(), key=lambda x: -x[1]))
    error_summary = f"{len(errors)} error(s) detected" if errors else "No errors detected"

    prompt = {
        "system": (
            f"You are a log analysis assistant. Provide a detailed activity summary.\n"
            f"Be specific and descriptive. Reference actual data from the logs.\n\n"
            f"Activity period: last {days} day(s)\n"
            f"Total events: {len(recent)}\n"
            f"Modules active: {mod_summary}\n"
            f"Categories: {cat_summary}\n"
            f"Errors: {error_summary}\n\n"
            f"Detailed log entries:\n\n{context}"
        ),
        "messages": [{"role": "user", "content": (
            "Write a structured summary covering:\n"
            "1. Activity Overview\n"
            "2. Key Actions with timestamps\n"
            "3. Patterns and trends\n"
            "4. Issues or errors\n"
            "5. Recommendations"
        )}],
    }

    raw_text = await asyncio.to_thread(generate_text, prompt, 512)
    return validate_ai_response(raw_text)
