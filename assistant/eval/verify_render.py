#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""零配額驗證：用 demo 已拿到的真實 LLM 輸出（名稱式 citation），離線重跑修好的 _render_answer。
不呼叫 Gemini，只驗 code 後處理：verbatim 原文是否插入、載點是否填上。"""
from datetime import date

import sys as _sys, pathlib as _pl
_R = next(p for p in _pl.Path(__file__).resolve().parents if (p / "config.example.json").exists())
_sys.path[:0] = [str(_R), str(_R / "assistant")]

from rag import load_config, load_catalog, resolve_versions, fetch, _render_answer

cfg = load_config()
catalog = load_catalog(cfg)
REF = date(2026, 6, 26)

# routed + 上一輪 demo 真實拿到的 LLM result（citation 用辦法名稱，正是踩到 bug 的格式）
CASES = [
    (["HR-003"], {
        "found": True,
        "answer": "目前生育津貼每胎 6,000 元；新版 v2.0 將於 2026-07-01 起調為 10,000 元，現行仍適用舊版。",
        "citations": [{"doc_no": "生育津貼補助辦法 v1.0", "articles": ["第三條"]}],
    }),
    (["HR-001", "HR-002"], {
        "found": True,
        "answer": "出差第六條→請假第四條(事假)；程序依請假第五條事先申請；出差的事後補單不可套到請假。",
        "citations": [{"doc_no": "出差管理辦法 v2.0", "articles": ["第六條"]},
                      {"doc_no": "請假管理辦法 v1.0", "articles": ["第四條", "第五條"]}],
    }),
]

for routed, llm in CASES:
    vm = resolve_versions(routed, catalog, REF)
    fetched = fetch(vm, catalog, REF)
    print("=" * 72)
    print(_render_answer(llm, fetched))
    print()
