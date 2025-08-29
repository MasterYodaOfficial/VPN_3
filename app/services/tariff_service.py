import json
from typing import List, Optional

from app.logger import logger
from database.models import Tariff
from database.session import get_session
from sqlalchemy import select



class TariffService:
    """
    Класс-сервис для управления бизнес-логикой, связанной с тарифами.
    Отвечает за загрузку, предоставление и управление тарифами.
    """

    async def load_and_sync_tariffs(self, file_path: str = "database/tariffs.json"):
        """
        Синхронизирует тарифы из JSON-файла с базой данных.
        - Обновляет существующие тарифы.
        - Добавляет новые.
        - Деактивирует те, которых нет в файле.
        Этот метод предназначен для вызова при старте приложения.
        """
        logger.info(f"Запуск синхронизации тарифов из файла: {file_path}")
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                json_tariffs = json.load(f)
        except FileNotFoundError:
            logger.error(f"Файл тарифов не найден по пути: {file_path}")
            return
        except json.JSONDecodeError:
            logger.error(f"Ошибка декодирования JSON в файле тарифов: {file_path}")
            return

        async with get_session() as session:
            # Получаем все тарифы из БД одним запросом
            existing_tariffs_result = await session.execute(select(Tariff))
            existing_tariffs_dict = {t.name: t for t in existing_tariffs_result.scalars().all()}

            json_tariff_names = set()

            for tariff_data in json_tariffs:
                name = tariff_data.get("name")
                if not name:
                    continue

                json_tariff_names.add(name)

                # Обновляем или создаем тариф
                tariff = existing_tariffs_dict.get(name)
                if tariff:
                    # Обновляем существующий
                    tariff.duration_days = tariff_data["duration_days"]
                    tariff.price = tariff_data["price"]
                    tariff.currency = tariff_data.get("currency", "RUB")
                    tariff.is_active = tariff_data.get("is_active", True)
                else:
                    # Создаем новый
                    session.add(Tariff(**tariff_data))

            # Деактивируем тарифы, которых больше нет в JSON-файле
            for name, tariff in existing_tariffs_dict.items():
                if name not in json_tariff_names:
                    tariff.is_active = False

            await session.commit()
        logger.info("Синхронизация тарифов успешно завершена.")

    async def get_active_tariffs(self) -> List[Tariff]:
        """
        Возвращает список всех активных тарифов, отсортированных по цене.
        Используется для отображения в клавиатурах бота.
        """
        async with get_session() as session:
            return await Tariff.get_active(session)

    async def get_tariff_by_id(self, tariff_id: int) -> Optional[Tariff]:
        """
        Получает конкретный тариф по его ID.
        """
        async with get_session() as session:
            return await Tariff.get_by_id(session, tariff_id)



tariff_service = TariffService()