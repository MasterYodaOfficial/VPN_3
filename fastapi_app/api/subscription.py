from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from database.session import get_db_session
from database.models import Subscription
from fastapi_app.schemas import ConfigResponse
from database.crud.crud_subscription import get_subscription_with_configs_by_service_name
from fastapi_app.services.generator_subscriptions import generate_vpn_yaml
router = APIRouter()

@router.get("/{sub_name}", response_model=ConfigResponse)
async def get_subscription_config(
    sub_name: str,
    session: AsyncSession = Depends(get_db_session),
):
    subscription: Subscription = await get_subscription_with_configs_by_service_name(session, sub_name)
    if not subscription:
        raise HTTPException(status_code=404, detail="Not found")

    configs = [conf.config_data for conf in subscription.configs]
    if not configs:
        raise HTTPException(status_code=404, detail="No active config found")
    yaml_config = generate_vpn_yaml(configs)
    return ConfigResponse(config=yaml_config)
