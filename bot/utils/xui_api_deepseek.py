import base64
import json
import uuid
import urllib.parse
import aiohttp
import random
import string
from typing import Dict, Optional, Tuple




class XUIHandler:
    """Асинхронный класс для управления пользователями через панель 3x-ui."""

    def __init__(self, panel_url: str, username: str, password: str):
        self.panel_url = panel_url.rstrip('/')
        self.username = username
        self.password = password
        self.session = None  # Сессия будет инициализирована асинхронно
        self.inbound_id = None

    async def __aenter__(self):
        await self.login()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.close()

    async def login(self) -> None:
        """Асинхронная авторизация на панели управления."""
        self.session = aiohttp.ClientSession()
        try:
            async with self.session.post(
                    f"{self.panel_url}/login",
                    json={"username": self.username, "password": self.password},
                    timeout=aiohttp.ClientTimeout(total=10)
            ) as response:
                if response.status != 200:
                    raise AuthenticationError("Invalid credentials")
        except aiohttp.ClientError as ex:
            raise ConnectionError(f"Connection error: {ex}")

    async def close(self) -> None:
        """Закрытие асинхронной сессии."""
        if self.session:
            await self.session.close()

    async def get_clients(self) -> Optional[Dict]:
        """Асинхронное получение списка клиентов."""
        try:
            async with self.session.get(f"{self.panel_url}/panel/api/inbounds/list") as response:
                response.raise_for_status()
                data = await response.json()
                return self._normalize_json(data)
        except (aiohttp.ClientError, json.JSONDecodeError) as ex:
            print(f"Error getting clients: {str(ex)}")
            return None

    async def get_inbounds(self) -> Optional[Dict]:
        """Получает список всех инбаундов и кэширует первый ID VLESS."""
        try:
            async with self.session.get(f"{self.panel_url}/panel/api/inbounds/list") as response:
                response.raise_for_status()
                data = await response.json()
                normalized = self._normalize_json(data)

                # Находим первый VLESS инбаунд
                for inbound in normalized.get('obj', []):
                    if inbound.get('protocol') == 'vless':
                        self.inbound_id = int(inbound['id'])
                        break
                return normalized
        except (aiohttp.ClientError, json.JSONDecodeError) as ex:
            print(f"Error getting inbounds: {str(ex)}")
            return None

    async def add_client_vless(self, email: str, uid: str) -> Optional[str]:
        """Асинхронное добавление VLESS-клиента."""
        try:
            await self.get_inbounds()
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
            payload = {"id": self.inbound_id, "settings": json.dumps({"clients": [client_data]})}

            async with self.session.post(
                    f"{self.panel_url}/panel/api/inbounds/addClient",
                    json=payload,
                    headers={'Accept': 'application/json'},
                    timeout=aiohttp.ClientTimeout(total=15)
            ) as response:
                response.raise_for_status()
                return uid
        except (aiohttp.ClientError, KeyError) as ex:
            print(f"Error adding client: {str(ex)}")
            return None

    async def get_conf_user_vless(self, email: str, conf_name: str) -> Optional[str]:
        """Асинхронная генерация конфигурационной ссылки."""
        try:
            inbounds = await self.get_clients()
            if not inbounds or 'obj' not in inbounds:
                print("No inbounds found")
                return None

            server_address = self.panel_url.split('://')[-1].split(':')[0]
            if '/' in server_address:
                server_address = server_address.split('/')[0]

            for inbound in inbounds['obj']:
                if inbound.get('protocol') != 'vless':
                    continue
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
                            conf_name=conf_name
                        )
            print(f"Client {email} not found")
            return None
        except Exception as ex:
            print(f"Error generating config: {str(ex)}")
            return None

    async def delete_client_vless(self, client_uuid: str) -> bool:
        """Асинхронное удаление клиента."""
        try:
            await self.get_inbounds()
            async with self.session.post(
                    f"{self.panel_url}/panel/api/inbounds/{self.inbound_id}/delClient/{client_uuid}",
                    timeout=aiohttp.ClientTimeout(total=10)
            ) as response:
                response.raise_for_status()
                if response.status == 200:
                    print(f"Client {client_uuid} deleted successfully")
                    return True
                return False
        except aiohttp.ClientError as ex:
            print(f"Error deleting client: {str(ex)}")
            return False


    @staticmethod
    def generate_random_string(length=10):
        characters = string.ascii_letters + string.digits
        return ''.join(random.choices(characters, k=length))


    @staticmethod
    def _build_vless_url(**kwargs) -> str:
        """Формирует VLESS-ссылку с правильными параметрами безопасности."""
        client = kwargs['client']
        inbound = kwargs['inbound']
        stream_settings = kwargs['stream_settings']
        server_address = kwargs['server_address']
        conf_name = kwargs['conf_name']

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
            f"{conf_name}"
        ))


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


class AuthenticationError(Exception):
    pass
