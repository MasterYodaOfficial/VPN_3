from fastapi import APIRouter
from app.core.limiter import limiter
from fastapi import Request
from fastapi.templating import Jinja2Templates
from app.core.config import settings


head_router = APIRouter()
templates = Jinja2Templates(directory=settings.TEMPLATES_PATHS)

@head_router.get("/")
@limiter.limit("20/minute")
async def index(request: Request):
    context = {"request": request, "page_title": "Welcome to QuickLab"}
    return templates.TemplateResponse("head_app.html", context)
