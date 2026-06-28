# metadata schema — 管理辦法小幫手（治理層權威）

> 鎖定日：2026-06-26。**改任何欄位都會 ripple 全鏈（catalog → 路由 → 檢索 → 答題）**，動前先想清楚。
> 每份辦法檔（`corpus/sources/<子夾>/*.md`）開頭以 YAML frontmatter 攜帶本 schema。

## 欄位定義

| key（程式） | 中文 | 型別 | 必填 | 說明 |
|---|---|---|---|---|
| `name` | 名稱 | str | ✅ | 辦法全名（值用中文） |
| `doc_no` | 文號 | str | ✅ | 業務識別碼，如 HR-002。**版本鏈共用同一 doc_no** |
| `dept` | 部門 | str | ✅ | = 物理子夾、權限邊界、**單一歸屬** |
| `version` | 版本 | str | ✅ | 帶引號防數字截斷（`"2.0"`） |
| `effective_date` | 生效日 | str(ISO) | ✅ | 版本守門起點 |
| `expiry_date` | 失效日 | str(ISO)/null | ✅ | null=仍生效；新版公告時設舊版 = 新版生效日 − 1 |
| `classification` | 機密等級 | enum | ✅ | 公開 / 內部 / 機密（order：公開 0 < 內部 1 < 機密 2） |
| `summary` | 摘要 | str | ✅ | **路由線索、只找不答**；給「類別＋代表物＋動作」三鉤子，**零具體數值** |
| `tags` | 標籤 | list | ✅ | 邏輯分類、**可跨/多標籤**；不窮舉、配 `_tags.md` 同義詞擴展 |
| `status_label` | 狀態標籤 | str | — | **純人讀**；catalog 與守門**不信此欄**、一律用日期推導 |

## 三態守門（★命門，由查詢時的參考日 D 動態算，catalog 不凍結）

- **生效中**：`effective_date ≤ D < expiry_date`（expiry 為 null 視為 +∞）
- **已公告未生效**：`effective_date > D` → 不作答金額、但**主動預告**生效日
- **已廢止**：`expiry_date ≤ D` → 排除（除非明確問歷史）

D 預設今天（系統時鐘），可被問題裡的日期覆蓋（如「7 月後…」）。

## 兩條鐵則（為什麼這樣設計）

1. **摘要/tags 零 specific fact**：金額/日數/門檻全留原文條文。摘要寫數值會**短路版本守門**（LLM 直接讀摘要作答、跳過日期過濾）。
2. **版本區分是日期欄位的職責、不是摘要的職責**：同辦法兩版摘要相同是**正確**的（靠 `effective_date`/`expiry_date` + 參考日選版）。
