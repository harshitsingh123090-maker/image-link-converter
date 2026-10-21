#!/usr/bin/env python3
"""
Image to Link Converter - Python standard library only. No pip installs needed.
Run: python3 server.py   (opens on http://localhost:8000)
"""
import os
import re
import json
import uuid
import base64
import mimetypes
import urllib.request
import urllib.error
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import unquote, urlparse, urlencode

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
UPLOAD_DIR = os.path.join(BASE_DIR, "uploads")
INDEX_FILE = os.path.join(BASE_DIR, "index.html")
ALLOWED_EXT = {".jpg", ".jpeg", ".png", ".webp", ".gif"}
MAX_UPLOAD_BYTES = 25 * 1024 * 1024  # 25 MB per request safety limit

# ImgBB permanent storage (used when IMGBB_API_KEY is set, e.g. on Render)
IMGBB_UPLOAD_URL = os.environ.get("IMGBB_UPLOAD_URL", "https://api.imgbb.com/1/upload")
IMGBB_TIMEOUT = 60  # seconds per image

os.makedirs(UPLOAD_DIR, exist_ok=True)


def imgbb_key():
    return (os.environ.get("IMGBB_API_KEY") or "").strip()


def upload_to_imgbb(data, original_name, key):
    """Upload bytes to ImgBB (permanent, no expiration). Returns (link, filename) or raises RuntimeError."""
    stem, _ext = sanitize_filename(original_name)
    payload = urlencode({
        "image": base64.b64encode(data).decode("ascii"),
        "name": stem,
    }).encode("ascii")
    url = IMGBB_UPLOAD_URL + ("&" if "?" in IMGBB_UPLOAD_URL else "?") + urlencode({"key": key})
    req = urllib.request.Request(
        url, data=payload, method="POST",
        headers={"Content-Type": "application/x-www-form-urlencoded",
                 "User-Agent": "ImageLinkConverter/1.0"},
    )
    try:
        with urllib.request.urlopen(req, timeout=IMGBB_TIMEOUT) as resp:
            raw = resp.read()
    except urllib.error.HTTPError as e:
        msg = f"HTTP {e.code}"
        try:
            err = json.loads(e.read().decode("utf-8", "ignore"))
            detail = (err.get("error") or {}).get("message") if isinstance(err.get("error"), dict) else err.get("error")
            if detail:
                msg += f": {detail}"
        except Exception:
            pass
        raise RuntimeError(f"ImgBB upload failed ({msg})")
    except urllib.error.URLError as e:
        raise RuntimeError(f"ImgBB upload failed (could not connect: {getattr(e, 'reason', e)})")
    except Exception as e:  # timeout etc.
        raise RuntimeError(f"ImgBB upload failed ({type(e).__name__})")
    try:
        result = json.loads(raw.decode("utf-8"))
        info = result["data"]
        link = info["url"]
    except Exception:
        raise RuntimeError("ImgBB upload failed (unexpected response)")
    if not link or not str(link).startswith("http"):
        raise RuntimeError("ImgBB upload failed (no link returned)")
    image_info = info.get("image") or {}
    filename = image_info.get("filename") or os.path.basename(urlparse(link).path) or f"{stem}{_ext}"
    return link, filename


def sanitize_filename(name):
    # Keep only the file name, remove unsafe characters
    name = os.path.basename(name or "image")
    name = unquote(name)
    # Split stem / extension
    stem, ext = os.path.splitext(name)
    ext = ext.lower()
    if ext not in ALLOWED_EXT:
        ext = ".png"
    stem = re.sub(r"[^A-Za-z0-9._-]+", "_", stem).strip("._-") or "image"
    stem = stem[:60]
    return stem, ext


def unique_filename(original):
    stem, ext = sanitize_filename(original)
    suffix = uuid.uuid4().hex[:8]
    return f"{stem}_{suffix}{ext}"


def parse_multipart(body, content_type):
    """Very small multipart/form-data parser (stdlib only). Returns list of (name, filename, data)."""
    m = re.search(r"boundary=([^;]+)", content_type)
    if not m:
        return []
    boundary = m.group(1).strip().strip('"')
    delimiter = b"--" + boundary.encode()
    parts = []
    for chunk in body.split(delimiter):
        if not chunk or chunk in (b"--", b"--\r\n", b"\r\n"):
            continue
        if chunk.startswith(b"\r\n"):
            chunk = chunk[2:]
        if chunk.endswith(b"\r\n"):
            chunk = chunk[:-2]
        if chunk.endswith(b"--"):
            chunk = chunk[:-2]
            if chunk.endswith(b"\r\n"):
                chunk = chunk[:-2]
        # Split headers / body
        if b"\r\n\r\n" not in chunk:
            continue
        header_blob, data = chunk.split(b"\r\n\r\n", 1)
        headers = header_blob.decode("utf-8", errors="ignore")
        name_match = re.search(r'name="([^"]*)"', headers)
        file_match = re.search(r'filename="([^"]*)"', headers)
        name = name_match.group(1) if name_match else ""
        filename = file_match.group(1) if file_match else None
        parts.append((name, filename, data))
    return parts


