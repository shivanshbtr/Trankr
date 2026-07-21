"""
run.py — Trankr Launcher
========================
Run this file to start everything:

    python run.py

What it does:
1. Installs dependencies automatically (first run only)
2. Starts FastAPI backend in a background thread
3. Waits until the server is ready
4. Opens http://localhost:8000 in your default browser
5. Shows live status in the terminal
6. Ctrl+C to shut everything down cleanly
"""

import sys
import os
import subprocess
import threading
import time
import webbrowser
import urllib.request
import urllib.error

# ── Config ────────────────────────────────────────────────────────────────────
PORT        = 8000
HOST        = "127.0.0.1"
URL         = f"http://{HOST}:{PORT}"
BACKEND_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "backend")
DB_PATH     = os.path.join(BACKEND_DIR, "trankr.db")

# ── Colors (work on Mac/Linux/Windows 10+) ────────────────────────────────────
GREEN  = "\033[92m"
YELLOW = "\033[93m"
RED    = "\033[91m"
CYAN   = "\033[96m"
BOLD   = "\033[1m"
DIM    = "\033[2m"
RESET  = "\033[0m"

def c(color, text):
    """Wrap text in color codes."""
    return f"{color}{text}{RESET}"


# ── Step 1: Auto-install dependencies ────────────────────────────────────────

def install_deps():
    req_file = os.path.join(BACKEND_DIR, "requirements.txt")
    marker   = os.path.join(BACKEND_DIR, ".deps_installed")

    # Only install if requirements changed or first run
    if os.path.exists(marker):
        req_mtime    = os.path.getmtime(req_file)
        marker_mtime = os.path.getmtime(marker)
        if marker_mtime >= req_mtime:
            return  # already up to date

    print(c(YELLOW, "📦 Installing dependencies (first run — takes ~30s)..."))
    result = subprocess.run(
        [sys.executable, "-m", "pip", "install", "-r", req_file, "-q"],
        capture_output=True, text=True
    )
    if result.returncode != 0:
        print(c(RED, "❌ Dependency install failed:"))
        print(result.stderr)
        sys.exit(1)

    # Write marker file
    open(marker, "w").close()
    print(c(GREEN, "✅ Dependencies ready"))


# ── Step 2: Start FastAPI in background thread ────────────────────────────────

server_process = None

def start_server():
    """Launch uvicorn as a subprocess so we can kill it cleanly on exit."""
    global server_process
    server_process = subprocess.Popen(
        [
            sys.executable, "-m", "uvicorn",
            "main:app",
            "--host", HOST,
            "--port", str(PORT),
            "--log-level", "warning",   # suppress INFO spam in terminal
        ],
        cwd    = BACKEND_DIR,
        stdout = subprocess.DEVNULL,
        stderr = subprocess.PIPE,
    )

    # Stream any errors to terminal
    def stream_errors():
        for line in server_process.stderr:
            decoded = line.decode("utf-8", errors="replace").strip()
            if decoded:
                print(c(RED, f"  [server] {decoded}"))

    threading.Thread(target=stream_errors, daemon=True).start()


# ── Step 3: Wait until server responds ───────────────────────────────────────

def wait_for_server(timeout=20):
    """Poll /health until the server is up, or time out."""
    start = time.time()
    while time.time() - start < timeout:
        try:
            urllib.request.urlopen(f"{URL}/health", timeout=1)
            return True
        except Exception:
            time.sleep(0.3)
    return False


# ── Step 4: DB info helper ────────────────────────────────────────────────────

