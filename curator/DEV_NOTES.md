# DEV_NOTES — 開發環境筆記（管理辦法小幫手 PoC）

## Gemini 免費層配額（2026-06-26 實測）

> ⚠️ **配額是 per-model、per-day，且各型號額度不同**——**不可假設「每型號都 20」**。
> 確切數字只有兩個可靠來源：① 撞限時的 429 錯誤訊息會明示該型號 `limit:N` ② 查當下官方文件。

| 型號 | 免費層每日配額 | 依據 | 用途 |
|---|---|---|---|
| gemini-2.5-flash | **20 次/天** | 429 明示 `limit:20` | （曾用） |
| gemini-3.5-flash | **20 次/天**（2026-06-27 撞限確認） | 429 明示 `limit:20` | **generate（答題）** |
| gemini-2.0-flash / 2.0-flash-lite | **0（不開放）** | 429 明示 `limit:0` | 不可用 |
| gemini-3.1-flash-lite | 可用，配額未撞（route 較省，累計十餘次未撞） | 探針成功 | **route（路由）** |
| gemini-3-flash-preview | 可用，但 2026-06-27 多次 **503 高需求** | 探針/429 | 備用（不穩） |
| gemini-flash-latest | 可用，確切配額未知 | 探針成功 | 備用 |
| gemini-2.5-flash-lite | 503 暫時過載（非配額問題） | 探針 | 備用 |

## 配額策略
- **route 與 generate 拆用不同型號** → 兩者每日配額互不擠壓（`answer()` 一題 = route×1 + generate×1，分屬兩型號）。
- 一輪完整 eval（A–H＋B2 共 10 題）= route×10 + generate×10。
- `call_gemini()` 對 429 做指數退避；但**每日配額（RPD）耗盡時退避無效**，需換型號或隔日。
- 確切每日配額未完整實測；跑量大時以「撞限錯誤訊息的 `limit` 值」為準。
- 真要穩定高頻（Stage 2 上線/大量 eval）需付費層；免費層僅夠 PoC 低頻開發。

## 攝取作業經驗（2026-06-27，原始文件 → RAG 資料；待整理成正式 SOP）
- **來源判斷別只看「A 開頭」**：law.moj 的 pcode 有 A/N… 多種（勞基法是 N0030001）；lawweb.pcc 才是 FL/GL。`ingest_law.py` 判斷＝「FL/GL → lawweb.pcc，其餘 → law.moj」（曾因誤判把勞基法抓成 0 條）。
- **不同來源不同結構**：law.moj（div：col-no/col-data/line）｜lawweb.pcc 辦法（table：th「第N條」+ ClearCss，`<br>` 是排版斷行非分項）｜lawweb.pcc 要項（th 空、編號「一、」在內容首行）｜pcc.gov.tw content（法規是 **PDF 附件**，需 PDF 管線＝Stage2）｜docx（python-docx 讀 table，合併儲存格會重複，要去連續重複）。
- **條號中文↔阿拉伯要正規化**：法規多阿拉伯「第 22 條」、LLM 答題用中文「第二十二條」；`rag.py _norm_art()` 統一比對，否則 verbatim 抓不到。`build_catalog` ARTICLE_RE 已支援中文/阿拉伯/「第 11-1 條」。
- **source_type 是並陳關鍵**：每份標 `source_type`（公司辦法/政府法令/會議記錄）→ catalog → fetch → 答題標〔來源類型〕→ GEN_SYSTEM 規則 9 並陳公司↔法令。
- **真實 vs 合成混庫會污染路由**：測政府法規時須過濾；正式化應拆 corpus（見架構討論）。
- **call_gemini 退避**：429（配額）與 503（型號高需求）都要退避。

## 其他環境坑
- PyYAML 未裝 → frontmatter 用零依賴手寫 parser（`build_catalog.py`）。
- 中文/emoji 輸出需 `PYTHONIOENCODING=utf-8`（Windows）。
