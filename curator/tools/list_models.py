#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""列出你這把 key 實際可用、且支援 generateContent 的型號。需先填 config.local.json。"""
import sys as _sys, pathlib as _pl
_R = next(p for p in _pl.Path(__file__).resolve().parents if (p / "config.example.json").exists())
_sys.path[:0] = [str(_R), str(_R / "assistant")]

from rag import load_config, get_client

cfg = load_config()
if "PASTE" in cfg["gemini_api_key"]:
    raise SystemExit("⚠️ config.local.json 的 gemini_api_key 還是佔位字串，請先填入真實 key。")

client = get_client(cfg)
print("你的 key 可用的型號：\n")
for m in client.models.list():
    actions = getattr(m, "supported_actions", None) or getattr(m, "supported_generation_methods", None) or []
    if not actions or "generateContent" in actions:
        name = m.name.replace("models/", "")
        flag = " ⭐flash" if "flash" in name.lower() else ""
        print(f"  {name}{flag}")
