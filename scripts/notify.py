"""Bark 推送辅助：从环境变量 BARK_URL 读取目标地址，向 iPhone 发送通知。"""
from __future__ import annotations

import json
import os

import requests

BARK_URL_ENV = "BARK_URL"


def send(
    title: str,
    body: str,
    group: str = "stock-scan",
    url: str | None = None,
) -> bool:
    bark_url = os.environ.get(BARK_URL_ENV)
    if not bark_url:
        print(f"[notify] 环境变量 {BARK_URL_ENV} 未配置，跳过推送")
        return False

    payload: dict[str, str] = {"title": title, "body": body, "group": group}
    if url:
        payload["url"] = url

    try:
        resp = requests.post(
            bark_url.rstrip("/"),
            json=payload,
            timeout=10,
        )
        ok = 200 <= resp.status_code < 300
        print(f"[notify] {'成功' if ok else f'失败 status={resp.status_code}'}")
        return ok
    except requests.RequestException as exc:
        print(f"[notify] 推送异常: {exc}")
        return False


if __name__ == "__main__":
    import sys

    title = sys.argv[1] if len(sys.argv) > 1 else "测试"
    body = sys.argv[2] if len(sys.argv) > 2 else "Bark 推送测试"
    send(title, body)
