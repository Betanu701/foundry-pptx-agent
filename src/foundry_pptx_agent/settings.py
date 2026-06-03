from __future__ import annotations

import os
from pathlib import Path


ROOT_DIR = Path(__file__).resolve().parents[2]
TEMPLATES_DIR = Path(os.getenv("TEMPLATES_DIR", ROOT_DIR / "templates")).resolve()
OUTPUT_DIR = Path(os.getenv("OUTPUT_DIR", ROOT_DIR / "generated")).resolve()
DEFAULT_TEMPLATE_ID = os.getenv("DEFAULT_TEMPLATE_ID", "sample-board-template")
PUBLIC_BASE_URL = os.getenv("PUBLIC_BASE_URL", "").rstrip("/")


def ensure_runtime_dirs() -> None:
    TEMPLATES_DIR.mkdir(parents=True, exist_ok=True)
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)


def template_path(template_id: str) -> Path:
    safe_id = template_id.replace("/", "").replace("\\", "")
    path = (TEMPLATES_DIR / f"{safe_id}.pptx").resolve()
    if not str(path).startswith(str(TEMPLATES_DIR)):
        raise ValueError("template_id resolved outside the templates directory")
    if not path.exists():
        raise FileNotFoundError(f"Template '{template_id}' was not found at {path}")
    return path


def template_contract_path(template_id: str) -> Path:
    safe_id = template_id.replace("/", "").replace("\\", "")
    return (TEMPLATES_DIR / f"{safe_id}.contract.json").resolve()


def artifact_url(filename: str) -> str:
    path = f"/api/artifacts/{filename}"
    return f"{PUBLIC_BASE_URL}{path}" if PUBLIC_BASE_URL else path
