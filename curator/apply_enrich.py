#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""apply_enrich.py — 把 sub-agent 的 enrich 輸出寫回 md（MAINTENANCE §9.2 步驟 4–5）。

吃 JSON {doc_no: {summary, tags}} → lint_enrich 驗證/正規化 → 受控序列化
→ 只替換 frontmatter 的 summary/tags 兩行 → round-trip 斷言。
冪等：只改占位/空 tags 的；已 enrich 的跳過。

用法：python curator/apply_enrich.py <input.json> [--dry-run] [--rebuild]
  --dry-run  只驗證+模擬寫回+round-trip，不落檔（測 pipeline 用）
  --rebuild  全數成功後接著跑 build_catalog.py
"""
import json
import re
import subprocess
import sys
from pathlib import Path

_ROOT = next(p for p in Path(__file__).resolve().parents if (p / "config.example.json").exists())
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))
sys.path.insert(0, str(Path(__file__).resolve().parent))

from corpus_io import SOURCES, parse_frontmatter
from lint_enrich import PLACEHOLDER, validate


def build_doc_index():
    """doc_no -> md Path（掃一次 sources）。"""
    idx = {}
    for md in SOURCES.rglob("*.md"):
        meta, _ = parse_frontmatter(md.read_text(encoding="utf-8"))
        if meta.get("doc_no"):
            idx[meta["doc_no"]] = md
    return idx


def is_placeholder(meta):
    return (PLACEHOLDER in (meta.get("summary") or "")) or not meta.get("tags")


def serialize_tags(tags):
    return "[" + ", ".join(tags) + "]"   # 受控：固定 ASCII 逗號+空格、ASCII 方括號


def apply_one(md, clean_summary, clean_tags):
    """回 new_text；只改 frontmatter 內 summary/tags 兩行（lambda 回傳避免 re 反參照）。"""
    text = md.read_text(encoding="utf-8")
    parts = text.split("---", 2)
    if len(parts) < 3:
        raise ValueError("無 frontmatter")
    fm = parts[1]
    fm, n_s = re.subn(r"(?m)^summary:.*$", lambda m: f"summary: {clean_summary}", fm)
    fm, n_t = re.subn(r"(?m)^tags:.*$", lambda m: f"tags: {serialize_tags(clean_tags)}", fm)
    if n_s != 1 or n_t != 1:
        raise ValueError(f"summary/tags 行數異常 (summary×{n_s}, tags×{n_t})")
    return parts[0] + "---" + fm + "---" + parts[2]


def main():
    args = sys.argv[1:]
    dry = "--dry-run" in args
    rebuild = "--rebuild" in args
    paths = [a for a in args if not a.startswith("--")]
    if not paths:
        print(__doc__)
        sys.exit(1)
    data = json.loads(Path(paths[0]).read_text(encoding="utf-8"))
    idx = build_doc_index()

    written, skipped, failed = [], [], []
    for dn, payload in data.items():
        md = idx.get(dn)
        if not md:
            failed.append((dn, "找不到對應 md"))
            continue
        meta, _ = parse_frontmatter(md.read_text(encoding="utf-8"))
        if not is_placeholder(meta):
            skipped.append((dn, "已 enrich（冪等跳過）"))
            continue
        try:
            cs, ct, warns = validate(payload.get("summary"), payload.get("tags"))
            new_text = apply_one(md, cs, ct)
            rt_meta, _ = parse_frontmatter(new_text)   # round-trip 斷言（dry-run 也驗）
            if rt_meta.get("summary") != cs or rt_meta.get("tags") != ct:
                raise ValueError(f"round-trip 不符 tags={rt_meta.get('tags')!r}")
            if not dry:
                md.write_text(new_text, encoding="utf-8")
            written.append((dn, warns))
        except Exception as e:
            msg = e.errors()[0]["msg"] if hasattr(e, "errors") else str(e).splitlines()[0]
            failed.append((dn, msg))

    head = "[dry-run] " if dry else ""
    print(f"{head}寫入 {len(written)}　跳過 {len(skipped)}　失敗 {len(failed)}")
    for dn, w in written:
        if w:
            print(f"  ⚠️ {dn}: {'; '.join(w)}")
    for dn, r in skipped:
        print(f"  ⊘ {dn}: {r}")
    for dn, r in failed:
        print(f"  ⛔ {dn}: {r}")

    if rebuild and not dry and not failed:
        print("--- 重建 catalog ---")
        subprocess.run([sys.executable, str(Path(__file__).with_name("build_catalog.py"))])
    if failed:
        sys.exit(1)


if __name__ == "__main__":
    main()
