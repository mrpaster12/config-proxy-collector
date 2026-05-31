import re
import json
import base64
import html
import time
import requests
from urllib.parse import urlparse, parse_qs, unquote
from datetime import datetime

# Source channels list
VPN_CHANNELS = [
    "v2rayng_org", "v2ray_outline_config", "V2rayNG_VPNo", "V2ray_Alpha", "v2rayng_Configs",
    "free_v2ray_config", "v2ray_config_pool", "v2rayNG_VPN", "VPNGate_Central", "v2rayng_vpn1",
    "v2ray_vmess_vless", "v2ray_free_conf", "shadowsocks_free", "Vmess_Vless_Config", "npvchannel"
]

MTPROTO_CHANNELS = [
    "ProxyMTProto", "MTProto_Proxy", "TelMTProto", "ProxyForTelegram", "Pink_Proxy",
    "Golden_Proxy", "MelliProxy", "Proxy_MTProto_Telegram", "SanyProxy", "ActiveMTProto",
    "ProxyDao", "DailyMTProto", "IR_Proxy", "Bi_Proxy", "MTProtoProxies"
]

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
}

def parse_remark(config_str):
    """
    Attempts to extract a readable label/remark for different configuration schemas.
    """
    config_str = config_str.strip()
    if config_str.startswith("vmess://"):
        try:
            b64_part = config_str[8:].split('#')[0]
            b64_part += "=" * ((4 - len(b64_part) % 4) % 4)  # Fix padding
            decoded = base64.b64decode(b64_part).decode('utf-8', errors='ignore')
            data = json.loads(decoded)
            if 'ps' in data and data['ps']:
                return str(data['ps']).strip()
        except Exception:
            pass
            
    # Standard fallback for fragment extraction (everything after '#')
    try:
        parsed = urlparse(config_str)
        if parsed.fragment:
            return unquote(parsed.fragment).strip()
    except Exception:
        pass

    if "#" in config_str:
        try:
            return unquote(config_str.split("#")[-1]).strip()
        except Exception:
            pass

    return "پیکربندی بدون نام"

def scrape_vpn_configs():
    extracted_configs = []
    seen = set()
    vpn_pattern = re.compile(r'(?:vless|vmess|ss|trojan|tuic|hysteria2|hy2)://[^\s"\'<>]+')

    for channel in VPN_CHANNELS:
        url = f"https://t.me/s/{channel}"
        try:
            response = requests.get(url, headers=HEADERS, timeout=15)
            if response.status_code == 200:
                unescaped_html = html.unescape(response.text)
                matches = vpn_pattern.findall(unescaped_html)
                
                for match in matches:
                    clean_config = re.split(r'["\'<>\s]', match)[0].strip()
                    # Remove trailing punctuation often caught by broad regex
                    clean_config = clean_config.rstrip('.,;()[]{}<>')
                    
                    if clean_config and clean_config not in seen:
                        seen.add(clean_config)
                        
                        # Determine Protocol
                        protocol = "unknown"
                        for p in ["vless", "vmess", "ss", "trojan", "tuic", "hysteria2", "hy2"]:
                            if clean_config.startswith(f"{p}://"):
                                protocol = p
                                break
                        
                        remark = parse_remark(clean_config)
                        extracted_configs.append({
                            "protocol": protocol,
                            "config": clean_config,
                            "remark": remark,
                            "channel": channel,
                            "scraped_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                        })
            # Respectful throttling
            time.sleep(1)
        except Exception as e:
            print(f"Error scraping channel {channel}: {e}")
            
    return extracted_configs

def scrape_mtproto_proxies():
    extracted_proxies = []
    seen = set()
    proxy_pattern = re.compile(r'(?:tg://proxy\?|https://t.me/proxy\?)[^\s"\'<>]+')

    for channel in MTPROTO_CHANNELS:
        url = f"https://t.me/s/{channel}"
        try:
            response = requests.get(url, headers=HEADERS, timeout=15)
            if response.status_code == 200:
                unescaped_html = html.unescape(response.text)
                matches = proxy_pattern.findall(unescaped_html)
                
                for match in matches:
                    clean_proxy = re.split(r'["\'<>\s]', match)[0].strip()
                    clean_proxy = clean_proxy.rstrip('.,;()[]{}<>')
                    
                    # Unified scheme normalization
                    unified_proxy = clean_proxy.replace("https://t.me/proxy?", "tg://proxy?")
                    
                    if unified_proxy and unified_proxy not in seen:
                        seen.add(unified_proxy)
                        
                        # Extract query parameters
                        try:
                            parsed_url = urlparse(unified_proxy)
                            params = parse_qs(parsed_url.query)
                            server = params.get('server', [''])[0]
                            port = params.get('port', [''])[0]
                            secret = params.get('secret', [''])[0]
                            
                            if server and port and secret:
                                web_url = unified_proxy.replace("tg://proxy?", "https://t.me/proxy?")
                                extracted_proxies.append({
                                    "url": unified_proxy,
                                    "web_url": web_url,
                                    "server": server,
                                    "port": port,
                                    "secret": secret,
                                    "channel": channel,
                                    "scraped_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                                })
                        except Exception:
                            pass
            time.sleep(1)
        except Exception as e:
            print(f"Error scraping channel {channel}: {e}")
            
    return extracted_proxies

def main():
    print("Scraping VPN configurations...")
    configs = scrape_vpn_configs()
    
    print("Scraping MTProto Proxies...")
    proxies = scrape_mtproto_proxies()
    
    # Write Structured JSON for Frontend
    with open("configs.json", "w", encoding="utf-8") as f:
        json.dump(configs, f, ensure_ascii=False, indent=2)
        
    # Write Structured Proxies JSON
    proxies_output = {
        "updated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "proxies": proxies
    }
    with open("proxies.json", "w", encoding="utf-8") as f:
        json.dump(proxies_output, f, ensure_ascii=False, indent=2)

    # Generate v2ray client compatible subscriptions
    raw_configs = [item["config"] for item in configs]
    raw_configs_str = "\n".join(raw_configs)
    
    # Output plain text configuration subscription file
    with open("sub_raw.txt", "w", encoding="utf-8") as f:
        f.write(raw_configs_str)
        
    # Output Base64 subscription file (standard for most V2ray clients)
    b64_configs = base64.b64encode(raw_configs_str.encode('utf-8')).decode('utf-8')
    with open("sub.txt", "w", encoding="utf-8") as f:
        f.write(b64_configs)

    print(f"Successfully processed {len(configs)} configs and {len(proxies)} proxies.")

if __name__ == "__main__":
    main()