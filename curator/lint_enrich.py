#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""lint_enrich.py — enrich 輸出的驗證 + 正規化（MAINTENANCE §9.3.5 第 1 層）。

寫入嚴格：硬違規拋 ValueError（拒寫該份）；軟問題回 warnings（照寫、標記人工複核）。
依賴 pydantic 2.x（專案已裝）。被 apply_enrich.py 呼叫，也可獨立自測。
"""
import re

from pydantic import BaseModel, field_validator

PLACEHOLDER = "待 LLM enrich"
# tag 內不允許的分隔字元：半形/全形逗號、方括號、冒號 → 出現＝agent 把多 tag 擠成一串或夾帶結構符
TAG_FORBIDDEN = set(",，[]［］:：")
DIGIT_RE = re.compile(r"[0-9０-９%％]")  # 只抓阿拉伯數字/百分比(金額/日數/比率)；中文數字常見於「統一/第三人」故不抓
SUMMARY_BAD_HEAD = '["\'（[／'


class EnrichItem(BaseModel):
    summary: str
    tags: list[str]

    @field_validator("summary", mode="before")
    @classmethod
    def _norm_summary(cls, v):
        if not isinstance(v, str):
            raise ValueError(f"summary 非字串: {type(v).__name__}")
        return re.sub(r"\s+", " ", v).strip()  # 換行/連續空白 → 收斂成單行

    @field_validator("summary")
    @classmethod
    def _check_summary(cls, v):
        if not v:
            raise ValueError("summary 空")
        if PLACEHOLDER in v:
            raise ValueError("summary 仍是占位")
        if len(v) > 100:
            raise ValueError(f"summary 過長 ({len(v)}>100)")
        if v[:1] in SUMMARY_BAD_HEAD:
            raise ValueError(f"summary 開頭可疑字元 {v[:1]!r}（會被 parser 誤判）")
        return v

    @field_validator("tags")
    @classmethod
    def _check_tags(cls, v):
        out, seen = [], set()
        for t in v:
            if not isinstance(t, str):
                raise ValueError(f"tag 非字串: {t!r}")
            t = t.strip()
            if not t:
                continue
            bad = [c for c in t if c in TAG_FORBIDDEN or c == "\n"]
            if bad:
                raise ValueError(f"tag 含非法分隔字元 {bad}: {t!r}")
            if t not in seen:
                seen.add(t)
                out.append(t)
        if len(out) < 3:
            raise ValueError(f"tag 太少 ({len(out)}<3)")
        return out


def validate(summary, tags):
    """回 (clean_summary, clean_tags, warnings)。硬違規拋 ValueError。"""
    item = EnrichItem(summary=summary, tags=tags)
    warnings = []
    if not (8 <= len(item.tags) <= 14):          # 生成目標 8–14；6–14 外只警告不擋
        warnings.append(f"tag 數 {len(item.tags)} 不在建議 8–14")
    if DIGIT_RE.search(item.summary):
        warnings.append("summary 含數值（應零數值，請人工複核）")
    return item.summary, item.tags, warnings


if __name__ == "__main__":
    cases = [
        ("規範勞動條件最低標準，含工資、工時、休假、退休、資遣、職災補償等勞工權益事項。",
         ["勞基法", "勞動基準法", "工資", "工時", "休假", "退休", "資遣", "職災"], "正常"),
        ("第一行\n第二行接續", ["a", "b", "c"], "summary 換行→應收斂單行"),
        ("規範某事項。", ["勞基法，工資", "工時"], "全形逗號 tag→應拋"),
        ("規範某事項。", ["a", "b"], "tag<3→應拋"),
        ("待 LLM enrich", ["a", "b", "c"], "占位→應拋"),
        ("規範雇主應於 30 日內辦理之事項。", ["a", "b", "c", "d"], "含數值→警告不擋"),
    ]
    for s, t, desc in cases:
        try:
            cs, ct, w = validate(s, t)
            print(f"[{desc}] ✅ summary={cs!r}")
            print(f"        tags={ct}  warn={w}")
        except Exception as e:
            print(f"[{desc}] ⛔ {str(e).splitlines()[0] if not hasattr(e,'errors') else e.errors()[0]['msg']}")
