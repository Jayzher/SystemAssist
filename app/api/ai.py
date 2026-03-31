from fastapi import APIRouter, Depends, HTTPException, status
from app.models.user import ChatRequest, SummaryRequest
from app.security.rbac import verify_api_key, get_user_context
from app.security.guardrails import detect_prompt_injection, sanitize_query
from app.services.ai_service import query_logs_with_ai, generate_summary
from app.services.session_service import get_or_create_session, append_message, get_conversation_history
from app.services.log_service import get_logs_for_embedding
from app.services.embedding_service import build_index

router = APIRouter(prefix="/api", tags=["ai"])


@router.post("/chat", summary="AI-powered log query with session support for follow-ups")
async def ai_chat(req: ChatRequest, user_ctx: dict = Depends(get_user_context)):
    if user_ctx["auth_type"] == "session_token":
        effective_user_id = user_ctx["user_id"]
    else:
        if not req.user_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="user_id is required in the request body when authenticating via X-Api-Key.",
            )
        effective_user_id = req.user_id

    cleaned = sanitize_query(req.query)
    if detect_prompt_injection(cleaned):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Your query contains disallowed patterns. Please rephrase.",
        )

    session = await get_or_create_session(effective_user_id, req.session_id)
    history = await get_conversation_history(session.session_id)

    await append_message(session.session_id, "user", cleaned)

    response = await query_logs_with_ai(
        query=cleaned,
        user_id=effective_user_id,
        top_k=req.limit,
        conversation_history=history if history else None,
    )

    await append_message(session.session_id, "assistant", response)

    return {
        "status": "ok",
        "session_id": session.session_id,
        "query": cleaned,
        "response": response,
    }


@router.post("/summary", summary="Generate an activity summary for a user")
async def get_summary(req: SummaryRequest, _: str = Depends(verify_api_key)):
    response = await generate_summary(
        user_id=req.user_id,
        days=req.days,
        module=req.module,
    )
    return {"status": "ok", "user_id": req.user_id, "summary": response}


@router.post("/reindex", summary="Rebuild the FAISS search index from all logs")
async def reindex(_: str = Depends(verify_api_key)):
    log_docs = await get_logs_for_embedding(user_id=None)
    index, ids = build_index(log_docs)
    return {"status": "ok", "indexed": index.ntotal}
