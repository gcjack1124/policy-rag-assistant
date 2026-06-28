#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""段 3 完整批量驗收：A–H＋B2 跑真實答題，自動斷言（路由/found/必含/禁含）+ 印全文人工複核。
每題撞配額時 try/except 跳過、繼續，最後報告。"""
import time

from datetime import date

import sys as _sys, pathlib as _pl
_R = next(p for p in _pl.Path(__file__).resolve().parents if (p / "config.example.json").exists())
_sys.path[:0] = [str(_R), str(_R / "assistant")]

from rag import load_config, load_catalog, answer

cfg = load_config()
catalog = load_catalog(cfg)
REF = date(2026, 6, 26)


def norm(s):
    return s.replace(",", "").replace(" ", "").replace("，", "")


# route: 期望⊇此集合（空=應查無）｜found: 期望 found 值｜must: 全須含｜mustnot: 全不可含
CASES = [
    {"id": "A",  "q": "出差住宿費上限多少？",
     "route": {"HR-002"}, "found": True,  "must": ["2,000"], "mustnot": []},
    {"id": "B",  "q": "公司有沒有寵物友善政策，可以帶寵物上班嗎？",
     "route": set(),      "found": False, "must": [],        "mustnot": []},
    {"id": "C",  "q": "採購金額多少以上要三家比價？",
     "route": {"GA-005"}, "found": True,  "must": ["10萬"],  "mustnot": ["5萬"]},
    {"id": "D",  "q": "如果家裡突然有急事，我明天沒辦法去公司怎麼辦？",
     "route": {"HR-001"}, "found": True,  "must": ["事假"],  "mustnot": ["事後補假"]},
    {"id": "E",  "q": "我出差到一半，家裡有事要請假，怎麼算？",
     "route": {"HR-001", "HR-002"}, "found": True, "must": ["事假"], "mustnot": []},
    {"id": "G",  "q": "現在生小孩補助多少？",
     "route": {"HR-003"}, "found": True,  "must": ["6,000"], "mustnot": []},
    {"id": "H",  "q": "出差的時候如果遇到家裡有事要請事假，手續要怎麼辦？",
     "route": {"HR-002"}, "found": True,  "must": ["事先"],  "mustnot": ["事後補假"]},
    {"id": "B2", "q": "喪假可以請幾天？",
     "route": {"HR-001"}, "found": False, "must": [],        "mustnot": []},
]

results = []
for i, case in enumerate(CASES):
    if i:
        time.sleep(4)
    try:
        r = answer(case["q"], catalog, cfg, REF)
    except Exception as e:
        print(f"\n[{case['id']}] ⚠️ API 錯誤（可能配額）：{str(e)[:140]}")
        results.append((case["id"], None))
        continue

    at = r["answer_text"]
    n = norm(at)
    route_ok = (set(r["routed"]) == set()) if not case["route"] else case["route"].issubset(set(r["routed"]))
    found_ok = (r["raw"]["found"] == case["found"])
    must_ok = all(norm(m) in n for m in case["must"])
    mustnot_ok = all(norm(x) not in n for x in case["mustnot"])
    ok = route_ok and found_ok and must_ok and mustnot_ok
    results.append((case["id"], ok))

    print("\n" + "=" * 72)
    print(f"[{case['id']}] {case['q']}")
    print(f"  路由{'✅' if route_ok else '❌'}({r['routed']})  "
          f"found{'✅' if found_ok else '❌'}({r['raw']['found']})  "
          f"必含{'✅' if must_ok else '❌'}{case['must']}  "
          f"禁含{'✅' if mustnot_ok else '❌'}{case['mustnot']}  → {'PASS' if ok else 'FAIL'}")
    print("-" * 72)
    print(at)

print("\n" + "#" * 72)
done = [r for r in results if r[1] is not None]
passed = [r for r in done if r[1]]
print(f"# 完成 {len(done)}/{len(CASES)} 題；PASS {len(passed)}/{len(done)}　"
      f"明細：{[(i, 'P' if v else 'F' if v is False else 'skip') for i, v in results]}")
