"""Start the capstone API locally with privacy-conscious defaults."""

import os

os.environ.setdefault("CREWAI_DISABLE_TELEMETRY", "true")
os.environ.setdefault("OTEL_SDK_DISABLED", "true")
os.environ.setdefault("TOKENIZERS_PARALLELISM", "false")

if __name__ == "__main__":
    import uvicorn

    # Application JSONL logging masks identifiers. Default access logs expose URLs.
    uvicorn.run("api_app:app", host="127.0.0.1", port=8000, reload=False, access_log=False)
