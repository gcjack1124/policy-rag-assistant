#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""用真實政府法規測 RAG（過濾掉合成公司辦法，只留 classification=公開 的政府法規）。"""
import time
from datetime import date

import sys as _sys, pathlib as _pl
_R = next(p for p in _pl.Path(__file__).resolve().parents if (p / "config.example.json").exists())
_sys.path[:0] = [str(_R), str(_R / "assistant")]

from rag import load_config, load_catalog, answer

cfg = load_config()
catalog = load_catalog(cfg)
gov = [e for e in catalog if e.get("classification") == "公開"]
REF = date(2026, 6, 27)
print(f"政府法規語料：{len(gov)} 部　{[e['name'] for e in gov]}\n")

QS = [
    "我們局裡這次要辦一個資安系統開發案，金額大約 800 萬，可以用『最有利標』找特定廠商議價嗎？還是必須公開評選？",
    "我們單位今年被歸類在『B級機關』，如果發生『三級資安事件』，我們要在多久以內通報？由誰來做通報？",
    "我們那個專案的廠商因為天災延誤履約，合約有寫逾期違約金。我可以幫他免除全部的違約金嗎？還是有上限扣減？",
    "我手上有一個 120 萬的勞務採購案，可以直接找廠商辦理限制性招標（比價）嗎？",
    "我們要委託專利商標事務所幫忙打官司和申請專利，這屬於專業服務還是技術服務？預算編列要用哪一種計費方式？",
]

for i, q in enumerate(QS):
    if i:
        time.sleep(4)
    r = answer(q, gov, cfg, REF)
    print("=" * 76)
    print(f"Q{i + 1}：{q}")
    print(f"路由→ {r['routed']}")
    print("-" * 76)
    print(r["answer_text"])
    print()
