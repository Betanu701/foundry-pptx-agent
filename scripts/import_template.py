from __future__ import annotations

import argparse
from pathlib import Path

from foundry_pptx_agent.template_onboarding import onboard_template


def main() -> None:
    parser = argparse.ArgumentParser(description="Import and onboard a local customer PowerPoint template.")
    parser.add_argument("source", help="Path to the source .pptx template")
    parser.add_argument("--template-id", default="customer-master-template")
    parser.add_argument("--overwrite", action="store_true", help="Replace existing template and contract files.")
    args = parser.parse_args()

    source = Path(args.source).expanduser().resolve()
    result = onboard_template(source, args.template_id, args.overwrite)
    print(f"Template: {result['template_path']}")
    print(f"Contract: {result['contract_path']}")
    print("Inferred layout map:")
    for intent, layout_index in result["contract"]["layout_map"].items():
        layout = result["contract"]["layout_catalog"][layout_index]
        print(f"  {intent}: {layout_index} ({layout['name']})")


if __name__ == "__main__":
    main()
