#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""段 3 真實答案展示：跑招牌題，印完整答案 + LLM 原始 JSON（看 Gemini 真的有沒有翻車）。"""
import time
from datetime import date

import sys as _sys, pathlib as _pl
_R = next(p for p in _pl.Path(__file__).resolve().parents if (p / "config.example.json").exists())
_sys.path[:0] = [str(_R), str(_R / "assistant")]

from rag import load_config, load_catalog, answer

cfg = load_config()
catalog = load_catalog(cfg)
REF = date(2026, 6, 26)

QS = [
    "現在生小孩補助多少？",                                  # G 版本預告：答 6000 + 預告 7/1 起 10000
    "出差的時候如果遇到家裡有事要請事假，手續要怎麼辦？",    # H 防污染：不可把出差事後補單套到請假
    "公司可以帶寵物上班嗎？",                                # B 查無：誠實說沒有
]

for i, q in enumerate(QS):
    if i:
        time.sleep(4)
    r = answer(q, catalog, cfg, REF)
    print("=" * 72)
    print("【問題】", q)
    print("【路由】", r["routed"], "｜取到原文：", [f'{f["name"]} v{f["version"]}({f["status"]})' for f in r["fetched"]])
    print("-" * 72)
    print(r["answer_text"])
    print("-" * 72)
    print("[LLM 原始 JSON]", r["raw"])
    print()
