#!/usr/bin/env python3
"""Image-to-3D via Hunyuan 3D tcproxy with TC3-HMAC-SHA256 signing.
Encodes local image as base64 and submits directly via the tcproxy endpoint."""

import sys
import json
import time
import base64
import hashlib
import hmac
import datetime
import requests
from pathlib import Path

# --------------------------------------------------------------------------
# Configuration
# --------------------------------------------------------------------------
TOKEN = "tk_nsCz5eX6yTvznFMcGORhrCBXhYDtUD4a"
ENDPOINT = "https://copilot.tencent.com/agenttool/v1/tcproxy"
SECRET_ID = "codebuddy"

# 3D provider config
PROVIDER = "hk-3d"
SERVICE = "ai3d"
VERSION = "2025-05-13"
SUBMIT_ACTION = "SubmitHunyuanTo3DProJob"
QUERY_ACTION = "QueryHunyuanTo3DProJob"
REGION = "ap-guangzhou"

OUTPUT_DIR = Path("E:/WorkSpaceForWorkbuddy/绘梨衣/downloads")


# --------------------------------------------------------------------------
# TC3-HMAC-SHA256 signing (from buddy-cloud.py)
# --------------------------------------------------------------------------

def _sha256_hex(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()

def _hmac_sha256(key: bytes, msg: bytes) -> bytes:
    return hmac.new(key, msg, hashlib.sha256).digest()

def _sign_headers(action: str, payload: str, host: str = "copilot.tencent.com",
                  timestamp: int = None) -> dict:
    """Build TC3-signed HTTP headers."""
    if timestamp is None:
        timestamp = int(time.time())
    
    secret_key = "TC3" + TOKEN
    
    date = datetime.datetime.fromtimestamp(
        timestamp, tz=datetime.timezone.utc
    ).strftime("%Y-%m-%d")
    
    # 1. Canonical request
    http_method = "POST"
    canonical_uri = "/"
    canonical_querystring = ""
    content_type = "application/json; charset=utf-8"
    signed_headers = "content-type;host;x-tc-action"
    canonical_headers = (
        f"content-type:{content_type}\n"
        f"host:{host}\n"
        f"x-tc-action:{action.lower()}\n"
    )
    hashed_payload = _sha256_hex(payload.encode("utf-8"))
    
    canonical_request = (
        f"{http_method}\n"
        f"{canonical_uri}\n"
        f"{canonical_querystring}\n"
        f"{canonical_headers}\n"
        f"{signed_headers}\n"
        f"{hashed_payload}"
    )
    
    # 2. String to sign
    algorithm = "TC3-HMAC-SHA256"
    credential_scope = f"{date}/{SERVICE}/tc3_request"
    hashed_canonical = _sha256_hex(canonical_request.encode("utf-8"))
    string_to_sign = (
        f"{algorithm}\n"
        f"{timestamp}\n"
        f"{credential_scope}\n"
        f"{hashed_canonical}"
    )
    
    # 3. Signing key
    secret_date = _hmac_sha256(
        ("TC3" + TOKEN).encode("utf-8"), date.encode("utf-8")
    )
    secret_service = _hmac_sha256(secret_date, SERVICE.encode("utf-8"))
    secret_signing = _hmac_sha256(secret_service, b"tc3_request")
    
    # 4. Signature
    signature = hmac.new(
        secret_signing, string_to_sign.encode("utf-8"), hashlib.sha256
    ).hexdigest()
    
    # 5. Authorization header
    authorization = (
        f"{algorithm} "
        f"Credential={SECRET_ID}/{credential_scope}, "
        f"SignedHeaders={signed_headers}, "
        f"Signature={signature}"
    )
    
    return {
        "Authorization": authorization,
        "Content-Type": content_type,
        "Host": host,
        "X-TC-Action": action,
        "X-TC-Version": VERSION,
        "X-TC-Region": REGION,
        "X-TC-Timestamp": str(timestamp),
    }


def _call_api(action: str, body: dict, timeout: int = 180) -> dict:
    """Call tcproxy with TC3-HMAC-SHA256 signing."""
    outer = {
        "Action": action,
        "Provider": PROVIDER,
        "Service": SERVICE,
        "Version": VERSION,
        "Region": REGION,
        "Body": body,
    }
    payload = json.dumps(outer)
    headers = _sign_headers(action, payload)
    
    resp = requests.post(ENDPOINT, headers=headers, data=payload.encode("utf-8"),
                         timeout=timeout)
    
    if resp.status_code != 200:
        print(f"  HTTP {resp.status_code}: {resp.text[:500]}")
        return {"Error": {"Code": str(resp.status_code), "Message": resp.text[:500]}}
    
    result = resp.json()
    if "Response" in result:
        inner = result["Response"]
        if "Error" in inner:
            return {"Error": inner["Error"]}
        return inner
    
    return result


# --------------------------------------------------------------------------
# Main workflow
# --------------------------------------------------------------------------

def submit_image_to_3d(image_path: str, model: str = "3.1",
                       face_count: int = 1200000, enable_pbr: bool = True):
    """Submit image-to-3D via tcproxy with TC3 signing."""
    
    image_path = Path(image_path)
    if not image_path.exists():
        print(f"ERROR: Image not found: {image_path}")
        return None
    
    print(f"[1/5] Encoding image: {image_path.name}")
    with open(image_path, "rb") as f:
        image_data = f.read()
    image_b64 = base64.b64encode(image_data).decode("utf-8")
    print(f"  Image: {len(image_data):,} bytes -> Base64: {len(image_b64):,} chars")
    
    body = {
        "Model": model,
        "ImageBase64": image_b64,
    }
    if enable_pbr:
        body["EnablePBR"] = True
    if face_count:
        body["FaceCount"] = face_count
    body["GenerateType"] = "Normal"
    body["ResultFormat"] = "FBX"
    
    print(f"[2/5] Submitting image-to-3D via tcproxy (TC3 signed)...")
    result = _call_api(SUBMIT_ACTION, body)
    
    if "Error" in result:
        print(f"  Submit Error: {result['Error'].get('Code')} - {result['Error'].get('Message', '')}")
        return None
    
    job_id = result.get("JobId")
    if not job_id:
        print(f"  No JobId. Response: {json.dumps(result, ensure_ascii=False)[:500]}")
        return None
    
    print(f"  Job ID: {job_id}")
    
    print(f"[3/5] Polling for completion...")
    max_polls = 72  # 6 minutes at 5s intervals
    for i in range(max_polls):
        time.sleep(5)
        poll_result = _call_api(QUERY_ACTION, {"JobId": job_id}, timeout=30)
        
        if "Error" in poll_result:
            print(f"  Poll {i+1} Error: {poll_result['Error']}")
            continue
        
        status = poll_result.get("Status", "UNKNOWN")
        
        if status == "DONE":
            print(f"  Poll {i+1}: DONE!")
            return poll_result
        elif status == "FAIL":
            print(f"  Poll {i+1}: FAILED")
            err = poll_result.get("ErrorMessage", poll_result.get("JobErrorMsg", ""))
            print(f"  Error message: {err}")
            return None
        else:
            if i % 3 == 0:
                elapsed = (i + 1) * 5
                print(f"  Poll {i+1}: {status} (elapsed: {elapsed}s)")
    
    print(f"  Timeout after {max_polls} polls")
    return None


def download_results(result_data: dict, prefix: str):
    """Download all result files."""
    if not result_data:
        return
    
    results = result_data.get("ResultFile3Ds", [])
    
    if not results:
        for key in ("ModelUrl", "ResultModelUrl", "ResultFileUrl"):
            url = result_data.get(key)
            if url:
                results = [{"Url": url, "Type": "FBX"}]
                break
    
    if not results:
        print(f"  No result files. Keys: {list(result_data.keys())}")
        print(f"  Response: {json.dumps(result_data, ensure_ascii=False)[:1000]}")
        return
    
    print(f"[4/5] Downloading {len(results)} result file(s)...")
    
    for i, item in enumerate(results):
        if isinstance(item, str):
            url, file_type = item, f"file_{i}"
        else:
            url = item.get("Url", item.get("ResultUrl", item.get("ModelUrl", "")))
            file_type = item.get("Type", f"file_{i}")
        
        if not url:
            continue
        
        # Determine extension
        ext = ""
        for e in [".zip", ".fbx", ".glb", ".obj", ".stl"]:
            if url.lower().endswith(e) or e.upper() in url:
                ext = e
                break
        if not ext:
            ext = f".{file_type.lower()}"
        
        filename = f"{prefix}_{file_type}{ext}"
        out_path = OUTPUT_DIR / filename
        
        print(f"  Downloading -> {out_path}")
        dl_resp = requests.get(url, timeout=300)
        if dl_resp.status_code == 200:
            with open(out_path, "wb") as f:
                f.write(dl_resp.content)
            print(f"  Saved: {len(dl_resp.content):,} bytes")
        else:
            print(f"  FAILED: HTTP {dl_resp.status_code}")
    
    print(f"[5/5] Done!")


if __name__ == "__main__":
    image_path = sys.argv[1] if len(sys.argv) > 1 else \
        "E:/WorkSpaceForWorkbuddy/绘梨衣/downloads/Anime_style_character_sheet_of_2026-06-14T17-34-41.png"
    prefix = sys.argv[2] if len(sys.argv) > 2 else "eriyi_image_to_3d"
    
    print("=" * 60)
    print("Image-to-3D Generation (TC3 signed via tcproxy)")
    print("=" * 60)
    
    result = submit_image_to_3d(image_path, model="3.1", face_count=1200000, enable_pbr=True)
    
    if result:
        download_results(result, prefix)
        print("\nSUCCESS!")
    else:
        print("\nFAILED: Image-to-3D generation did not complete successfully")
