import os
import re

import requests

_USER_AGENT = "Mozilla/5.0 (compatible; DailyEnglish/1.0)"


def _windows_pac_proxy() -> str | None:
    try:
        import winreg
    except ImportError:
        return None

    try:
        with winreg.OpenKey(
            winreg.HKEY_CURRENT_USER,
            r"Software\Microsoft\Windows\CurrentVersion\Internet Settings",
        ) as k:
            pac_url, _ = winreg.QueryValueEx(k, "AutoConfigURL")
        if not pac_url:
            return None

        text = requests.get(
            pac_url, timeout=8, proxies={"http": None, "https": None}
        ).text
        m = re.search(r"PROXY\s+([\d.]+:\d+)", text)
        if m:
            return m.group(1)
        m = re.search(r"SOCKS5?\s+([\d.]+:\d+)", text)
        if m:
            return m.group(1)
    except Exception:
        return None
    return None


def get_proxies() -> dict | None:
    http_p = os.environ.get("HTTP_PROXY") or os.environ.get("http_proxy")
    https_p = os.environ.get("HTTPS_PROXY") or os.environ.get("https_proxy")
    if http_p or https_p:
        return {"http": http_p, "https": https_p or http_p}

    pac = _windows_pac_proxy()
    if pac:
        return {"http": f"http://{pac}", "https": f"http://{pac}"}
    return None


def fetch(url: str, timeout: int = 20) -> requests.Response:
    """抓取 URL，自动使用系统代理（env 或 Windows PAC），并回退 http/https、代理/直连。"""
    proxies = get_proxies()
    headers = {"User-Agent": _USER_AGENT}

    variants = [url]
    if url.startswith("https://"):
        variants.append("http://" + url[len("https://"):])
    elif url.startswith("http://"):
        variants.append("https://" + url[len("http://"):])

    seen: set[tuple[str, bool]] = set()
    last_err: Exception | None = None

    for v in variants:
        for p in (proxies, None):
            key = (v, bool(p))
            if key in seen:
                continue
            seen.add(key)
            try:
                resp = requests.get(v, timeout=timeout, proxies=p, headers=headers)
                resp.raise_for_status()
                return resp
            except Exception as e:
                last_err = e

    raise last_err if last_err else RuntimeError(f"抓取失败: {url}")
