from fastapi import APIRouter, Request, Header, Response, HTTPException
from typing import Optional
from app.services.webhook_remna_validator import webhook_validator
from app.services.webhook_remna_service import webhook_service
from app.logger import logger


remna_webhook_router = APIRouter(prefix="/remnawave")


@remna_webhook_router.post("/webhook")
async def handle_remnawave_webhook(
        request: Request,
        x_remnawave_signature: Optional[str] = Header(None)
):
    """
    Принимает, валидирует и обрабатывает вебхуки от панели Remnawave.
    """
    if not x_remnawave_signature:
        logger.warning("Получен вебхук без заголовка подписи. Отклонено.")
        raise HTTPException(status_code=403, detail="Signature header is missing")

    # Получаем тело запроса как байты для корректной валидации
    body_bytes = await request.body()

    if not webhook_validator.validate_signature(body_bytes, x_remnawave_signature):
        logger.error("Получен вебхук с НЕВАЛИДНОЙ подписью. Отклонено.")
        raise HTTPException(status_code=403, detail="Invalid signature")

    try:
        payload = await request.json()
        await webhook_service.process_webhook(payload)
        return Response(status_code=200)
    except Exception as e:
        logger.critical(f"Критическая ошибка при обработке вебхука Remnawave: {e}")
        return Response(status_code=500)