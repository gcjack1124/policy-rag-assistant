#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""透明化：印出路由真正送給 Gemini 的完整 prompt、Gemini 原始回應、每次耗時。"""
import time

import sys as _sys, pathlib as _pl
_R = next(p for p in _pl.Path(__file__).resolve().parents if (p / "config.example.json").exists())
_sys.path[:0] = [str(_R), str(_R / "assistant")]

from rag import load_config, load_catalog, routing_view, ROUTE_SYSTEM, call_gemini

cfg = load_config()
catalog = load_catalog(cfg)
view = routing_view(catalog)
catalog_text = "\n".join(
    f'- {v["doc_no"]}（{v["dept"]} {v["name"]}）：{v["summary"]}｜tags: {", ".join(v["tags"])}'
    for v in view
)

QUESTIONS = [
    "出差住宿費上限多少？",                              # A 直球
    "公司有沒有寵物友善政策，可以帶寵物上班嗎？",        # B 應查無
    "如果家裡突然有急事，我明天沒辦法去公司怎麼辦？",    # D 零關鍵字語意
]

print("#" * 72)
print("# 送給 Gemini 的 SYSTEM PROMPT（每題都一樣）")
print("#" * 72)
print(ROUTE_SYSTEM)

for q in QUESTIONS:
    prompt = "[目錄]\n" + catalog_text + f"\n\n[問題]\n{q}\n\n請輸出相關辦法的 doc_no JSON 陣列。"
    print("\n" + "#" * 72)
    print(f"# USER PROMPT — 問題：{q}")
    print("#" * 72)
    print(prompt)
    t0 = time.time()
    raw = call_gemini(prompt, cfg["model_route"], cfg, system=ROUTE_SYSTEM)
    dt = time.time() - t0
    print(f"\n>>> Gemini 原始回應（耗時 {dt:.2f} 秒，型號 {cfg['model_route']}）<<<")
    print("repr:", repr(raw))
    print("text:", raw)
    time.sleep(3)
