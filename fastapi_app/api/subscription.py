import base64
from fastapi import APIRouter, Depends, HTTPException, Response, Query
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Literal

from database.session import get_db_session
from database.models import Subscription
from database.crud.crud_subscription import get_subscription_with_configs_by_service_name
from fastapi_app.services.generator_subscriptions import generate_yaml_for_hiddify
from core.config import settings

router = APIRouter()


@router.get("/{sub_name}")
async def get_subscription(
        sub_name: str,
        session: AsyncSession = Depends(get_db_session),
        # Параметр для выбора формата. По умолчанию 'hiddify'
        client: Literal['hiddify', 'happ'] = Query('hiddify')
):
    subscription: Subscription = await get_subscription_with_configs_by_service_name(session, sub_name)
    if not subscription or not subscription.is_active:
        raise HTTPException(status_code=404, detail="Subscription not found")

    configs_list = [conf.config_data for conf in subscription.configs]
    if not configs_list:
        raise HTTPException(status_code=404, detail="No active configs found")

    # --- ГОТОВИМ МЕТАДАННЫЕ В ЗАГОЛОВКАХ (ОНИ ОБЩИЕ ДЛЯ ОБОИХ КЛИЕНТОВ) ---
    profile_title_raw = f"🚀 {settings.LOGO_NAME}"
    profile_title_b64 = base64.b64encode(profile_title_raw.encode('utf-8')).decode('utf-8')

    headers = {
        'profile-title': f"base64:{profile_title_b64}",
        'subscription-userinfo': f'upload=0; download=0; total=109951162777600; expire={int(subscription.end_date.timestamp())}',
        'support-url': settings.SUPPORT_URL,
        'profile-update-interval': '24'
    }

    # --- ВЫБИРАЕМ ТЕЛО ОТВЕТА В ЗАВИСИМОСТИ ОТ КЛИЕНТА ---

    if client == 'happ':
        # Для Happ отдаем ПРОСТОЙ СПИСОК VLESS-ССЫЛОК, как указано в их документации
        content_body = "\n".join(configs_list)
        media_type = "text/plain; charset=utf-8"
    else:  # client == 'hiddify'
        # Для Hiddify отдаем ПОЛНОФУНКЦИОНАЛЬНЫЙ YAML
        content_body = generate_yaml_for_hiddify(configs_list, settings.LOGO_NAME)
        media_type = "text/yaml; charset=utf-8"

    return Response(
        content=content_body,
        media_type=media_type,
        headers=headers
    )