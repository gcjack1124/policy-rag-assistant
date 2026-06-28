# MAINTENANCE.md — 管理辦法小幫手 RAG 維護作業規範（文管員）

> **本檔給「維護者」**（人 或 agent）：負責把新文件攝取進 RAG、重建 catalog、維護 log。
> **不是**問答小幫手的答題規範（那在 `assistant/rag.py` 的 `GEN_SYSTEM`）。
> 維護本專案前先讀本檔；維護完回來更新 log（必要時更新本檔）。

## 0. 三塊與資料流
- `corpus/`＝共享資產（語料 + catalog + refs_law）；`assistant/`＝問答；`curator/`＝你（維護工具+規範）。
- 路徑與解析集中於專案根 `corpus_io.py`（`PROJECT_ROOT / SOURCES / CATALOG / REFS_LAW` + `parse_frontmatter` / `split_articles`）。**改路徑只改這裡。**
- 資料流：原始文件 →（`ingest_law.py` 或手工）→ `corpus/sources/<子夾>/*.md`（frontmatter + 條文）→ `build_catalog.py` → `corpus/catalog.json` → 小幫手讀。

## 1. 攝取決策樹（拿到文件先判斷類型）

| 來源 | 判斷 | 流程 |
|---|---|---|
| **law.moj 法規**（pcode A/N…）| `law.moj.gov.tw/…?pcode=…` | `curl` 存 HTML → `python curator/ingest_law.py <html> <pcode>` |
| **lawweb.pcc 法規**（id FL/GL）| `lawweb.pcc.gov.tw/…?id=…` | 同上，`ingest_law.py` 自動走 table parser |
| **docx 公司文件** | 你給的 .docx | python-docx 讀（合併儲存格要去連續重複）→ 手工整理成條級 md |
| **PDF**（如 pcc.gov.tw content 附件）| 法規是 PDF 下載 | ⚠️ Stage 2 PDF 管線（pdf-extract + 可能 OCR），**目前未做** |
| **會議記錄** | 決議/案由（非條文）| ⚠️ **待設計**（決議單元，非「第X條」）|

★ `ingest_law.py` 來源判斷＝「**FL/GL 開頭 → lawweb.pcc；其餘（A/N…）→ law.moj**」。別用「A 開頭」判斷（會漏 N 開頭的勞基法）。

## 2. 黃金樣本（照已做的改，別從零想）

| 範本 | 檔 | 示範 |
|---|---|---|
| law.moj div 結構 | `corpus/sources/政府法規/政府採購法.md` | 阿拉伯條號、章節 |
| lawweb.pcc 要項類 | `corpus/sources/政府法規/採購契約要項.md` | 「一、二、」編號 |
| docx 公司文件 | `corpus/sources/HR_人資/勞工休假及請假規定一覽表.md` | 表格→條級、**法源欄→法源依據** |

## 3. metadata 規範
- 欄位定義以 `curator/schema/_schema.md` 為準（必填：name/doc_no/dept/version/effective_date/expiry_date/classification/summary/tags）。
- **`source_type`（並陳關鍵）**：`公司辦法` / `政府法令` / `會議記錄`。決定答題時是否並陳公司↔法令（見 GEN_SYSTEM 規則 9）。
- **命名**：doc_no（公司自訂 HR-/GA-/IT-；法規用 pcode/id）；子夾＝部門 或 政府法令/政府法規；`source_url`（外部來源）、`source_file`（本地原檔，相對專案根）。
- **法源依據**：公司辦法若有對應上位法令，在條文標【法源】（如休假表），答題會沿法源並陳。
- summary/tags：給「類別+代表物+動作」鉤子，不窮舉；可手寫或 LLM enrich。

## 4. 條號 / 結構處理
- 條號正規化：中文「第二十二條」≡ 阿拉伯「第 22 條」（`corpus_io.ARTICLE_RE` + `rag._norm_art`）。md 內中/阿皆可，但**同一份要一致**。
- ★**條標題判定**：`ARTICLE_RE` 要求條號後接「空白或行尾」(`(?=\s|$)`)。否則內文裡行首的交叉引用（如「第十七條規定於本條…準用之」）會被誤切成新條、且吃掉前一條結尾（2026-06-27 修，曾全語料誤切 167 條）。新來源若條標題與內文同行緊貼，需先正規化。
- 要項類「一、二、」：`ingest_law` 自動轉內部條號；docx 手工整理時用「第 N 條　<假別/標題>」當錨點讓 build_catalog 切。