class Handler(BaseHTTPRequestHandler):
    server_version = "ImageLinkConverter/1.0"

    def log_message(self, fmt, *args):
        print(f"{self.address_string()} - {fmt % args}")

    def base_url(self):
        proto = self.headers.get("X-Forwarded-Proto", "http").split(",")[0].strip() or "http"
        host = self.headers.get("X-Forwarded-Host") or self.headers.get("Host") or "localhost:8000"
        host = host.split(",")[0].strip()
        return f"{proto}://{host}"

    def send_json(self, obj, status=200):
        data = json.dumps(obj).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def do_GET(self):
        parsed = urlparse(self.path)
        path = unquote(parsed.path)

        if path == "/" or path == "/index.html":
            try:
                with open(INDEX_FILE, "rb") as f:
                    data = f.read()
            except FileNotFoundError:
                self.send_error(404, "index.html not found")
                return
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Length", str(len(data)))
            self.end_headers()
            self.wfile.write(data)
            return

        if path == "/api/images":
            files = []
            base = self.base_url()
            if os.path.isdir(UPLOAD_DIR):
                entries = []
                for name in os.listdir(UPLOAD_DIR):
                    if name.startswith("."):
                        continue
                    full = os.path.join(UPLOAD_DIR, name)
                    if os.path.isfile(full) and os.path.splitext(name)[1].lower() in ALLOWED_EXT:
                        entries.append((os.path.getmtime(full), name, os.path.getsize(full)))
                entries.sort(reverse=True)
                for _, name, size in entries:
                    files.append({
                        "filename": name,
                        "link": f"{base}/images/{name}",
                        "size": size,
                    })
            self.send_json({"files": files, "links": [f["link"] for f in files]})
            return

        if path.startswith("/images/"):
            filename = os.path.basename(path[len("/images/"):])
            # Prevent path traversal
            if not filename or "/" in filename or "\\" in filename:
                self.send_error(404, "Not found")
                return
            full = os.path.join(UPLOAD_DIR, filename)
            if not os.path.isfile(full):
                self.send_error(404, "Image not found")
                return
            ctype, _ = mimetypes.guess_type(full)
            if not ctype:
                ctype = "application/octet-stream"
            with open(full, "rb") as f:
                data = f.read()
            self.send_response(200)
            self.send_header("Content-Type", ctype)
            self.send_header("Content-Length", str(len(data)))
            self.send_header("Cache-Control", "public, max-age=86400")
            self.send_header("Access-Control-Allow-Origin", "*")
            self.end_headers()
            self.wfile.write(data)
            return

        self.send_error(404, "Not found")

    def do_POST(self):
        parsed = urlparse(self.path)
        if parsed.path != "/upload":
            self.send_error(404, "Not found")
            return

        content_type = self.headers.get("Content-Type", "")
        if "multipart/form-data" not in content_type:
            self.send_json({"error": "Expected multipart/form-data upload"}, status=400)
            return

        try:
            length = int(self.headers.get("Content-Length", 0))
        except ValueError:
            length = 0
        if length <= 0:
            self.send_json({"error": "No file received"}, status=400)
            return
        if length > MAX_UPLOAD_BYTES * 5:
            self.send_json({"error": "Upload too large"}, status=413)
            return

        body = self.rfile.read(length)
        parts = parse_multipart(body, content_type)
        saved = []
        errors = []
        base = self.base_url()
        key = imgbb_key()

        for _name, filename, data in parts:
            if not filename:
                continue
            if not data:
                continue
            ext = os.path.splitext(filename)[1].lower()
            if ext not in ALLOWED_EXT:
                continue
            original = os.path.basename(filename)
            if len(data) > MAX_UPLOAD_BYTES:
                errors.append({"original_name": original, "error": "File too large (max 25 MB)"})
                continue
            if key:
                try:
                    link, new_name = upload_to_imgbb(data, filename, key)
                except RuntimeError as e:
                    print(f"Upload error for {original}: {e}")
                    errors.append({"original_name": original, "error": str(e)})
                    continue
            else:
                new_name = unique_filename(filename)
                full = os.path.join(UPLOAD_DIR, new_name)
                with open(full, "wb") as out:
                    out.write(data)
                link = f"{base}/images/{new_name}"
            saved.append({
                "filename": new_name,
                "original_name": original,
                "link": link,
                "size": len(data),
            })

        if not saved:
            if errors:
                msg = "; ".join(f"{e['original_name']}: {e['error']}" for e in errors)
                self.send_json({"error": msg, "errors": errors}, status=502)
            else:
                self.send_json({"error": "No valid image found. Please upload JPG, PNG, WEBP or GIF."}, status=400)
            return

        if errors:
            self.send_json({"files": saved, "links": [f["link"] for f in saved], "errors": errors})
            return

        self.send_json({"files": saved, "links": [f["link"] for f in saved]})


if __name__ == "__main__":
    port = int(os.environ.get("PORT", "8000"))
    server = ThreadingHTTPServer(("0.0.0.0", port), Handler)
    print(f"Image to Link Converter running at http://localhost:{port}")
    print("Storage: ImgBB (permanent links)" if imgbb_key() else "Storage: local uploads/ folder (set IMGBB_API_KEY for permanent ImgBB links)")
    print("Press Ctrl+C to stop.")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nStopped.")
