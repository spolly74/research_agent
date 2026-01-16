from app.core.database import engine, Base
from app.models.chat import ChatSession, Message

def init_db():
    Base.metadata.create_all(bind=engine)

if __name__ == "__main__":
    init_db()
