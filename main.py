import os
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Dict, List, Optional

from database import db, create_document, get_documents
from schemas import Player, ActionLog

app = FastAPI(title="Litera API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/")
def read_root():
    return {"message": "Litera backend running"}

# Utility

def get_player_collection_name():
    return Player.__name__.lower()

# Models for requests

class StartSessionRequest(BaseModel):
    session_id: str

class ChoiceRequest(BaseModel):
    session_id: str
    module: str  # "prebunking" | "ethical" | "professional"
    action_type: str
    payload: Dict = {}

# Endpoints

@app.post("/api/start")
def start_session(body: StartSessionRequest):
    # Check if player exists
    existing = db[get_player_collection_name()].find_one({"session_id": body.session_id})
    if existing:
        return {
            "session_id": body.session_id,
            "public_trust": existing.get("public_trust", 50),
            "personal_clout": existing.get("personal_clout", 50),
            "professional_skill": existing.get("professional_skill", 0),
            "relationships": existing.get("relationships", {}),
        }

    player = Player(session_id=body.session_id)
    create_document(get_player_collection_name(), player)
    return player.model_dump()

@app.post("/api/choice")
def submit_choice(body: ChoiceRequest):
    # Fetch player
    player_doc = db[get_player_collection_name()].find_one({"session_id": body.session_id})
    if not player_doc:
        raise HTTPException(status_code=404, detail="Session not found. Start first.")

    public_trust = player_doc.get("public_trust", 50)
    personal_clout = player_doc.get("personal_clout", 50)
    professional_skill = player_doc.get("professional_skill", 0)
    relationships: Dict[str, int] = player_doc.get("relationships", {})

    outcome: Dict = {}

    module = body.module.lower()
    if module == "prebunking":
        label = body.payload.get("label")  # user decision: verified|misleading|hoax
        truth = body.payload.get("truth")  # ground truth from scenario
        if label == truth:
            public_trust = min(100, public_trust + 5)
            personal_clout = max(0, personal_clout - 1) if truth != "verified" else min(100, personal_clout + 2)
            outcome = {"message": "Good call.", "delta": {"public_trust": +5, "personal_clout": (+2 if truth=="verified" else -1)}}
        else:
            public_trust = max(0, public_trust - 8)
            personal_clout = min(100, personal_clout + 4) if label != "verified" else max(0, personal_clout - 2)
            outcome = {"message": "That choice undermined trust.", "delta": {"public_trust": -8, "personal_clout": (+4 if label!="verified" else -2)}}

    elif module == "ethical":
        choice = body.payload.get("choice")  # intervene|report|stay_silent|participate
        if choice == "intervene":
            public_trust = min(100, public_trust + 6)
            for k in ["victim", "bystander"]:
                relationships[k] = min(100, relationships.get(k, 50) + 8)
            outcome = {"message": "You stood up. Respect earned.", "delta": {"public_trust": +6, "relationships": {"victim": +8, "bystander": +8}}}
        elif choice == "report":
            public_trust = min(100, public_trust + 4)
            relationships["victim"] = min(100, relationships.get("victim", 50) + 6)
            outcome = {"message": "You reported the issue.", "delta": {"public_trust": +4, "relationships": {"victim": +6}}}
        elif choice == "stay_silent":
            public_trust = max(0, public_trust - 5)
            relationships["victim"] = max(0, relationships.get("victim", 50) - 7)
            outcome = {"message": "Silence has a cost.", "delta": {"public_trust": -5, "relationships": {"victim": -7}}}
        elif choice == "participate":
            public_trust = max(0, public_trust - 12)
            for k in ["victim", "bystander"]:
                relationships[k] = max(0, relationships.get(k, 50) - 10)
            outcome = {"message": "Harmful choice hurt your standing.", "delta": {"public_trust": -12, "relationships": {"victim": -10, "bystander": -10}}}
        else:
            outcome = {"message": "No effect"}

    elif module == "professional":
        task = body.payload.get("task")  # meeting|email|collab
        success = body.payload.get("success", False)
        if success:
            professional_skill = min(100, professional_skill + 7)
            public_trust = min(100, public_trust + 2)
            outcome = {"message": "Professional skill leveled up!", "delta": {"professional_skill": +7, "public_trust": +2}}
        else:
            professional_skill = max(0, professional_skill - 2)
            outcome = {"message": "Incomplete attempt. Try again.", "delta": {"professional_skill": -2}}
    else:
        raise HTTPException(status_code=400, detail="Unknown module")

    # Persist changes
    db[get_player_collection_name()].update_one(
        {"session_id": body.session_id},
        {"$set": {
            "public_trust": public_trust,
            "personal_clout": personal_clout,
            "professional_skill": professional_skill,
            "relationships": relationships,
        }}
    )

    # Log action
    log = ActionLog(
        session_id=body.session_id,
        module=module,
        action_type=body.action_type,
        payload=body.payload,
        outcome=outcome,
    )
    create_document(ActionLog.__name__.lower(), log)

    return {
        "session_id": body.session_id,
        "public_trust": public_trust,
        "personal_clout": personal_clout,
        "professional_skill": professional_skill,
        "relationships": relationships,
        "outcome": outcome,
    }

@app.get("/test")
def test_database():
    response = {
        "backend": "✅ Running",
        "database": "❌ Not Available",
        "database_url": None,
        "database_name": None,
        "connection_status": "Not Connected",
        "collections": []
    }
    try:
        if db is not None:
            response["database"] = "✅ Available"
            response["database_url"] = "✅ Configured"
            response["database_name"] = db.name
            response["connection_status"] = "Connected"
            collections = db.list_collection_names()
            response["collections"] = collections[:10]
            response["database"] = "✅ Connected & Working"
    except Exception as e:
        response["database"] = f"❌ Error: {str(e)[:80]}"

    # Check env
    response["database_url"] = "✅ Set" if os.getenv("DATABASE_URL") else "❌ Not Set"
    response["database_name"] = "✅ Set" if os.getenv("DATABASE_NAME") else "❌ Not Set"
    return response

if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)
