#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""段 2 路由驗證：對 eval 題跑 route + resolve_versions，印命中表（只驗路由+版本，不答題）。"""
import time
from datetime import date

import sys as _sys, pathlib as _pl
_R = next(p for p in _pl.Path(__file__).resolve().parents if (p / "config.example.json").exists())
_sys.path[:0] = [str(_R), str(_R / "assistant")]

from rag import load_config, load_catalog, route, resolve_versions

cfg = load_config()
catalog = load_catalog(cfg)
REF = date(2026, 6, 26)  # 參考日＝今天

# (題號, 問題, 期望路由⊇此集合；空集合＝應查無)
CASES = [
    ("A",  "出差住宿費上限多少？", {"HR-002"}),
    ("B",  "公司有沒有寵物友善政策，可以帶寵物上班嗎？", set()),
    ("C",  "採購金額多少以上要三家比價？", {"GA-005"}),
    ("D",  "如果家裡突然有急事，我明天沒辦法去公司怎麼辦？", {"HR-001"}),
    ("E",  "我出差到一半，家裡有事要請假，怎麼算？", {"HR-002"}),
    ("G",  "現在生小孩補助多少？", {"HR-003"}),
    ("H",  "出差的時候如果遇到家裡有事要請事假，手續要怎麼辦？", {"HR-002"}),
    ("B2", "喪假可以請幾天？", {"HR-001"}),
]

print(f"參考日 D = {REF}\n{'='*60}")
passed = 0
for i, (tid, q, expect) in enumerate(CASES):
    if i:  # 題間退避，降低免費層 rate limit 撞線
        time.sleep(3)
    got = route(q, catalog, cfg)
    got_set = set(got)
    hit = (got_set == set()) if not expect else expect.issubset(got_set)
    mark = "✅" if hit else "❌"
    passed += hit
    print(f"\n{mark} [{tid}] {q}")
    print(f"     路由→ {got or '[]'}   期望⊇ {sorted(expect) or '（查無）'}")
    for dn, ver in resolve_versions(got, catalog, REF).items():
        a, u = ver["active"], ver["upcoming"]
        astr = a["doc_id"] if a else "（無生效中版）"
        ustr = f'｜⏳預告 {u["doc_id"]}（{u["effective_date"]} 起）' if u else ""
        print(f'     {dn} 版本守門：生效中={astr}{ustr}')

print(f"\n{'='*60}\n路由命中：{passed}/{len(CASES)}")
