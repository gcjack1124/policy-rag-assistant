#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
build_catalog.py — 掃 corpus/sources/ 產出 corpus/catalog.json（路由索引）

零依賴。屬四階段 A 攝取，PoC 版：解析 frontmatter → 條級切分 → 抽交叉引用 → 寫 catalog.json。
★三態不凍結（查詢時依參考日 D 算）；catalog 不含條文全文（rag.py 按條號回原檔撈）。
解析函式與路徑常數集中於專案根 corpus_io.py。
"""
import json
import sys
from pathlib import Path

# ── 專案根 bootstrap（搬資料夾後讓跨層 import corpus_io）──────────
_ROOT = next(p for p in Path(__file__).resolve().parents if (p / "config.example.json").exists())
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from corpus_io import (PROJECT_ROOT, SOURCES, CATALOG, XREF_RE,
                       parse_frontmatter, split_articles)


def extract_xrefs(contents):
    """從每條內文抽「依○○辦法第○條」→ 引用圖。"""
    refs = []
    for art, txt in contents.items():
        for m in XREF_RE.finditer(txt):
            refs.append({"from_article": art,
                         "target_doc_name": m.group(1),
                         "target_article": m.group(2)})
    return refs


FULLW_DELIM = set("，［］")  # tag 內若有全形分隔符＝寫入端漏網


def check_entries(entries):
    """讀取端 tripwire（§9.3.5）：抓型別/全形汙染。回 (errors, 未enrich清單)。"""
    errs, placeholders = [], []
    for e in entries:
        tags = e.get("tags")
        if not isinstance(tags, list):
            errs.append(f'{e["doc_no"]}: tags 非 list（{type(tags).__name__}，型別汙染）')
        else:
            for t in tags:
                if any(c in FULLW_DELIM for c in t):
                    errs.append(f'{e["doc_no"]}: tag 含全形分隔符 {t!r}')
        if not e.get("summary"):
            errs.append(f'{e["doc_no"]}: summary 缺')
        elif "待 LLM enrich" in e["summary"]:
            placeholders.append(e["doc_no"])
    return errs, placeholders


def build():
    if not SOURCES.exists():
        print(f"找不到 sources/：{SOURCES}", file=sys.stderr)
        sys.exit(1)
    entries = []
    for md in sorted(SOURCES.rglob("*.md")):
        meta, body = parse_frontmatter(md.read_text(encoding="utf-8"))
        if not meta.get("doc_no"):
            print(f"⚠️ 跳過（無 doc_no）：{md}", file=sys.stderr)
            continue
        articles, contents = split_articles(body)
        entries.append({
            "doc_id": f'{meta["doc_no"]}@{meta.get("version", "")}',
            "name": meta.get("name"),
            "doc_no": meta.get("doc_no"),
            "dept": meta.get("dept"),
            "version": meta.get("version"),
            "effective_date": meta.get("effective_date"),
            "expiry_date": meta.get("expiry_date"),
            "classification": meta.get("classification"),
            "source_type": meta.get("source_type"),
            "summary": meta.get("summary"),
            "tags": meta.get("tags", []),
            "articles": articles,
            "cross_refs": extract_xrefs(contents),
            "path": str(md.relative_to(PROJECT_ROOT)).replace("\\", "/"),
        })
    entries.sort(key=lambda e: (e["doc_no"], e["version"] or ""))
    CATALOG.parent.mkdir(parents=True, exist_ok=True)
    CATALOG.write_text(json.dumps(entries, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"✅ catalog.json 已產出：{len(entries)} 筆 → {CATALOG.relative_to(PROJECT_ROOT)}")
    for e in entries:
        xr = f' ｜引用×{len(e["cross_refs"])}' if e["cross_refs"] else ''
        print(f'  - {e["doc_id"]:<14} {e["name"]}（{e["dept"]}）'
              f' 條數={len(e["articles"])} 生效={e["effective_date"]} 失效={e["expiry_date"]}{xr}')

    # 讀取端 tripwire（§9.3.5）：占位＝預期(只報數)；型別/全形汙染＝錯
    errs, placeholders = check_entries(entries)
    if placeholders:
        print(f"ℹ️  未 enrich（summary 占位）：{len(placeholders)} 份")
    if errs:
        print(f"⚠️  結構汙染 {len(errs)} 處：", file=sys.stderr)
        for x in errs:
            print(f"     {x}", file=sys.stderr)
        if "--strict" in sys.argv:
            sys.exit(1)


if __name__ == "__main__":
    build()
