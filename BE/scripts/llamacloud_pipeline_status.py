#!/usr/bin/env python3
"""Show LlamaCloud pipeline status, file counts, and error messages."""

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from dotenv import load_dotenv

load_dotenv(ROOT / ".env")

from app.core.config import settings
from llama_cloud import LlamaCloud


def main() -> None:
    pipeline_id = settings.LLAMA_CLOUD_PIPELINE_ID
    if len(sys.argv) > 1:
        pipeline_id = sys.argv[1]
    if not pipeline_id:
        raise SystemExit("Set LLAMA_CLOUD_PIPELINE_ID or pass pipeline id as argument.")
    if not settings.LLAMA_CLOUD_API_KEY:
        raise SystemExit("Set LLAMA_CLOUD_API_KEY in BE/.env")

    client = LlamaCloud(api_key=settings.LLAMA_CLOUD_API_KEY)
    st = client.pipelines.get_status(pipeline_id=pipeline_id, full_details=True)
    fc = client.pipelines.files.get_status_counts(pipeline_id=pipeline_id)

    print(f"Pipeline: {pipeline_id}")
    print(f"Status: {st.status}")
    print(f"File counts: {fc.counts} (total={fc.total_count})")
    if st.error:
        print("\nErrors:")
        for err in st.error:
            print(f"  step={err.step}")
            print(f"  {err.message[:500]}")
            if len(err.message) > 500:
                print("  ...")

    success = (fc.counts or {}).get("SUCCESS", 0)
    if success > 0:
        print("\nIndex is ready for retrieval.")
    else:
        print("\nIndex is NOT ready — no successful files yet.")


if __name__ == "__main__":
    main()