def db_info():
    """Return human-readable info about the database file."""
    if not os.path.exists(DB_PATH):
        return "  📁 Database: not created yet (will be created on first login)"

    size_bytes = os.path.getsize(DB_PATH)

    if size_bytes < 1024:
        size_str = f"{size_bytes} B"
    elif size_bytes < 1024 * 1024:
        size_str = f"{size_bytes / 1024:.1f} KB"
    else:
        size_str = f"{size_bytes / (1024*1024):.2f} MB"

    # Try to read row counts if sqlite3 is available
    row_info = ""
    try:
        import sqlite3
        conn = sqlite3.connect(DB_PATH)
        cur  = conn.cursor()
        tables = ["users", "goals", "milestones", "tasks", "habits", "habit_logs", "journals", "targets"]
        counts = {}
        for t in tables:
            try:
                cur.execute(f"SELECT COUNT(*) FROM {t}")
                counts[t] = cur.fetchone()[0]
            except Exception:
                pass
        conn.close()
        if counts:
            relevant = {k: v for k, v in counts.items() if v > 0}
            if relevant:
                parts = ", ".join(f"{v} {k}" for k, v in relevant.items())
                row_info = f"\n  📊 Contents : {parts}"
    except Exception:
        pass

    return (
        f"  📁 Location : {c(CYAN, DB_PATH)}\n"
        f"  💾 File size: {c(GREEN, size_str)}  "
        f"{c(DIM, '(SQLite — single file, zero config)')}"
        + row_info
    )


# ── Step 5: Storage capacity info ─────────────────────────────────────────────

def storage_info():
    """Show how much disk space is available for the DB."""
    try:
        stat = os.statvfs(BACKEND_DIR) if hasattr(os, "statvfs") else None
        if stat:
            free_gb  = (stat.f_bavail * stat.f_frsize) / (1024**3)
            total_gb = (stat.f_blocks * stat.f_frsize) / (1024**3)
            return f"  💿 Disk free : {c(GREEN, f'{free_gb:.1f} GB')} of {total_gb:.0f} GB total"
    except Exception:
        pass
    return ""


# ── Main ──────────────────────────────────────────────────────────────────────

def main():
    # Enable ANSI colors on Windows
    if sys.platform == "win32":
        os.system("color")

    print()
    print(c(BOLD, "  ✦  Trankr — Goal & Progress Tracker"))
    print(c(DIM,  "  ─────────────────────────────────────"))
    print()

    # Install deps
    install_deps()

    # Start server
    print(c(YELLOW, "🚀 Starting server..."))
    start_server()

    # Wait for it to be ready
    ready = wait_for_server(timeout=20)
    if not ready:
        print(c(RED, "❌ Server didn't start in time. Check errors above."))
        if server_process:
            server_process.terminate()
        sys.exit(1)

    # Print status dashboard
    print()
    print(c(GREEN,  "✅ Trankr is running!"))
    print()
    print(c(BOLD,   "  🌐 App URL"))
    print(f"  {c(CYAN, URL)}  ← opening in your browser now")
    print()
    print(c(BOLD,   "  🗄  Database"))
    print(db_info())
    extra = storage_info()
    if extra:
        print(extra)
    print()
    print(c(BOLD,   "  ℹ️  Storage facts"))
    print(c(DIM,    "  SQLite stores everything in one file: backend/trankr.db"))
    print(c(DIM,    "  Typical usage: ~1 MB per year of daily data"))
    print(c(DIM,    "  Practical limit: ~281 TB (you will never hit it)"))
    print()
    print(c(DIM,    "  Press Ctrl+C to stop Trankr"))
    print()

    # Open browser
    time.sleep(0.5)
    webbrowser.open(URL)

    # Keep running until Ctrl+C
    try:
        while True:
            # Check if server is still alive every 5s
            if server_process and server_process.poll() is not None:
                print(c(RED, "\n⚠️  Server stopped unexpectedly. Exiting."))
                break
            time.sleep(5)
    except KeyboardInterrupt:
        print()
        print(c(YELLOW, "👋 Shutting down Trankr..."))
        if server_process:
            server_process.terminate()
            try:
                server_process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                server_process.kill()
        print(c(GREEN, "✅ Stopped cleanly. See you tomorrow!"))
        print()


if __name__ == "__main__":
    main()
