
from contextlib import asynccontextmanager
from datetime import date
from fastapi import FastAPI, Query, Header, HTTPException
from fastapi.responses import FileResponse
from pathlib import Path
from fastapi.middleware.cors import CORSMiddleware
from .database import init_db, connect
from .collector import collect_all
import os

@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    yield

app = FastAPI(title="长沙活动雷达 API", version="1.1.0", lifespan=lifespan)
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
            sql += " AND (price LIKE %s OR price LIKE %s)"
            params += ["%免费%", "%免门票%"]
        else:
            sql += " AND category=%s"
            params.append(category)
    if q:
        sql += " AND (title LIKE %s OR venue LIKE %s OR description LIKE %s)"
        params += [f"%{q}%"] * 3
    if upcoming:
        sql += " AND (start_date='' OR start_date>=%s)"
        params.append(date.today().isoformat())
    sql += " ORDER BY CASE WHEN start_date='' THEN 1 ELSE 0 END, start_date LIMIT %s"
    params.append(limit)
    with connect() as db:
        rows = [dict(r) for r in db.execute(sql, params).fetchall()]
    return {"items": rows, "count": len(rows)}

@app.get("/api/events/{event_id}")
def event_detail(event_id: int):
    with connect() as db:
        row = db.execute("SELECT * FROM events WHERE id=%s", (event_id,)).fetchone()
    return dict(row) if row else {"error": "not_found"}

@app.get("/api/logs")
def logs(limit: int = Query(30, ge=1, le=200)):
    with connect() as db:
        rows = [dict(r) for r in db.execute(
            "SELECT * FROM collection_logs ORDER BY id DESC LIMIT %s", (limit,)).fetchall()]
    return {"items": rows}

@app.post("/api/collect")
def run_collection(x_collect_secret: str = Header(default="")):
    secret = os.getenv("COLLECT_SECRET", "")
    if not secret or x_collect_secret != secret:
        raise HTTPException(status_code=403, detail="Forbidden")
    return {"results": collect_all()}

@app.patch("/api/events/{event_id}/verification")
def verify_event(event_id: int, status: str = Query(..., pattern="^(待核实|来源已发布|官方已确认)$")):
    with connect() as db:
        db.execute("UPDATE events SET verification=%s, updated_at=CURRENT_TIMESTAMP WHERE id=%s",
                   (status, event_id))
        row = db.execute("SELECT * FROM events WHERE id=%s", (event_id,)).fetchone()
        db.commit()
    return dict(row) if row else {"error": "not_found"}
