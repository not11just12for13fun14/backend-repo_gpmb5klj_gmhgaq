"""
Database Schemas

Define your MongoDB collection schemas here using Pydantic models.
These schemas are used for data validation in your application.

Each Pydantic model represents a collection in your database.
Model name is converted to lowercase for the collection name:
- User -> "user" collection
- Product -> "product" collection
- BlogPost -> "blogs" collection
"""

from pydantic import BaseModel, Field
from typing import Optional, Dict, List

# Core game schemas for Litera

class Player(BaseModel):
    """
    Player profile/state
    Collection name: "player"
    """
    session_id: str = Field(..., description="Client-generated session identifier")
    public_trust: int = Field(50, ge=0, le=100)
    personal_clout: int = Field(50, ge=0, le=100)
    professional_skill: int = Field(0, ge=0, le=100)
    relationships: Dict[str, int] = Field(default_factory=dict, description="Character -> affinity score 0-100")

class ActionLog(BaseModel):
    """
    Logs player actions across modules
    Collection name: "actionlog"
    """
    session_id: str
    module: str = Field(..., description="prebunking | ethical | professional")
    action_type: str
    payload: Dict = Field(default_factory=dict)
    outcome: Dict = Field(default_factory=dict)

class PrebunkingPost(BaseModel):
    """
    Seed content for the feed (not strictly required for gameplay)
    Collection name: "prebunkingpost"
    """
    post_id: str
    content: str
    source: str
    technique: str = Field(..., description="manipulation technique, e.g., 'emotion', 'false context'")
    label: str = Field(..., description="verified | misleading | hoax")
    hints: List[str] = Field(default_factory=list)

# Legacy example schemas kept for reference (unused by the game):

class User(BaseModel):
    name: str
    email: str
    address: str
    age: Optional[int] = None
    is_active: bool = True

class Product(BaseModel):
    title: str
    description: Optional[str] = None
    price: float
    category: str
    in_stock: bool = True
