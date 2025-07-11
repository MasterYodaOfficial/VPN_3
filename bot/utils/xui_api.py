import base64
import json
import uuid
from typing import Dict, Optional
import urllib.parse
from bot.utils.logger import logger
import requests
from requests.exceptions import RequestException
import random
import string


class XUIHandler:
    """Класс для управления пользователями и конфигурациями сервера через панель 3x-ui.

    Предоставляет методы для взаимодействия с API панели управления, включая авторизацию,
    управление клиентами и генерацию конфигурационных ссылок.

    Атрибуты:
        panel_url (str): URL панели управления с портом
        username (str): Имя пользователя для авторизации
        password (str): Пароль пользователя
        session (requests.session): Сессия для выполнения HTTP-запросов

    Исключения:
        ConnectionError: Возникает при проблемах с подключением к панели
        AuthenticationError: Возникает при неверных учетных данных

    """

    def __init__(self, panel_url: str, username: str, password: str):
        """Инициализирует экземпляр XUIHandler.

        Args:
            panel_url: URL панели управления с портом (например, 'http://example.com:54321')
            username: Имя пользователя для авторизации
            password: Пароль пользователя

        Raises:
            ConnectionError: При невозможности подключиться к серверу
            AuthenticationError: При неверных учетных данных
        """
        self.panel_url = panel_url.rstrip('/')
        self.username = username
        self.password = password
        self.session = requests.Session()
        self._login()

    def __enter__(self):
        """Возвращает экземпляр класса при входе в контекстный менеджер."""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Закрывает сессию при выходе из контекстного менеджера."""
        self.session.close()

    def _login(self) -> None:
        """Выполняет авторизацию на панели управления.

        Raises:
            ConnectionError: При проблемах с подключением
            AuthenticationError: При неверных учетных данных
        """
        try:
            response = self.session.post(
                f"{self.panel_url}/login",
                json={"username": self.username, "password": self.password},
                timeout=10
            )
            if response.status_code != 200:
                raise AuthenticationError("Invalid credentials")
        except RequestException as ex:
            logger.error(ex)

    def _normalize_json(self, data):
        """Рекурсивно преобразует строки с JSON-данными в объекты Python.

        Args:
            data: Входные данные для нормализации

        Returns:
            Нормализованные данные с преобразованными JSON-строками
        """
        if isinstance(data, dict):
            return {k: self._normalize_json(v) for k, v in data.items()}
        if isinstance(data, list):
            return [self._normalize_json(item) for item in data]
        if isinstance(data, str):
            try:
                return self._normalize_json(json.loads(data))
            except json.JSONDecodeError:
                return data
        return data

    def get_clients(self) -> Optional[Dict]:
        """Получает список всех клиентов из всех inbounds.

        Returns:
            Словарь с информацией о клиентах или None в случае ошибки

        """
        try:
            response = self.session.get(f"{self.panel_url}/panel/api/inbounds/list")
            response.raise_for_status()
            return self._normalize_json(response.json())
        except (RequestException, json.JSONDecodeError) as ex:
            logger.error(f"Error getting clients: {str(ex)}")
            return None

    def add_client_vless(self, inbound_id: int, email: str) -> str or None:
        """Добавляет нового VLESS-клиента в указанный inbound.

        Args:
            inbound_id: ID существующего inbound
            email: Уникальный идентификатор клиента (email)

        Returns:
            uid пользователя или None при ошибке
        """
        try:
            uid = str(uuid.uuid4())
            client_data = {
                "id": uid,
                "flow": "xtls-rprx-vision",
                "email": email,
                "limitIp": 0,
                "totalGB": 0,
                "expiryTime": 0,
                "enable": True,
                "tgId": "",
                "subId": base64.urlsafe_b64encode(uuid.uuid4().bytes).decode().rstrip('=')[:12],
                "reset": 0
            }

            payload = {
                "id": inbound_id,
                "settings": json.dumps({"clients": [client_data]})
            }

            response = self.session.post(
                f"{self.panel_url}/panel/api/inbounds/addClient",
                json=payload,
                headers={'Accept': 'application/json'},
                timeout=15
            )
            response.raise_for_status()
            return uid
        except (RequestException, KeyError) as ex:
            logger.error(f"Error adding client: {str(ex)}")
            return None

    def get_conf_user_vless(
            self,
            email: str,
            server_address: Optional[str] = None
    ) -> Optional[str]:
        """Генерирует конфигурационную ссылку VLESS для указанного клиента."""
        try:
            inbounds = self.get_clients()
            if not inbounds or 'obj' not in inbounds:
                logger.error("No inbounds found")
                return None

            server_address = server_address or self.panel_url.split('://')[-1].split(':')[0]
            if '/' in server_address:
                server_address = server_address.split('/')[0]

            for inbound in inbounds['obj']:
                if inbound.get('protocol') != 'vless':
                    continue

                # Парсим настройки с обработкой JSON-строк
                settings = json.loads(inbound['settings']) if isinstance(inbound['settings'], str) else inbound[
                    'settings']
                stream_settings = json.loads(inbound['streamSettings']) if isinstance(inbound['streamSettings'],
                                                                                      str) else inbound[
                    'streamSettings']

                for client in settings.get('clients', []):
                    if client.get('email') == email:
                        return self._build_vless_url(
                            client=client,
                            inbound=inbound,
                            stream_settings=stream_settings,
                            server_address=server_address,
                            email=email
                        )
            logger.error(f"Client {email} not found")
            return None
        except Exception as ex:
            logger.error(f"Error generating config: {str(ex)}")
            return None

    @staticmethod
    def _build_vless_url(**kwargs) -> str:
        """Формирует VLESS-ссылку с правильными параметрами безопасности."""
        client = kwargs['client']
        inbound = kwargs['inbound']
        stream_settings = kwargs['stream_settings']
        server_address = kwargs['server_address']
        email = kwargs['email']

        params = {
            'type': stream_settings.get('network', 'tcp'),
            'security': stream_settings.get('security', 'none')
        }

        security_type = stream_settings.get('security')
        tls_settings = stream_settings.get('tlsSettings', {})
        reality_settings = stream_settings.get('realitySettings', {})

        # Обработка TLS параметров
        if security_type == 'tls':
            if tls_settings.get('serverName'):
                params['sni'] = tls_settings['serverName']

            if tls_settings.get('settings', {}).get('fingerprint'):
                params['fp'] = tls_settings['settings']['fingerprint']

            if tls_settings.get('alpn'):
                params['alpn'] = ','.join(tls_settings['alpn'])

        # Обработка Reality параметров
        elif security_type == 'reality':
            if reality_settings.get('dest'):
                params['sni'] = reality_settings['dest'].split(':')[0]

            if reality_settings.get('settings', {}).get('fingerprint'):
                params['fp'] = reality_settings['settings']['fingerprint']

            if reality_settings.get('settings', {}).get('publicKey'):
                params['pbk'] = reality_settings['settings']['publicKey']

            if reality_settings.get('shortIds'):
                params['sid'] = reality_settings['shortIds'][0]

            if reality_settings.get('settings', {}).get('spiderX'):
                params['spx'] = reality_settings['settings']['spiderX']

        # Добавляем поток если есть
        if client.get('flow'):
            params['flow'] = client['flow']

        # Удаляем пустые и невалидные параметры
        clean_params = {}
        for k, v in params.items():
            if v and (k != 'sni' or security_type == 'tls'):
                clean_params[k] = v

        # Формируем URL
        return urllib.parse.urlunparse((
            'vless',
            f"{client['id']}@{server_address}:{inbound['port']}",
            '',
            '',
            urllib.parse.urlencode(clean_params, doseq=True, safe='/:'),
            urllib.parse.quote(email, safe='')  # Кодируем только email
        ))

    @staticmethod
    def generate_random_string(length=10):
        characters = string.ascii_letters + string.digits
        return ''.join(random.choices(characters, k=length))

    def delete_client_vless(self, inbound_id: int, client_uuid: str) -> bool:
        """Удаляет клиента VLESS из указанного inbound.

        Args:
            inbound_id: ID inbound, из которого нужно удалить клиента.
            client_uuid: UUID клиента, которого нужно удалить.

        Returns:
            bool: True, если клиент успешно удален, иначе False.

        Raises:
            RequestException: Если произошла ошибка при выполнении запроса.
        """
        try:
            response = self.session.post(
                f"{self.panel_url}/panel/api/inbounds/{inbound_id}/delClient/{client_uuid}",
                timeout=10
            )
            response.raise_for_status()

            # Проверяем, что клиент успешно удален
            if response.status_code == 200:
                logger.info(f"Client {client_uuid} successfully deleted from inbound {inbound_id}.")
                return True
            else:
                logger.error(f"Failed to delete client {client_uuid} from inbound {inbound_id}.")
                return False
        except RequestException as ex:
            logger.error(f"Error deleting client {client_uuid}: {str(ex)}")
            return False


class AuthenticationError(Exception):
    """Ошибка аутентификации при неверных учетных данных."""


server = XUIHandler(
    panel_url="https://serv1.myquickcloud.ru:40771/24l6Jo2YjXSjyCH/",
    username="RoWaVjRRw5",
    password="sb5f0bdGTa"
)