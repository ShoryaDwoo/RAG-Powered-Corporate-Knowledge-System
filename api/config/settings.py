"""
Central configuration — loaded once at startup.
All environment variables are read here; nothing else imports os.environ directly.

Employee → Role mapping:
  Stored in the EMPLOYEE_ROLE_MAP dict below, or overridden via the
  EMPLOYEE_ROLES env var as a comma-separated list of id=Role pairs:
    EMPLOYEE_ROLES=EMP001=HR-Admin,EMP002=Finance,EMP003=General-Staff
"""
import os
from dataclasses import dataclass, field
from dotenv import load_dotenv

load_dotenv()


@dataclass(frozen=True)
class Settings:
    # OpenAI
    #openai_api_key: str = field(default_factory=lambda: os.environ["OPENAI_API_KEY"])
    gemini_api_key: str = field(default_factory=lambda: os.environ["GEMINI_API_KEY"])

    # Qdrant
    qdrant_url: str = field(default_factory=lambda: os.getenv("QDRANT_URL", "http://98.82.167.144:6333"))
    qdrant_api_key: str | None = field(default_factory=lambda: os.getenv("QDRANT_API_KEY"))
    qdrant_collection: str = field(default_factory=lambda: os.getenv("QDRANT_COLLECTION", "hr_docs"))

    # Embedding
    embedding_model: str = field(default_factory=lambda: os.getenv(
        "EMBEDDING_MODEL", "sentence-transformers/all-MiniLM-L6-v2"
    ))
    embedding_dimensions: int = field(default_factory=lambda: int(
        os.getenv("EMBEDDING_DIMENSIONS", "384") 
    ))
    ollama_url: str = field(default_factory=lambda: os.getenv(
        "OLLAMA_URL", "http://<YOUR-EC2-PUBLIC-IP>:11434"
    ))
    ollama_model: str = field(default_factory=lambda: os.getenv(
        "OLLAMA_MODEL", "llama3.2:3b-instruct-q4_K_M"
    ))

    # Chunking
    md_chunk_size: int = field(default_factory=lambda: int(os.getenv("MD_CHUNK_SIZE", "512")))
    md_chunk_overlap: int = field(default_factory=lambda: int(os.getenv("MD_CHUNK_OVERLAP", "50")))
    pdf_child_chunk_size: int = field(default_factory=lambda: int(os.getenv("PDF_CHILD_CHUNK_SIZE", "200")))
    pdf_child_chunk_overlap: int = field(default_factory=lambda: int(os.getenv("PDF_CHILD_CHUNK_OVERLAP", "20")))
    pdf_parent_chunk_size: int = field(default_factory=lambda: int(os.getenv("PDF_PARENT_CHUNK_SIZE", "1024")))

    # Query
    top_k: int = field(default_factory=lambda: int(os.getenv("TOP_K_RESULTS", "5")))
    log_level: str = field(default_factory=lambda: os.getenv("LOG_LEVEL", "INFO"))


# Singleton — import this everywhere
cfg = Settings()


# ── Role permission hierarchy ──────────────────────────────────────
# Each role can see its own tier plus everything below it.
ROLE_PERMISSIONS: dict[str, list[str]] = {
    "HR-Admin":      ["HR-Admin", "Finance", "General-Staff", "Public"],
    "Finance":       ["Finance", "General-Staff", "Public"],
    "General-Staff": ["General-Staff", "Public"],
    "Contractor":    ["Public"],
}


# ── Employee → Role map ────────────────────────────────────────────
# Seed this dict with your actual employee IDs and roles.
# You can also override/extend it via the EMPLOYEE_ROLES env var:
#   EMPLOYEE_ROLES=EMP001=HR-Admin,EMP002=Finance,EMP003=General-Staff
_EMPLOYEE_ROLE_MAP: dict[str, str] = {
    "EMP001": "HR-Admin",
    # "EMP002": "Finance",
    # "EMP003": "General-Staff",
    # "EMP004": "Contractor",
}

# Merge overrides from environment variable
_env_roles = os.getenv("EMPLOYEE_ROLES", "")
if _env_roles:
    for pair in _env_roles.split(","):
        pair = pair.strip()
        if "=" in pair:
            emp_id, role = pair.split("=", 1)
            _EMPLOYEE_ROLE_MAP[emp_id.strip()] = role.strip()


def get_role_for_employee(employee_id: str) -> str | None:
    """
    Return the RBAC role for an employee_id, or None if not found.
    """
    return _EMPLOYEE_ROLE_MAP.get(employee_id)
