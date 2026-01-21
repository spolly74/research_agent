from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List

from app.core.database import get_db
from app.models.chat import ChatSession as ChatSessionModel, Message as MessageModel
from app.schemas.chat import ChatSession, ChatSessionCreate, Message, MessageCreate

router = APIRouter()

@router.post("/sessions", response_model=ChatSession)
def create_session(session: ChatSessionCreate, db: Session = Depends(get_db)):
    db_session = ChatSessionModel(title=session.title)
    db.add(db_session)
    db.commit()
    db.refresh(db_session)
    return db_session

@router.get("/sessions", response_model=List[ChatSession])
def get_sessions(skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
    sessions = db.query(ChatSessionModel).order_by(ChatSessionModel.updated_at.desc()).offset(skip).limit(limit).all()
    return sessions

@router.get("/sessions/{session_id}", response_model=ChatSession)
def get_session(session_id: int, db: Session = Depends(get_db)):
    session = db.query(ChatSessionModel).filter(ChatSessionModel.id == session_id).first()
    if session is None:
        raise HTTPException(status_code=404, detail="Session not found")
    return session

def generate_title_from_query(query: str, max_length: int = 40) -> str:
    """Generate an intelligent title from the user's query using LLM."""
    try:
        from app.core.llm import get_llm
        from langchain_core.messages import HumanMessage, SystemMessage

        llm = get_llm()

        messages = [
            SystemMessage(content="""Generate a very short title (3-6 words) that summarizes the main topic of this research request.
Rules:
- Be specific about the subject matter
- Use title case
- No quotes or punctuation at the end
- Focus on the core topic, not the request type
- Maximum 40 characters

Examples:
- "Write a report on climate change effects" -> "Climate Change Effects"
- "Research the history of artificial intelligence" -> "History of AI"
- "Tell me about quantum computing applications" -> "Quantum Computing Applications"
- "Analyze the impact of social media on teens" -> "Social Media Impact on Teens"

Just respond with the title, nothing else."""),
            HumanMessage(content=query)
        ]

        response = llm.invoke(messages)
        title = response.content.strip().strip('"\'')

        # Ensure it's not too long
        if len(title) > max_length:
            title = title[:max_length].rsplit(" ", 1)[0]

        return title if title else "Research Task"

    except Exception as e:
        # Fallback to simple extraction if LLM fails
        import logging
        logging.warning(f"LLM title generation failed: {e}, using fallback")

        prefixes = ["research", "write a report on", "tell me about", "what is", "explain", "analyze"]
        query_lower = query.lower().strip()
        for prefix in prefixes:
            if query_lower.startswith(prefix):
                query = query[len(prefix):].strip()
                break

        title = query.strip().strip("?.,!").strip()
        if len(title) > max_length:
            title = title[:max_length].rsplit(" ", 1)[0] + "..."

        return title.title() if title else "Research Task"


@router.post("/sessions/{session_id}/messages", response_model=Message)
def create_message(session_id: int, message: MessageCreate, db: Session = Depends(get_db)):
    # Verify session exists
    session = db.query(ChatSessionModel).filter(ChatSessionModel.id == session_id).first()
    if session is None:
        raise HTTPException(status_code=404, detail="Session not found")

    # Auto-generate title from first user message if title is default
    if session.title == "New Chat" and message.role == "user":
        session.title = generate_title_from_query(message.content)
        db.commit()

    db_message = MessageModel(**message.model_dump(), session_id=session_id)
    db.add(db_message)
    db.commit()
    db.refresh(db_message)

    # Start execution tracking
    from app.core.execution_tracker import get_execution_tracker
    tracker = get_execution_tracker()
    tracking_session_id = f"chat-{session_id}"
    tracker.start_session(tracking_session_id, message.content)

    # Trigger Agent Workflow
    from app.agents.graph import graph
    from langchain_core.messages import HumanMessage

    try:
        # Run the graph with session_id for tracking
        inputs = {
            "messages": [HumanMessage(content=message.content)],
            "session_id": tracking_session_id
        }
        config = {"configurable": {"thread_id": str(session_id)}}
        result = graph.invoke(inputs, config=config)

        # Save Authorization/Final Result
        final_content = result.get("final_report", "Processing complete.")
        if not final_content:
            final_content = result["messages"][-1].content

        # Mark session complete
        tracker.complete_session(tracking_session_id, final_content[:200] if final_content else "")

    except Exception as e:
        # Record error in tracking
        tracker.record_error(tracking_session_id, str(e), recoverable=False)
        raise

    ai_message = MessageModel(
        role="assistant",
        content=final_content,
        session_id=session_id
    )
    db.add(ai_message)
    db.commit()
    db.refresh(ai_message)

    return db_message

@router.get("/sessions/{session_id}/plan")
def get_session_plan(session_id: int):
    from app.agents.graph import graph

    config = {"configurable": {"thread_id": str(session_id)}}
    try:
        current_state = graph.get_state(config)
        if not current_state or not current_state.values:
            return {"status": "no_state", "plan": None}

        plan = current_state.values.get("plan")
        return {"status": "active", "plan": plan}
    except Exception as e:
        return {"status": "error", "error": str(e)}

@router.patch("/sessions/{session_id}", response_model=ChatSession)
def update_session(session_id: int, title: str, db: Session = Depends(get_db)):
    """Update session title."""
    session = db.query(ChatSessionModel).filter(ChatSessionModel.id == session_id).first()
    if session is None:
        raise HTTPException(status_code=404, detail="Session not found")

    session.title = title
    db.commit()
    db.refresh(session)
    return session


@router.get("/sessions/{session_id}/history")
def get_session_history(session_id: int):
    """Get execution history for a session."""
    from app.core.execution_tracker import get_execution_tracker

    tracker = get_execution_tracker()
    tracking_session_id = f"chat-{session_id}"
    status = tracker.get_status(tracking_session_id)

    if not status:
        return {"session_id": session_id, "status": "not_found", "current_phase": "", "agents_used": [], "tools_used": []}

    # Extract unique agent names from history
    agents_used = list(set(a.agent_name for a in status.agent_history))

    # Extract unique tool names from all agent executions
    tools_used = set()
    for agent_exec in status.agent_history:
        for tool in agent_exec.tools_used:
            tools_used.add(tool.tool_name)

    return {
        "session_id": session_id,
        "status": status.current_phase.value if hasattr(status.current_phase, 'value') else str(status.current_phase),
        "current_phase": status.current_phase.value if hasattr(status.current_phase, 'value') else str(status.current_phase),
        "agents_used": agents_used,
        "tools_used": list(tools_used),
        "started_at": status.started_at.isoformat() if status.started_at else None,
        "completed_at": status.completed_at.isoformat() if status.completed_at else None,
        "error": status.error
    }


@router.delete("/sessions/{session_id}", status_code=204)
def delete_session(session_id: int, db: Session = Depends(get_db)):
    session = db.query(ChatSessionModel).filter(ChatSessionModel.id == session_id).first()
    if session is None:
        raise HTTPException(status_code=404, detail="Session not found")

    db.delete(session)
    db.commit()
    return None
