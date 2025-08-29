import hmac
import hashlib
import json
from typing import Union, Dict, Any

from app.core.config import settings


class WebhookValidator:
    def validate_signature(self, body: Union[bytes, Dict[Any, Any]], signature: str) -> bool:
        """
        Проверяет подпись вебхука от Remnawave.
        """
        if not settings.REMNAWAVE_WEBHOOK_SECRET:
            # Если секрет не настроен, не можем проверить подпись
            return False

        if isinstance(body, dict):
            body_bytes = json.dumps(body, separators=(',', ':')).encode('utf-8')
        else:
            body_bytes = body

        computed_signature = hmac.new(
            settings.REMNAWAVE_WEBHOOK_SECRET.encode('utf-8'),
            body_bytes,
            hashlib.sha256
        ).hexdigest()

        return hmac.compare_digest(computed_signature, signature)


webhook_validator = WebhookValidator()