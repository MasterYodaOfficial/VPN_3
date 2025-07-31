import base64
from fastapi import APIRouter, Depends, HTTPException, Response, Request
from sqlalchemy.ext.asyncio import AsyncSession

from database.session import get_db_session
from database.models import Subscription
from database.crud.crud_subscription import get_subscription_with_configs_by_access_key
from fastapi_app.services.generator_subscriptions import generate_vless_list_for_happ
from core.config import settings
from fastapi_app.core.limiter import limiter




router = APIRouter()


@router.get("/{access_key}")
@limiter.limit("10/minute")
async def get_happ_compatible_subscription(
        access_key: str,
        request: Request,
        session: AsyncSession = Depends(get_db_session)
):
    """
    Отдает универсальную подписку, максимально совместимую с Happ.
    Метаданные передаются в заголовках, а тело - простой список VLESS-ссылок.
    """
    subscription: Subscription = await get_subscription_with_configs_by_access_key(session, access_key)
    if not subscription or not subscription.is_active:
        raise HTTPException(status_code=404, detail="Stop do that please =)")

    configs_list = [conf.config_data for conf in subscription.configs]
    if not configs_list:
        raise HTTPException(status_code=404, detail="No active configs found")

    # --- ГОТОВИМ МЕТАДАННЫЕ В ЗАГОЛОВКАХ (КАК ТРЕБУЕТ ДОКУМЕНТАЦИЯ) ---
    profile_title_raw = f"🚀 {settings.LOGO_NAME}"
    profile_title_b64 = base64.b64encode(profile_title_raw.encode('utf-8')).decode('utf-8')

    headers = {
        'profile-title': f"base64:{profile_title_b64}",
        'subscription-userinfo': f'upload=0; download=0; total=109951162777600; expire={int(subscription.end_date.timestamp())}',
        'support-url': settings.SUPPORT_URL,
        'profile-update-interval': '12'
    }

    # --- ГОТОВИМ ТЕЛО ОТВЕТА (ПРОСТОЙ СПИСОК ССЫЛОК) ---
    content_body = generate_vless_list_for_happ(configs_list)

    return Response(
        content=content_body,
        media_type="text/plain; charset=utf-8",
        headers=headers
    )