import base64
import urllib.parse
from typing import List, Dict, Any
import yaml


def generate_full_clash_yaml(configs: List[str], logo_name: str) -> str:
    """
    Генерирует полнофункциональный Clash YAML с правилами и группами для Hiddify.
    """
    proxies = []
    proxy_groups = []

    for i, uri in enumerate(configs):
        try:
            parsed = urllib.parse.urlparse(uri)
            # Раскодируем имена с кириллицей и эмодзи для красивого отображения в Hiddify
            proxy_name = urllib.parse.unquote(parsed.fragment) or f"Server-{i + 1}"

            query_params = urllib.parse.parse_qs(parsed.query)
            proxy: Dict[str, Any] = {
                "name": proxy_name, "type": "vless", "server": parsed.hostname,
                "port": parsed.port, "uuid": parsed.username,
                "network": query_params.get("type", [""])[0],
                "tls": query_params.get("security", [""])[0] == "tls", "udp": True,
                "client-fingerprint": query_params.get("fp", [""])[0], "flow": query_params.get("flow", [""])[0]
            }
            if alpn := query_params.get("alpn", [""])[0]:
                proxy["alpn"] = [a.strip() for a in alpn.split(",")]
            proxies.append(proxy)
        except Exception as e:
            print(f"Error parsing URI for Clash YAML: {uri}, error: {e}")
            continue

    if proxies:
        all_proxy_names = [p["name"] for p in proxies]
        proxy_groups.extend([
            # Группа для ручного выбора, включает авто-выбор
            {"name": "PROXY", "type": "select", "proxies": ["Auto-Select ⚡️"] + all_proxy_names},
            # Группа для авто-выбора самого быстрого сервера
            {"name": "Auto-Select ⚡️", "type": "url-test", "proxies": all_proxy_names,
             "url": "http://www.gstatic.com/generate_204", "interval": 300},
        ])

    config = {
        # Базовые настройки для совместимости
        "port": 7890, "socks-port": 7891, "allow-lan": True, "mode": "rule",
        "log-level": "info", "ipv6": False,

        # Безопасные DNS-настройки, как у конкурентов
        "dns": {
            "enable": True, "enhanced-mode": "redir-host",
            "default-nameserver": ["1.1.1.1", "8.8.8.8"],
            "proxy-server-nameserver": ["1.1.1.1"],
            "nameserver": ["https://dns.google/dns-query", "https://cloudflare-dns.com/dns-query"]
        },

        "proxies": proxies,
        "proxy-groups": proxy_groups,

        # Простое правило по умолчанию: весь трафик через VPN
        "rules": ["MATCH,PROXY"]
    }

    return yaml.dump(config, allow_unicode=True, sort_keys=False)


def generate_base64_vless_list(configs: List[str]) -> str:
    """
    Создает простой список VLESS-ссылок и кодирует его в Base64 для Happ.
    """
    plain_text = "\n".join(configs)
    return base64.b64encode(plain_text.encode('utf-8')).decode('utf-8')


def generate_vless_list_for_happ(configs: List[str]) -> str:
    """
    Создает простой текстовый список VLESS-ссылок,
    разделенных переносом строки.
    Это формат, который ожидает Happ.
    """
    # Убедимся, что в списке нет пустых строк или None
    valid_configs = [c for c in configs if c]

    return "\n".join(valid_configs)