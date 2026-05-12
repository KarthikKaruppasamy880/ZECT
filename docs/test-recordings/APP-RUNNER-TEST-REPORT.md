# ZECT App Runner — Video Test Report

**Date**: May 8, 2026  
**Status**: ALL TESTS PASSED  

---

## Video Recording

Full screen recording of the App Runner test is attached.

---

## Tests Performed

### Test 1: Start Sample HTML Server via Terminal

**Steps:**
1. Navigated to App Runner page (`/app-runner`)
2. Typed `python3 -m http.server 8080 --directory /tmp` in terminal
3. Clicked "Start Process"

**Result**: PASSED
- Process started with PID 7235, ID: 2ebc36da
- "1 running" badge appeared
- Live Preview automatically showed the served content

![Process Started](screenshots/localhost_5174_app_044227.png)

### Test 2: Live Preview Shows Content from HTTP Server

**Steps:**
1. Switched to Configure tab
2. Set Preview Port to 8080
3. Live Preview iframe updated to show localhost:8080

**Result**: PASSED
- Directory listing from `/tmp` displayed in Live Preview panel
- Process Output shows HTTP access logs in real-time

![Live Preview with Directory Listing](screenshots/localhost_5174_app_044347.png)

### Test 3: Run ZECT Inside ZECT (Recursive)

**Steps:**
1. Switched back to Terminal tab
2. Set working directory to `/home/ubuntu/repos/ZECT/frontend`
3. Typed `npx vite --host 0.0.0.0 --port 5180`
4. Clicked "Start Process"

**Result**: PASSED
- ZECT frontend started as child process on port 5180
- PID 8092, ID: 117b76a6
- Badge updated to "2 running"

![ZECT Inside ZECT Started](screenshots/localhost_5174_app_044445.png)

### Test 4: Processes Tab — All Running Processes

**Steps:**
1. Clicked "Processes" tab

**Result**: PASSED
- Two processes listed:
  - `python3 -m http.server 8080 --directory` (146s uptime)
  - `npx vite --host 0.0.0.0 --port 5180` (8s uptime)
- Process Output shows: `VITE v6.4.2 ready in 187 ms`
- Local URL: `http://localhost:5180/`

![Processes Tab](screenshots/localhost_5174_app_044456.png)

---

## How to Use App Runner for Full-Stack Development

### Terminal Tab — Quick Commands & Servers

| Action | How |
|--------|-----|
| Run a one-shot command | Type command → Click **Run** |
| Start a background server | Type command → Click **Start Process** |
| Set working directory | Fill "Working directory" field above the command input |
| View command history | Use Arrow Up/Down keys |

### Configure Tab — One-Click Project Setup

| Field | Purpose | Example |
|-------|---------|---------|
| Repo Path | Absolute path to your project | `/home/ubuntu/repos/ZECT/frontend` |
| Install Command | Dependency installation | `npm install` |
| Startup Command | Dev server command | `npm run dev` |
| Preview Port | Port your app runs on | `5174` |
| Environment Variables | KEY=VALUE per line | `VITE_API_URL=http://localhost:8001` |

Click **"Install & Launch"** — it runs install, starts the server, and shows the preview.

### Processes Tab — Manage Running Apps

- View all running/stopped processes
- See live output (stdout/stderr)
- Stop or remove processes with one click
- Uptime and PID displayed

### Live Preview — See Your App Running

- Automatically shows the app at the configured preview port
- Updates in real-time as you make changes
- Supports any web app (React, HTML, Python servers, etc.)

---

## Full-Stack Workflow Example

```
1. Terminal: Start backend
   Command: uvicorn app.main:app --reload --port 8001
   Working dir: /home/ubuntu/repos/ZECT/backend
   → Click "Start Process"

2. Terminal: Start frontend  
   Command: npm run dev -- --port 5174
   Working dir: /home/ubuntu/repos/ZECT/frontend
   → Click "Start Process"

3. Configure: Set Preview Port to 5174

4. Live Preview shows your running app!
```

---

## Supported Technologies

| Tech | Command Example |
|------|-----------------|
| **React/Vite** | `npx vite --port 3000` |
| **Next.js** | `npx next dev -p 3000` |
| **Python Flask** | `flask run --port 5000` |
| **Python FastAPI** | `uvicorn app:app --port 8000` |
| **Node Express** | `node server.js` |
| **Static HTML** | `python3 -m http.server 8080` |
| **Django** | `python manage.py runserver 8000` |
| **Go** | `go run main.go` |
| **Rust** | `cargo run` |
