#!/usr/bin/env python3
"""In-process image-to-3D: imports buddy-cloud functions to avoid arg length limits."""
import sys
import os
import base64
import importlib.util

# Add buddy-cloud script directory
SCRIPT_DIR = r"E:\Workbuddy\resources\app.asar.unpacked\resources\builtin-skills\buddy-multimodal-generation\scripts"

# Import buddy-cloud module (hyphenated name, so use importlib)
spec = importlib.util.spec_from_file_location("buddy_cloud", 
    os.path.join(SCRIPT_DIR, "buddy-cloud.py"))
bc = importlib.util.module_from_spec(spec)
sys.path.insert(0, SCRIPT_DIR)
spec.loader.exec_module(bc)

# Now use buddy_cloud functions directly - no CLI arg limits
TOKEN = "tk_nsCz5eX6yTvznFMcGORhrCBXhYDtUD4a"

# Build the 3D body with image base64
with open(r"E:\WorkSpaceForWorkbuddy\绘梨衣\downloads\Anime_style_character_sheet_of_2026-06-14T17-34-41.png", "rb") as f:
    b64 = base64.b64encode(f.read()).decode("utf-8")

print(f"Image encoded: {len(b64)} chars")

body = bc._build_3d_body(
    prompt="",
    image_base64=b64,
    enable_pbr=True,
    face_count=1200000,
    generate_type="Normal",
    result_format="FBX",
)

print(f"Body built, submitting...")

# Call API using the built-in functions
cfg = bc._PROVIDER_MAP["3d"]
endpoint = bc._DEFAULT_ENDPOINT

submit_resp = bc._call_api(
    endpoint, cfg["provider"], cfg["service"], cfg["version"],
    cfg["submit_action"], body, TOKEN,
)

print(f"Submit response: {bc._redact_token(str(submit_resp))[:2000]}")
