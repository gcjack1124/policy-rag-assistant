#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
corpus_io.py — 專案根共用模組（assistant 小幫手 + curator 文管員 都 import）

集中：專案根偵測、config 載入、語料路徑常數、frontmatter / 條文解析。
★搬資料夾後，路徑只在這裡定義一次，避免各腳本各自寫死 ROOT。
"""
import json
import re
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent   # corpus_io.py 位於專案根
CORPUS = PROJECT_ROOT / "corpus"                  # Stage 2 若改指外部文件庫，改這裡或從 config 讀
SOURCES = CORPUS / "sources"
CATALOG = CORPUS / "catalog.json"
REFS_LAW = CORPUS / "refs_law"


def load_config():
    cfg_path = PROJECT_ROOT / "config.local.json"
    if not cfg_path.exists():
        raise FileNotFoundError(
            "找不到 config.local.json。請複製 config.example.json 為 config.local.json 並填入 gemini_api_key。"
        )
    return json.loads(cfg_path.read_text(encoding="utf-8"))


# ── 解析（建索引 build_catalog 與取原文 rag.fetch 共用）────────────
ARTICLE_RE = re.compile(r'^(第\s*[一二三四五六七八九十百千\d]+(?:-\d+)?\s*條)(?=\s|$)')
# ↑ 條號後須接「空白或行尾」才算條標題；防止內文交叉引用（如「第十七條規定…」）被誤切成新條。
XREF_RE = re.compile(r'依(.{2,20}?辦法)(第[一二三四五六七八九十百]+條)')


def parse_frontmatter(text):
    """解析前兩個 --- 之間的扁平 YAML 子集。回傳 (meta_dict, body)。"""
    if not text.startswith('---'):
        return {}, text
    parts = text.split('---', 2)
    if len(parts) < 3:
        return {}, text
    fm, body = parts[1], parts[2]
    meta = {}
    for line in fm.splitlines():
        if not line.strip() or ':' not in line:
            continue
        key, _, val = line.partition(':')
        key, val = key.strip(), val.strip()
        if val in ('null', ''):
            meta[key] = None
        elif val.startswith('[') and val.endswith(']'):
            inner = val[1:-1].strip()
            meta[key] = [x.strip() for x in inner.split(',')] if inner else []
        else:
            if (val[:1] == '"' and val[-1:] == '"') or (val[:1] == "'" and val[-1:] == "'"):
                val = val[1:-1]
            meta[key] = val
    return meta, body


def split_articles(body):
    """按「第X條」切條。回傳 (條號清單, {條號: 內文})。"""
    articles, contents = [], {}
    current, buf = None, []
    for line in body.splitlines():
        m = ARTICLE_RE.match(line.strip())
        if m:
            if current:
                contents[current] = '\n'.join(buf).strip()
            current = m.group(1)
            articles.append(current)
            buf = [line.strip()]
        elif current:
            buf.append(line)
    if current:
        contents[current] = '\n'.join(buf).strip()
    return articles, contents


def split_chapters(body):
    """按「## 章名」切章，回傳 [{title, arts:[條號...]}]（條號與 split_articles 一致）。
    無章節的法 → 回單筆 {title: None, arts: 全部條}，供二段路由判斷「不可再切章」。"""
    chapters = []
    current = {"title": None, "arts": []}
    for line in body.splitlines():
        s = line.strip()
        if s.startswith('## '):
            if current["title"] is not None or current["arts"]:
                chapters.append(current)
            current = {"title": s[3:].strip(), "arts": []}
        else:
            m = ARTICLE_RE.match(s)
            if m:
                current["arts"].append(m.group(1))
    chapters.append(current)
    return [c for c in chapters if c["arts"]]
