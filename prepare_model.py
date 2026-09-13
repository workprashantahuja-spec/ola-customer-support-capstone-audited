"""One-time online setup; indexing and searching run offline afterwards."""

import json
import os

from rag_config import MODEL_DIR, MODEL_ID, MODEL_REVISION


def model_weights_are_readable():
    weights = MODEL_DIR / "model.safetensors"
    if not weights.is_file():
        return False
    try:
        from safetensors import safe_open
        with safe_open(weights, framework="pt") as handle:
            return bool(handle.keys())
    except Exception:
        return False


def main():
    # Setup is the only project command that deliberately downloads a model.
    os.environ["HF_HUB_DISABLE_TELEMETRY"] = "1"
    from huggingface_hub import snapshot_download

    download_options = dict(
        repo_id=MODEL_ID,
        revision=MODEL_REVISION,
        local_dir=str(MODEL_DIR),
        allow_patterns=[
            "*.json", "*.txt", "model.safetensors", "1_Pooling/config.json",
        ],
        ignore_patterns=["onnx/*", "openvino/*"],
    )
    snapshot_download(**download_options)
    if not model_weights_are_readable():
        # Recover a partial or interrupted weight download during setup.
        snapshot_download(**download_options, force_download=True)
    required = ["modules.json", "config.json", "model.safetensors", "tokenizer.json",
                "1_Pooling/config.json"]
    missing = [name for name in required if not (MODEL_DIR / name).is_file()]
    if missing:
        raise RuntimeError(f"Incomplete model download: {missing}")
    if not model_weights_are_readable():
        raise RuntimeError("Downloaded model weights are unreadable")
    marker = {"model_id": MODEL_ID, "revision": MODEL_REVISION}
    (MODEL_DIR / "capstone_model.json").write_text(
        json.dumps(marker, indent=2) + "\n", encoding="utf-8"
    )
    print(json.dumps({"model_prepared": True, **marker,
                      "next_command": "python rag_index.py build"}, indent=2))


if __name__ == "__main__":
    main()
