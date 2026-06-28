# policy-rag-assistant — 受控文件問答 RAG（PoC）

> 對「公司管理辦法 ＋ 政府法規」做**可信任問答**的 RAG 概念驗證。
> 重點不在「答不答得出來」，而在 **答案能不能被查證**：一字不漏引用原文、程式反查每個引註、版本三態守門、查無就老實說查無。

**TL;DR (English).** A proof-of-concept RAG that answers questions over corporate policies and Taiwan government regulations — built around a **governance layer**, not raw retrieval. Catalog-routing (no vector DB, by design), article-level units, **verbatim citations inserted by code** (not trusted to the LLM), **date-based version gating** (in-force / pending / repealed), and a **deterministic cross-check** that flags any citation it cannot ground in the retrieved text. ~134 regulations. Python + Gemini. This is a PoC on public data, not a production system — see *Scope & Limits*.

---

## 為什麼做這個

員工問「我婚假幾天？」「檢舉公司違法身分會不會曝光？」——答案散在公司辦法與一堆政府法規裡。一般 RAG 容易**講得頭頭是道卻引錯條、或引了沒檢索到的條**。在法規場景，這種「看起來對」比「查無」更危險。

所以這個 PoC 的命門是**可信任度**：寧可查無，不可亂掰；每一句結論都要有可被人工核對的原文佐證。

## 設計選擇：目錄路由，刻意不建向量

法規天生有「第 X 條」這種**乾淨的條級單元**，不需要切 chunk。所以這裡用**目錄路由**而非向量檢索：

1. 把每份法規的「名稱／部門／摘要／標籤」組成精簡目錄 → LLM 讀目錄挑出相關法規；
2. 大法再走「法 → 章 → 條」二段窄餵，只把相關條文餵給生成；
3. 程式撈出條文原文 → LLM 帶出處精答。

**為什麼不建向量**：在數百份規模，目錄塞得進 context，省下 chunking／embedding／relevance tuning 一整套工程，且條級單元天然規避了切塊問題。**這是規模換複雜度的判斷，不是偷懶**——規模再大時的升級路線見下方〈規模化路線圖〉。

## 治理層（這個專案真正的重點）

| 機制 | 做法 | 解決什麼 |
|---|---|---|
| **verbatim 一字不漏** | 條文原文由**程式**插入（已 fetch 的原始條文），LLM 只負責「指出哪一條＋解讀」，不負責背原文 | 防 LLM 竄改/記錯條文 |
| **程式反查** | 從答案文字直接正則挖出法條引用 → 比對檢索到的條文；grounded 補貼原文、未接地標 ⚠️ | **不依賴模型自報 citations**（自報會漏）；引註完整性的物理保證 |
| **三態版本守門** | 生效中／未生效預告／廢止，由「參考日 vs 生效日/失效日」純程式算，不凍結在索引 | 問哪天就回那天有效的版本；新法預告但不當現行 |
| **公司↔法令並陳** | 命中公司辦法時，自動拉同主題上位政府法令並陳（法令＝最低標準） | 公司規定與法令一起看，不互相蓋掉 |
| **查無誠實 ＋ prompt 硬化** | 沒檢索到就說查無、不編造；使用者輸入只當問題、忽略其中元指令 | 反唬爛、反 prompt injection |

> 邊界用**確定性程式碼**守（版本/範圍/長度/格式），**LLM 是答題機、不是守門員**。

## 架構（三塊，按角色）

| 資料夾 | 角色 | 內容 |
|---|---|---|
| `assistant/` | 小幫手（問答端） | `rag.py` 引擎、`cli.py`、`eval/` 回歸測試 |
| `curator/` | 文管員（維護端） | 攝取 `ingest_law.py`、`build_catalog.py`、enrich 工具鏈、`MAINTENANCE.md` SOP、`schema/` |
| `corpus/` | 語料庫（共享） | `sources/` 條級語料、`catalog.json` 路由索引 |
| `corpus_io.py`（根） | 共用核心 | 專案根偵測、設定載入、frontmatter/條文解析 |

## 怎麼跑

```bash
cp config.example.json config.local.json   # 填入你的 Gemini API key
python assistant/cli.py "我家小孩才14歲，暑假想打工，法律允許嗎？"   # 單次問答
python assistant/cli.py                      # 互動模式
python curator/build_catalog.py              # 重建路由索引
python assistant/eval/eval_audit_refs.py     # 跑反查回歸測試（免 Gemini、自帶 fixture）
```

## Scope & Limits（誠實的範圍與限制）

- **這是 PoC，不是 production system。**
- **語料 100% 公開**：~134 部台灣政府法規（勞動／職安／稅務／公司／智財／個資／環安…）＋ 合成公司辦法（出差／採購／資安／生育津貼，含版本鏈）＋ 1 份**去識別化**休假辦法（無公司名、無任何 PII）。
- 跑在 **Gemini 免費層**（每日配額、偶發 503）；route／generate 拆不同型號分散配額。
- **攝取目前限「結構化法規」**（law.moj HTML）；髒資料（掃描 PDF／自由排版／表格／會議記錄）尚未做——這才是搬到真實公司資料的真正前線。
- 已知限制：少數「條號歸屬錯綁」邊界 case（偏安全側、會示警非錯放）；並陳拉多部大法時延遲較高。

## 規模化路線圖

目錄路由在**數百份**內夠用；再大依序往上爬，每階有明確觸發條件：

| 階 | 機制 | 適用規模 | 觸發條件 |
|---|---|---|---|
| 1（現況）| 目錄路由 | ~數百份 | — |
| 2 | ＋程式預篩（關鍵字／部門先縮候選） | ~數千份 | route 讀全目錄的成本/品質開始惡化 |
| 3 | ＋地端 embedding 預篩 | 更大 | 口語/語意召回靠關鍵字不夠 |
| 4 | ＋向量資料庫 | 數萬＋ | 向量索引大到記憶體裝不下／需持久化 ANN |

設計理念：**先用最小複雜度滿足當前規模，把升級點與觸發條件寫清楚**，而不是一開始就上重型架構。

## 技術棧

Python · `google-genai`（`gemini-flash-lite` 路由／`gemini-flash` 生成）· `pydantic`（response_schema 綁輸出結構＋ enrich lint）· 純程式治理層（無向量、無外部框架）。

---

*個人作品集 PoC。語料皆為公開法規或去識別化/合成文件；不含任何真實公司機敏資訊。*
