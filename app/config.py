import os
from dataclasses import dataclass
from dotenv import load_dotenv

load_dotenv()
os.environ.setdefault("GOOGLE_GENAI_USE_VERTEXAI", "False")  # Gemini API key only

_configured_model = os.getenv("GEMINI_MODEL", "gemini-2.5-flash-lite")
if _configured_model in ("gemini-2.5-flash", ""):
    _configured_model = "gemini-2.5-flash-lite"

@dataclass
class AgentConfig:
    # Default gemini-2.5-flash-lite to avoid 20 req/day quota limit of gemini-2.5-flash
    model: str = _configured_model
    mcp_server_port: int = 8090
    max_iterations: int = 3
    pii_redaction_enabled: bool = True
    injection_detection_enabled: bool = True

config = AgentConfig()
