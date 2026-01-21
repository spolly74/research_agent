const API_URL = "http://localhost:8000/api/chat";

export async function createSession(title: string = "New Chat") {
    const response = await fetch(`${API_URL}/sessions`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ title }),
    });
    return response.json();
}

export async function getSessions() {
    const response = await fetch(`${API_URL}/sessions`);
    return response.json();
}

export async function getSession(sessionId: number) {
    const response = await fetch(`${API_URL}/sessions/${sessionId}`);
    return response.json();
}

export async function sendMessage(sessionId: number, content: string) {
    const response = await fetch(`${API_URL}/sessions/${sessionId}/messages`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ role: "user", content }),
    });
    return response.json();
}


export async function deleteSession(sessionId: number) {
    const response = await fetch(`${API_URL}/sessions/${sessionId}`, {
        method: "DELETE",
    });
    return response.ok;
}

export async function updateSessionTitle(sessionId: number, title: string) {
    const response = await fetch(`${API_URL}/sessions/${sessionId}?title=${encodeURIComponent(title)}`, {
        method: "PATCH",
    });
    return response.json();
}

export async function getSessionHistory(sessionId: number) {
    const response = await fetch(`${API_URL}/sessions/${sessionId}/history`);
    return response.json();
}
