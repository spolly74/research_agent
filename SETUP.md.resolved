# Research Agent Setup Guide

Follow these steps to configure the project on a new machine.

## Prerequisites
- **OS**: Mac or Linux recommended.
- **Python**: Version 3.11 or higher.
- **Node.js**: Version 18 or higher.
- **Ollama**: Installed and running ([Download Ollama](https://ollama.com/)).

## 1. AI Model Setup (Ollama)
The agent uses local LLMs. Ensure Ollama is running and pull the required model:
```bash
ollama serve
# In a new terminal:
ollama pull llama3.2
```

## 2. Backend Setup
Navigate to the `backend` directory.

### Install Dependencies
```bash
cd backend
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
playwright install  # Required for the browser tool
```

### Configuration (.env)
Create a [.env](file:///Users/scott/repos/research_agent/backend/.env) file in `backend/` with the following keys:
```env
LINKUP_API_KEY=your_key_here
```
*(You can get a free key from Linkup if needed for search)*

### Run Server
```bash
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```
The API will be available at `http://localhost:8000`.

## 3. Frontend Setup
Navigate to the `frontend` directory.

### Install & Run
```bash
cd frontend
npm install
npm run dev
```
The UI will run at `http://localhost:5173`.

## 4. Verification
1. Open the UI.
2. Type "Hi" to test the `Answer` path.
3. Type "Research the history of [Topic]" to test the `Research` path.