## 5. catalog 重建（改 sources 後【必跑】）
```
python curator/build_catalog.py
```
- 檢查條數與原文對照合理（曾出現 ingest 98 / build_catalog 102 的差異，要查根因）。
- catalog **不凍結三態**（生效中/廢止由查詢參考日算），只存 effective/expiry 原值。

## 6. log 維護規範（每次攝取/異動【記一筆】）
`curator/log.md` 加一列 `| 日期 | 操作 | 說明 |`。例：`| 2026-06-27 | 攝取勞基法 | N0030001，98 條，source_type=政府法令 |`。

## 7. 驗收（攝取後）
- 重建 catalog 成功、條數合理。
- 跑一題相關 query（`python assistant/cli.py "…"`）確認路由命中 + verbatim 讀得到原文。
- **三鐵則：一字不漏 / 不竄改法條 / 查無誠實**。能驗的入 `assistant/eval/`。
  - `eval_audit_refs.py`：程式反查（簡稱/指代解析 + 安全閘）回歸測試，**自帶 fixture、免 Gemini**，直接 `python assistant/eval/eval_audit_refs.py`（改 `rag._audit_prose`/`_resolve_doc` 後必跑）。
  - `sim_generate.py`：Gemini 配額耗盡/503 時，不靠 Gemini 測 generate 端的模擬 harness（`build` → 派 sub-agent 當 generate 替身 → `render`；★替身禁用先驗知識，反作弊）。

## 8. 環境 / 配額
見 `curator/DEV_NOTES.md`（Gemini 免費層各型號每日配額、route/generate 拆型號、`PYTHONIOENCODING=utf-8`）。

## 9. enrich SOP（攝取後補路由摘要 summary / tags）

> **enrich 是文管員常態工作**：把攝取時留占位的 `summary`/`tags` 填成真值。
> ⚠️ **不 call Gemini**——這是「讀法條重點→寫摘要+tags」的純文字任務，由文管員**派 Claude sub-agent** 生成，**不受 Gemini 免費層配額限制**（Gemini 只用於 runtime route/generate）。**模型＝Sonnet**（成本約 Opus 1/5，夠用；品質不滿意再個案升 Opus）。

### 9.1 觸發 / 冪等
- 每次攝取新法規後（ingest 產出必為占位）。待 enrich＝`summary` 含「待 LLM enrich」**或** `tags` 為空 `[]`。
- **只填空白、不覆蓋**（已手寫/已 enrich 的不動）→ 可重跑。

### 9.2 流程（6 步）
1. **掃清單**：`sources/**/*.md` 挑占位/空 tags。
2. **抽素材（★不讀全文）**：每份只餵 `name`＋`法規類別`＋章節標題（`##` 行）＋**第 1 條**（立法目的）。公司法 568 條也只餵這幾行。
3. **派 sub-agent 並行**：`⌈份數/20⌉` 個 Sonnet **同時**跑、各 20 份；回結構化 JSON `{doc_no:{summary,tags}}`，**不手寫 frontmatter**。
4. **★Lint 閘門**（§9.3）：`apply_enrich.py` 過 `lint_enrich` 驗證+正規化 → 受控序列化 → round-trip 斷言；不過拒寫該份。
5. **寫回**：只替換 md 的 `summary:`／`tags:` 兩行，不碰其他 metadata、不碰本文。
6. **`build_catalog.py` → 驗收（§9.4）→ `log.md` 記一筆**。

### 9.3 生成規則 + Lint 閘門（繼承 _schema.md 鐵則）

**生成（sub-agent）**：
- `summary`：一句、40–70 字、句式「規範〔對象〕，含〔代表事項〕等〔領域〕事項。」；給「類別＋代表物＋動作」三鉤子；**★零具體數值**（金額/日數/比率/門檻留原文，寫進摘要會短路版本守門）。黃金樣本 `政府採購法.md`。
- `tags`：**生成目標 8–14 個**，涵蓋①法規領域②核心概念③**法規俗名/簡稱**（勞基法/個資法…路由常靠俗名命中）④口語對應詞；不窮舉、不含數值。`_tags.md` 不主動窮舉，靠 eval 命中率驅動才補。
- **版本鐵則**：同 doc_no 多版本摘要相同是對的（版本靠日期欄）。

