import urllib.parse
from typing import List, Dict, Any
import yaml


def generate_yaml_for_hiddify(configs: List[str], logo_name: str) -> str:
    """
    Генерирует полнофункциональный YAML-профиль для Hiddify
    с поддержкой кириллицы, эмодзи и групп серверов.
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
                "name": proxy_name,
                "type": "vless",
                "server": parsed.hostname,
                "port": parsed.port,
                "uuid": parsed.username,
                "network": query_params.get("type", [""])[0],
                "tls": query_params.get("security", [""])[0] == "tls",
                "udp": True,
                "client-fingerprint": query_params.get("fp", [""])[0],
                "flow": query_params.get("flow", [""])[0]
            }
            if alpn := query_params.get("alpn", [""])[0]:
                proxy["alpn"] = [a.strip() for a in alpn.split(",")]
            proxies.append(proxy)
        except Exception as e:
            print(f"Error parsing Hiddify config from URI: {uri}, error: {e}")
            continue

    if proxies:
        all_proxy_names = [p["name"] for p in proxies]
        proxy_groups.extend([
            {"name": "Auto ⚡️", "type": "url-test", "proxies": all_proxy_names,
             "url": "http://www.gstatic.com/generate_204", "interval": 300},
            {"name": "Select-Server", "type": "select", "proxies": ["Auto ⚡️"] + all_proxy_names}
        ])

    config = {
        # 'name' в теле дублируем, так как некоторые клиенты предпочитают его, а не заголовок
        "name": f"🚀 {logo_name}",
        "proxies": proxies,
        "proxy-groups": proxy_groups,
        "rules": ["MATCH,Auto ⚡️"]
    }

    # Добавляем стандартные поля для полной совместимости
    standard_fields = "port: 7890\nsocks-port: 7891\nallow-lan: false\nmode: rule\nlog-level: info\n"
    yaml_config = yaml.dump(config, allow_unicode=True, sort_keys=False)

    return standard_fields + yaml_config