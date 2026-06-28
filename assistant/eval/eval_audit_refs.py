#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
eval_audit_refs.py — 程式反查（rag._audit_prose / _resolve_doc）回歸測試

鎖住 2026-06-28 修正：LLM 答案用簡稱/指代（同法、本辦法、施行細則）時，反查要能解析回
fetched 對應法並接地；★同時安全閘不可破——未檢索到的法、解到法但該條不存在、類稱在 fetched
不唯一者，一律照樣示警、絕不亂清（不可把真正的檢索漏失蓋掉）。

★自帶 fixture，不依賴任何外部檔／Gemini。路徑安全：從任何 cwd 都能跑：
    python assistant/eval/eval_audit_refs.py
"""
import sys
from pathlib import Path

# ── 路徑安全 bootstrap：往上找專案根（含 config.example.json）→ 把 assistant 上 path ──
_ROOT = next(p for p in Path(__file__).resolve().parents if (p / "config.example.json").exists())
sys.path.insert(0, str(_ROOT / "assistant"))

from rag import _audit_prose  # noqa: E402


def _doc(doc_no, name, tags, arts):
    return {"doc_no": doc_no, "name": name, "version": "2024-01-01",
            "path": f"corpus/sources/_eval/{name}.md", "tags": tags,
            "status": "生效中", "articles": arts}


# 假法規（條文內文只放占位；反查只比對「條號是否存在」，不看內文）
FIX = [
    _doc("T001", "測試就業平等法", ["測平法"], {
        "第 12 條": "第 12 條\n（性騷擾定義占位）",
        "第 16 條": "第 16 條\n（育嬰留停占位）",
        "第 21 條": "第 21 條\n（雇主不得拒絕占位）"}),
    _doc("T002", "測試就業平等法施行細則", [], {
        "第 4-3 條": "第 4-3 條\n（知悉不以申訴為限占位）"}),
    _doc("T003", "測試就業平等法檢舉辦法", [], {
        "第 6 條": "第 6 條\n（保密占位）"}),
]
# 加第二部「辦法」→ 類稱「辦法」在 fetched 不唯一，測「拒解、示警」
FIX_AMBIG = FIX + [_doc("T004", "測試就業平等法申訴辦法", [], {"第 5 條": "第 5 條\n（申訴占位）"})]


def _run(prose, fetched):
    add, _src, warns = _audit_prose(prose, fetched, set())
    return warns, add[0::2]      # warns, 補貼的 ■ 標頭


CASES = [
    # (名稱, prose, fetched, 預期判定(warns, 補貼)->bool)
    ("類稱_本辦法唯一可解並補貼",
     "依測試就業平等法第12條規定…又依本辦法第6條應予保密。", FIX,
     lambda w, s: not w and any("檢舉辦法" in x and "第 6 條" in x for x in s)),
    ("指代_同法解回前文法並補貼",
     "依測試就業平等法第16條…且依同法第21條，雇主不得拒絕。", FIX,
     lambda w, s: not w and any("第 21 條" in x for x in s)),
    ("類稱_施行細則唯一可解並補貼",
     "依測試就業平等法第12條…另依施行細則第4條之3辦理。", FIX,
     lambda w, s: not w and any("施行細則" in x and "第 4-3 條" in x for x in s)),
    ("安全_未檢索到法應示警",
     "另依勞工保險條例第10條請領給付。", FIX,
     lambda w, s: any("未檢索到" in x for x in w)),
    ("安全_解到法但條不存在應示警",
     "依測試就業平等法第12條…又依同法第999條…", FIX,
     lambda w, s: any("未在本次取得" in x for x in w)),
    ("安全_類稱不唯一(兩部辦法)應拒解示警",
     "依本辦法第5條規定辦理。", FIX_AMBIG,
     lambda w, s: any("未檢索到" in x for x in w)),
]


def main():
    fails = 0
    for name, prose, fetched, pred in CASES:
        warns, supplied = _run(prose, fetched)
        ok = pred(warns, supplied)
        print(f"[{'PASS' if ok else 'FAIL'}] {name}")
        if not ok:
            fails += 1
            print(f"    warns={warns}")
            print(f"    補貼={supplied}")
    print(f"\n{len(CASES) - fails}/{len(CASES)} PASS")
    sys.exit(1 if fails else 0)


if __name__ == "__main__":
    main()
