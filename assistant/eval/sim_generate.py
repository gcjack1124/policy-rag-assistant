#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
sim_generate.py — 不靠 Gemini 測「generate 生成端」的模擬 harness

用途：Gemini 配額耗盡／503 時仍能端到端測 LLM 生成端。把真實 route+fetch+窄餵建出的
「那一份 generate prompt」dump 出來 → 交 Claude sub-agent 當 generate 替身產 JSON → 再走回
真實 _parse_answer + _render_answer（含程式反查）。
★忠實性／反作弊：替身只能看這份 prompt、禁用先驗知識（由派工 prompt 強制）；docs 由真實
route 挑，retrieval 漏掉的替身也看不到。

半自動三步：
  1) python assistant/eval/sim_generate.py build    # 產 <OUT>/_system.txt + 各題 .prompt.txt + .fetched.pkl
  2) 主 context 派 sub-agent：讀 _system.txt + <qid>.prompt.txt，依規則寫 <qid>.out.json
  3) python assistant/eval/sim_generate.py render   # 讀 .out.json + .fetched.pkl → 渲染最終答案（含反查）

題庫改下方 QS。輸出落在 <專案根>/temp/sim_run/（暫存、可刪）。
"""
import sys
import glob
import pickle
from pathlib import Path
from datetime import date

# ── 路徑安全 bootstrap：往上找專案根（含 config.example.json）→ 把 assistant 上 path ──
_ROOT = next(p for p in Path(__file__).resolve().parents if (p / "config.example.json").exists())
sys.path.insert(0, str(_ROOT / "assistant"))

from rag import (load_config, load_catalog, route, resolve_versions, fetch,  # noqa: E402
                 narrow_fetched, GEN_SYSTEM, _render_block, _parse_answer,
                 _render_answer, NARROW_THRESHOLD)

OUT = _ROOT / "temp" / "sim_run"

QS = {
    "q1": "我家小孩才14歲，暑假想去打工賺點零用錢，法律上到底允不允許？",
    # 自行增減題目
}


def build():
    cfg = load_config(); catalog = load_catalog(cfg); ref = date.today()
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "_system.txt").write_text(GEN_SYSTEM, encoding="utf-8")
    for qid, q in QS.items():
        routed = route(q, catalog, cfg)
        fetched = fetch(resolve_versions(routed, catalog, ref), catalog, ref)
        fetched, _ = narrow_fetched(fetched, q, cfg, cfg.get("narrow_threshold", NARROW_THRESHOLD))
        active = [f for f in fetched if f["status"] == "生效中"]
        upcoming = [f for f in fetched if f["status"] == "未生效預告"]
        prompt = (f"[現行生效中條文（據以回答）]\n{_render_block(active)}\n\n"
                  f"[已公告未生效之新版條文（僅供預告，不可當現行答案）]\n{_render_block(upcoming)}\n\n"
                  f"[問題]\n{q}")
        (OUT / f"{qid}.prompt.txt").write_text(prompt, encoding="utf-8")
        pickle.dump(fetched, open(OUT / f"{qid}.fetched.pkl", "wb"))
        print(f"{qid}: routed={routed} fetched={[f['doc_id'] for f in fetched]}")
    print(f"build done → {OUT}\n（接著派 sub-agent 產 <qid>.out.json，再跑 render）")


def render():
    for pf in sorted(glob.glob(str(OUT / "*.out.json"))):
        qid = Path(pf).name[:-len(".out.json")]
        result = _parse_answer(Path(pf).read_text(encoding="utf-8"))
        fetched = pickle.load(open(OUT / f"{qid}.fetched.pkl", "rb"))
        print("=" * 72); print("#", qid)
        print(_render_answer(result, fetched))


if __name__ == "__main__":
    mode = sys.argv[1] if len(sys.argv) > 1 else ""
    if mode == "build":
        build()
    elif mode == "render":
        render()
    else:
        print("用法：python assistant/eval/sim_generate.py [build|render]")
        sys.exit(2)
