from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse
from pathlib import Path

media_router = APIRouter(prefix="/media", tags=["Media Files"])

MEDIA_DIR = Path(__file__).resolve().parent.parent / "bot" / "media"


@media_router.get("/{filename}")
async def get_media_file(filename: str):
    """
    Отдает медиафайл (logo.jpg, referral.jpg, welcome.jpg) из папки app/bot/media.
    """
    # Безопасность: проверяем, что в имени файла нет ".." для защиты от выхода из директории
    if ".." in filename:
        raise HTTPException(status_code=400, detail="Invalid filename")

    file_path = MEDIA_DIR / filename

    # Проверяем, существует ли файл
    if not file_path.is_file():
        raise HTTPException(status_code=404, detail="File not found")

    # Отдаем файл
    return FileResponse(file_path)