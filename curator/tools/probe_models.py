#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""探針：對候選型號各打一次最小請求，摸清免費層哪些可用（limit=0/耗盡/可用）。"""
import time

import sys as _sys, pathlib as _pl
_R = next(p for p in _pl.Path(__file__).resolve().parents if (p / "config.example.json").exists())
_sys.path[:0] = [str(_R), str(_R / "assistant")]

from rag import load_config, get_client

cfg = load_config()
client = get_client(cfg)

CANDIDATES = [
    "gemini-3.5-flash",
    "gemini-2.5-flash-lite",
    "gemini-flash-latest",
    "gemini-2.0-flash",
    "gemini-3-flash-preview",
    "gemini-3.1-flash-lite",
]

for m in CANDIDATES:
    try:
        r = client.models.generate_content(model=m, contents="嗨")
        print(f"✅ {m}: 可用 -> {r.text[:20]!r}")
    except Exception as e:
        msg = str(e)
        if "limit: 0" in msg:
            print(f"🚫 {m}: 免費層 limit=0（不開放）")
        elif "RESOURCE_EXHAUSTED" in msg:
            print(f"⏳ {m}: 配額耗盡或 RPM 限制")
        else:
            print(f"❌ {m}: {msg[:90]}")
    time.sleep(2)
