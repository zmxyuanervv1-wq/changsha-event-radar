from contextlib import asynccontextmanager
from datetime import date
from fastapi import FastAPI, Query
from fastapi.responses import FileResponse
from pathlib import Path
from fastapi.middleware.cors import CORSMiddleware
from apscheduler.schedulers.background import BackgroundScheduler
from .database import init_db, connect
from .collector import collect_all
import os
from zoneinfo import ZoneInfo

scheduler = BackgroundScheduler(timezone=ZoneInfo(os.getenv("TZ", "Asia/Shanghai")))

@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    if not scheduler.running:
        scheduler.add_job(collect_all, "cron",
            hour=int(os.getenv("COLLECT_HOUR", "8")),
            minute=int(os.getenv("COLLECT_MINUTE", "0")),
            id="daily_collection", replace_existing=True, max_instances=1)
        scheduler.start()
    yield
    if scheduler.running:
        scheduler.shutdown(wait=False)

app = FastAPI(title="长沙活动雷达 API", version="1.0.0", lifespan=lifespan)
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

@app.get("/")
def homepage():
    return FileResponse(Path(__file__).resolve().parent.parent / "index.html")

@app.get("/api/health")
def health():
    return {"ok": True, "service": "changsha-event-radar"}

@app.get("/api/events")
def list_events(category: str = "", q: str = "", upcoming: bool = True, limit: int = Query(100, ge=1, le=300)):
    sql = "SELECT * FROM events WHERE 1=1"
    params = []
    if category and category != "全部":
        if category == "免费":
            sql += " AND (price LIKE '%免费%' OR price LIKE '%免门票%')"
        else:
            sql += " AND category=?"
            params.append(category)
    if q:
        sql += " AND (title LIKE ? OR venue LIKE ? OR description LIKE ?)"
        params += [f"%{q}%"] * 3
    if upcoming:
        sql += " AND (start_date='' OR start_date>=?)"
        params.append(date.today().isoformat())
    sql += " ORDER BY CASE WHEN start_date='' THEN 1 ELSE 0 END, start_date LIMIT ?"
    params.append(limit)
    with connect() as db:
        rows = [dict(r) for r in db.execute(sql, params).fetchall()]
    return {"items": rows, "count": len(rows)}

@app.get("/api/events/{event_id}")
def event_detail(event_id: int):
    with connect() as db:
        row = db.execute("SELECT * FROM events WHERE id=?", (event_id,)).fetchone()
    return dict(row) if row else {"error": "not_found"}

@app.get("/api/logs")
def logs(limit: int = 30):
    with connect() as db:
        rows = [dict(r) for r in db.execute(
            "SELECT * FROM collection_logs ORDER BY id DESC LIMIT ?", (limit,)).fetchall()]
    return {"items": rows}

@app.post("/api/collect")
def run_collection():
    # Manual trigger for the owner; schedule also runs daily at 08:00 Asia/Shanghai.
    return {"results": collect_all()}

@app.patch("/api/events/{event_id}/verification")
def verify_event(event_id: int, status: str = Query(..., pattern="^(待核实|来源已发布|官方已确认)$")):
    with connect() as db:
        db.execute("UPDATE events SET verification=?, updated_at=CURRENT_TIMESTAMP WHERE id=?",
                   (status, event_id))
        db.commit()
        row = db.execute("SELECT * FROM events WHERE id=?", (event_id,)).fetchone()
    return dict(row) if row else {"error": "not_found"}
