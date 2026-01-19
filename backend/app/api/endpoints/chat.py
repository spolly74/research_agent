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

@router.post("/sessions/{session_id}/messages", response_model=Message)
def create_message(session_id: int, message: MessageCreate, db: Session = Depends(get_db)):
    # Verify session exists
    session = db.query(ChatSessionModel).filter(ChatSessionModel.id == session_id).first()
    if session is None:
        raise HTTPException(status_code=404, detail="Session not found")

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

@router.delete("/sessions/{session_id}", status_code=204)
def delete_session(session_id: int, db: Session = Depends(get_db)):
    session = db.query(ChatSessionModel).filter(ChatSessionModel.id == session_id).first()
    if session is None:
        raise HTTPException(status_code=404, detail="Session not found")

    db.delete(session)
    db.commit()
    return None
