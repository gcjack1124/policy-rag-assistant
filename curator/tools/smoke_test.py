#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""段 1 smoke test：確認 Gemini key/型號可用。需先在 config.local.json 填入 key。"""
import sys as _sys, pathlib as _pl
_R = next(p for p in _pl.Path(__file__).resolve().parents if (p / "config.example.json").exists())
_sys.path[:0] = [str(_R), str(_R / "assistant")]

from rag import load_config, call_gemini

cfg = load_config()
if "PASTE" in cfg["gemini_api_key"]:
    raise SystemExit("⚠️ config.local.json 的 gemini_api_key 還是佔位字串，請先填入真實 key。")

print(f"用型號 {cfg['model_route']} 打 Gemini …")
ans = call_gemini("請用繁體中文一句話回答：你是哪一個 Gemini 模型？", cfg["model_route"], cfg)
print("Gemini 回應：", ans)
print("✅ smoke test 通過，Gemini 已接通。")
