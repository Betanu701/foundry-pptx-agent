from __future__ import annotations

import argparse
import shutil
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
TEMPLATES = ROOT / "templates"


def main() -> None:
    parser = argparse.ArgumentParser(description="Import a local customer PowerPoint template without committing it.")
    parser.add_argument("source", help="Path to the source .pptx template")
    parser.add_argument("--template-id", default="customer-master-template")
    args = parser.parse_args()

    source = Path(args.source).expanduser().resolve()
    if not source.exists() or source.suffix.lower() != ".pptx":
        raise SystemExit(f"Expected a .pptx file, got: {source}")

    TEMPLATES.mkdir(parents=True, exist_ok=True)
    destination = TEMPLATES / f"{args.template_id}.pptx"
    shutil.copy2(source, destination)
    print(destination)


if __name__ == "__main__":
    main()
