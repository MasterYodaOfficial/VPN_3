# import yaml
# from urllib.parse import urlparse, parse_qs, unquote
#
# def parse_vless_uri(uri: str) -> dict:
#     # uri: "vless://uuid@host:port?query#name"
#     parsed = urlparse(uri)
#     scheme = parsed.scheme  # vless
#     userinfo = parsed.username  # uuid
#     host = parsed.hostname
#     port = parsed.port
#     query = parse_qs(parsed.query)
#     name = unquote(parsed.fragment)  # название
#
#     proxy = {
#         "name": name or f"{host}:{port}",
#         "type": scheme,
#         "server": host,
#         "port": port,
#         "uuid": userinfo,
#         "tls": query.get("security", [""])[0] == "tls",
#         "network": query.get("type", [""])[0],
#         "other_params": {}
#     }
#
#     # Добавим остальные параметры в other_params
#     for k, v in query.items():
#         if k not in ("security", "type"):
#             proxy["other_params"][k] = v[0]
#
#     return proxy
#
# def generate_vpn_yaml(configs: list[str]) -> str:
#     proxies = [parse_vless_uri(c) for c in configs]
#     data = {
#         "proxies": proxies,
#         "name": "MyVPN Configs ❤️"
#     }
#     return yaml.dump(data, sort_keys=False, allow_unicode=True)

import urllib.parse
from collections import defaultdict
from typing import List, Dict, Any
import yaml


def generate_vpn_yaml(configs: List[str]) -> str:
    """
    Преобразует список VLESS-конфигов в YAML для VPN приложений
    """
    proxies = []
    proxy_groups = []
    country_proxies = defaultdict(list)

    for uri in configs:
        try:
            # Парсинг URI
            parsed = urllib.parse.urlparse(uri)

            # Извлечение базовых параметров
            uuid = parsed.username
            server = parsed.hostname
            port = parsed.port
            country = parsed.fragment

            # Парсинг query-параметров
            query_params = urllib.parse.parse_qs(parsed.query)
            get_first = lambda key: query_params.get(key, [""])[0]

            # Построение конфига для прокси
            proxy: Dict[str, Any] = {
                "name": country,
                "type": "vless",
                "server": server,
                "port": port,
                "uuid": uuid,
                "network": get_first("type"),
                "tls": get_first("security") == "tls",
                "client-fingerprint": get_first("fp"),
                "flow": get_first("flow")
            }

            # Обработка ALPN
            if alpn := get_first("alpn"):
                proxy["alpn"] = [a.strip() for a in alpn.split(",")]

            # Удаление пустых значений
            proxy = {k: v for k, v in proxy.items() if v not in [None, "", []]}

            proxies.append(proxy)
            country_proxies[country].append(country)

        except Exception as e:
            # Логирование ошибок в реальном приложении
            continue

    # Группировка прокси
    if country_proxies:
        # Группа "auto" для автоматического выбора
        proxy_groups.append({
            "name": "auto",
            "type": "url-test",
            "proxies": [c for c in country_proxies.keys()],
            "url": "http://www.gstatic.com/generate_204",
            "interval": 300
        })

        # Группы по странам
        for country, names in country_proxies.items():
            proxy_groups.append({
                "name": country,
                "type": "select",
                "proxies": names
            })

    # Сборка финального конфига
    config = {
        "name": "VPN_Quick",
        "proxies": proxies,
        "proxy-groups": proxy_groups,
        "rules": ["MATCH,auto"]  # Стандартное правило
    }

    return yaml.dump(config, allow_unicode=True, sort_keys=False)
