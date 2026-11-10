from typing import List, Dict, Any, Optional, Union
from pydantic import BaseModel, Field

class ConfigResponse(BaseModel):
    required_features: List[str]
    version: str
    mode: str

class SessionRequest(BaseModel):
    site_key: str
    features: Dict[str, float]
    access_needs: List[str] = Field(default_factory=list)
    policy: Optional[str] = "P3"
    breach_cost: Optional[float] = 2.0

class SessionResponse(BaseModel):
    session_id: str
    action: str
    token: Optional[str] = None
    challenge: Optional[Dict[str, Any]] = None
    trace: Dict[str, Any]

class VerifyRequest(BaseModel):
    session_id: str
    challenge_id: str
    answer: Any
    interaction: Dict[str, Any] = Field(default_factory=dict)

class VerifyResponse(BaseModel):
    ok: bool
    token: Optional[str] = None
    attempts_left: int
    locked: bool
    error: Optional[str] = None
    new_challenge: Optional[Dict[str, Any]] = None

class SwitchRequest(BaseModel):
    session_id: str
    target_type: Optional[str] = None

class SessionNeedsRequest(BaseModel):
    session_id: str
    access_needs: List[str]

class SessionNeedsResponse(BaseModel):
    session_id: str
    challenge: Dict[str, Any]
    access_needs: List[str]
    allowed_ids: List[str]

class SiteVerifyRequest(BaseModel):
    token: str

class SiteVerifyResponse(BaseModel):
    success: bool
    challenge_type: Optional[str] = None
    band: Optional[str] = None
    ts: Optional[int] = None
    error: Optional[str] = None

class DemoLoginRequest(BaseModel):
    username: str
    password: str
    captcha_token: str

class DemoLoginResponse(BaseModel):
    success: bool
    message: str

