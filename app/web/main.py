from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from fastapi.templating import Jinja2Templates

from app.web.database import get_dashboard_summary, get_incident_detail


BASE_DIR = Path(__file__).resolve().parents[2]

templates = Jinja2Templates(
    directory=str(BASE_DIR / "app" / "templates")
)

app = FastAPI(
    title="YERİNDE SOC AI",
    version="1.0.0",
)


@app.get("/")
def dashboard(request: Request):
    data = get_dashboard_summary()

    return templates.TemplateResponse(
        request=request,
        name="dashboard.html",
        context=data,
    )


@app.get("/api/dashboard")
def dashboard_api():
    return JSONResponse(
        content=get_dashboard_summary()
    )


@app.get("/incidents/{incident_id}")
def incident_detail(request: Request, incident_id: int):
    data = get_incident_detail(incident_id)

    if data is None:
        return JSONResponse(
            status_code=404,
            content={"detail": "Incident bulunamadı"}
        )

    return templates.TemplateResponse(
        request=request,
        name="incident_detail.html",
        context=data,
    )