**Lint 閘門（`lint_enrich.py` + `apply_enrich.py`，pydantic 2.x）**——因 `parse_frontmatter` 脆弱（全形逗號→一顆大 tag、全形括號→tags 變字串、換行→截斷；`json.dumps` 不報錯＝silent corruption），三層防護：
1. **驗證+正規化**：summary 收斂單行、非占位、≤100 字、不得以 `[ " ' （ ／` 開頭（內文全形標點保留）；tags 為 `list[str]`、strip+dedup、每 tag 不得含分隔符 `, ， [ ] ［ ］ : ：`/換行、至少 3 個（**6–14 外只 warning 不擋**）；summary 含阿拉伯數字 → warning。硬違規拋錯拒寫。
2. **受控序列化**：腳本固定吐 ASCII `[a, b, c]`+單行 summary，**分隔符 LLM 永遠碰不到**。
3. **round-trip 斷言**：寫回後立即 reparse，比對 tags/summary 一致才算過，否則 rollback。
- **讀取端＝偵測報錯、不靜默容忍**：`build_catalog.py` 內建 tripwire，tags 非乾淨 list／含全形分隔符 → 印 ⚠️（`--strict` exit 1）；占位只報數不當錯。連手改/未來來源也有保險。**口訣：寫入嚴格、讀取大聲。**

### 9.4 驗收（enrich 後）
無占位殘留、無空 tags（`build_catalog.py --strict` 掃）；抽查 5–10 份 summary 無數值、tags 含俗名；跑 2–3 題**口語化** query 確認語意路由命中（點名法規的 query 占位時本就會中，測不出 enrich 效果）；能固化的入 `assistant/eval/`。

### 9.5 工具
- `curator/lint_enrich.py`：pydantic 模型 + 正規化，`validate(summary,tags)->(清洗值, warnings)|拋錯`。
- `curator/apply_enrich.py <input.json> [--dry-run] [--rebuild]`：吃 JSON→lint→受控序列化寫回→round-trip；冪等；`--dry-run` 只驗不落檔；`--rebuild` 全成功後接 build_catalog；失敗份列尾不中斷其餘。
- `curator/build_catalog.py [--strict]`：讀取端 tripwire（§9.3）。

### 9.6 enrich 不得觸碰的 invariants（也供未來改 ingest/parser 自檢）
1. **`articles` 只存條號清單、零內文**（內文留實體 md、fetch 才讀；保 catalog 輕量省路由 token）。
2. **「條之幾」存連字號字串**（第9條之1 → `第 9-1 條`，**不可**轉 `9.1`，會與「第9條第1項」混淆）。
3. **來源轉換須正規化條號**：`ARTICLE_RE` 認 `第 9-1 條`、**不認** `第9條之1`；新來源（docx 手key/他站）導入時條號須先轉連字號式，否則 `split_articles` 漏切。
4. **三態不凍結**：catalog 只存 effective/expiry 原值，狀態由查詢時參考日算。

## 10. 二段路由（assistant 側）依賴的 curator 資料

> 非 curator 操作，但 assistant 的「法→章→條」二段路由（`rag.narrow_fetched`，破萬字大法窄餵省 token）**靠 curator 維護的資料品質**，攝取時要顧：

- **章節結構**：靠 md 的 `## 章名` 行切章（`corpus_io.split_chapters`，查詢時讀、不進 catalog）。攝取時章節要完整（law.moj 的 h3 char-2 → ingest 寫成 `##`）。無 `##` 的單層條文法 → 二段路由自動退回整餵。
- **條號乾淨**（呼應 §9.7）：route2b 選條、程式反查都以條號為鍵；同份條號中/阿混用或重複會讓窄餵與反查比對失準。（2026-06-27 已治本：`ARTICLE_RE` 加 `(?=\s|$)`，條號後須接空白/行尾才算條標題，一次清掉全語料 45 份共 167 個「內文交叉引用被誤切」的假條，見 §4。）
- **閾值**：config `narrow_threshold`（預設 30，見 `rag.NARROW_THRESHOLD`）以下整餵、以上才窄餵。
- 流程細節見 `assistant/rag.py` docstring。

---
> **未來接縫（YAGNI，先不建）**：規模大到目錄塞不下需加**向量架構**時，於本檔新增一節、不另開資料夾；有**第二個小幫手**（各部門）時，再把 `assistant/curator/corpus` 抽成頂層多 instance。
