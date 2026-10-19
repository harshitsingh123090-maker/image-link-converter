# Image to Link Converter (for Amazon & Flipkart Bulk Sheets)

Upload product images → get a direct link for each image → paste the links into your Amazon / Flipkart bulk upload sheet.

## Files in this project
- `index.html` — the website page (what you see in the browser)
- `server.py` — the small server program (Python only, nothing to install)
- `uploads/` — uploaded images are saved here

## How to run on your own computer

1. Make sure Python 3 is installed. Check in Terminal / Command Prompt:
   ```
   python3 --version
   ```
   (On Windows it may be `python --version`. Download Python free from python.org if needed.)
2. Open Terminal / Command Prompt in this folder.
3. Run:
   ```
   python3 server.py
   ```
4. Open your browser and go to: **http://localhost:8000**
5. Drag & drop your images, copy the links, or click **Download CSV**.

To stop the server, press `Ctrl + C`.

You can change the port like this: `PORT=9000 python3 server.py`

## ⚠️ IMPORTANT — Read this before using links in Amazon / Flipkart

If you run this only on your own computer, links will start with `http://localhost:8000/...`

**Amazon and Flipkart CANNOT open localhost links.** Localhost means "only this computer".
Their computers are far away, so the image will fail in your bulk sheet.

**To get real public links (starting with `https://`), this website must be put on a public host on the internet.**
After that one-time setup, you just open your public website, upload images, and copy the `https://...` links into your sheet. Those links will work in Amazon / Flipkart.

## Free / easy ways to put it on the internet

### Option A — Render.com (free, recommended, simple steps)
1. Put this project folder in a GitHub account (github.com → New repository → upload these files: `index.html`, `server.py`, and keep the `uploads` folder). Or zip this folder and use a host that accepts it.
2. Go to **render.com** and create a free account.
3. Click **New + → Web Service**, connect your GitHub repository.
4. Settings:
   - **Runtime / Environment:** Python 3
   - **Build Command:** (leave blank / `echo ok` — nothing to install)
   - **Start Command:** `python3 server.py`
5. Click **Create Web Service**. Wait 2–5 minutes.
6. Render will give you a public address like `https://image-link-converter.onrender.com`
7. Open that address, upload images, copy the `https://...` links — paste them in your Amazon / Flipkart sheet.

Note: On free plans, images/files can be deleted when the service restarts. For permanent image storage for a large catalogue, use a paid disk on Render, or a VPS, or an image host — see "Good to know" below.

### Option B — Railway / PythonAnywhere / any VPS
- **Railway (railway.app):** New Project → Deploy from GitHub → Start command: `python3 server.py`
- **PythonAnywhere (pythonanywhere.com):** Free account → Web tab → create a web app, or run the server in a console and use their hosting options. A small custom setup is needed for a raw `http.server` app, so Render/Railway is easier.
- **Any VPS (your own server):** Copy this folder to the server, run `PORT=8000 python3 server.py`, and point a domain + HTTPS (for example with Nginx / Caddy) to it.

After deployment on any host, the website automatically uses that host's address in the links (it reads the Host header), so no code change is needed.

## How to use the website
1. Drag & drop images (or click **Choose Images**). JPG, JPEG, PNG, WEBP and GIF are accepted.
2. Each image gets its own link with a **Copy** button.
3. **Copy All Links** — copies every link, one per line.
4. **Download CSV** — downloads `image-links.csv` with columns `Filename, Image Link`, ready to open in Excel and paste into a bulk sheet.
5. The plain list box also shows one link per line for quick copy-paste into Excel.
6. **Remove** deletes one row from the list, **Clear All** empties the list.

## Good to know / limitations
- This is a simple, free tool. There is no login/password — anyone who knows your public website address can upload. Do not share the address publicly if that matters to you.
- Free hosting usually sleeps or restarts, and files in `uploads/` may not be permanent there. If you need links that must stay alive for months, use paid hosting with a persistent disk, or upload images to a dedicated image/CDN storage and use those links.
- Amazon/Flipkart may also have their own image rules (white background, minimum size like 1000px, etc.) — this tool only creates the link, it does not edit the photo.

## Zip of this project
A ready zip is at `/workspace/image-link-converter.zip` (on the computer where this was built) — you can send that zip to a developer or upload it to your host.
