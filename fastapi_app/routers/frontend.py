from fastapi import APIRouter, Request, Depends, HTTPException
from fastapi.templating import Jinja2Templates
from sqlalchemy.ext.asyncio import AsyncSession
from database.crud.crud_subscription import get_subscription_with_configs_by_service_name
from database.session import get_db_session
from core.config import settings # Импортируем настройки для домена

templates = Jinja2Templates(directory="templates")
router = APIRouter(
    tags=["Frontend"]
)

@router.get("/page/{sub_name}")
async def get_subscription_page(
    request: Request,
    sub_name: str,
    session: AsyncSession = Depends(get_db_session)
):
    subscription = await get_subscription_with_configs_by_service_name(session, sub_name)
    if not subscription:
        raise HTTPException(status_code=404, detail="Подписка не найдена")

    return templates.TemplateResponse("index.html", {
        "request": request,
        "subscription_name": sub_name,
        "domain": settings.DOMAIN_API # Передаем домен в шаблон
    })