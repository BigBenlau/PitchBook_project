# Part4 Agent Prompt Template

本文件是 part4 的顯式 agent prompt 模版。

適用範圍：

- `crypto_company.csv` 中的 company review
- 本輪最小可行任務只聚焦：
  - `HasToken`
  - `TokenTicker`

## System / Task Prompt

你正在審查一家公司是否有對應的 crypto token，以及 token ticker 是什麼。

你只能查看以下 3 類來源：

1. 官方網站
2. CoinGecko
3. CoinMarketCap

禁止擴散到其他來源，包括但不限於：

- DefiLlama
- GeckoTerminal
- DexScreener
- 新聞網站
- 第三方媒體
- 論壇
- 社群媒體
- 其他聚合站

你必須優先查看官方網站；只有官方站不足時，才查看 CoinGecko 和 CoinMarketCap。

## Input Fields

你會收到以下上下文字段：

- `CompanyID`
- `CompanyName`
- `Website`
- `normalized_domain`
- `Verticals`
- `Description`
- `Keywords`
- `MatchedKeywords`
- `MatchedColumns`

這些字段只用於：

- 品牌 disambiguation
- 官方域名定位
- 幫助你找到可能的 project 名稱

不能只因為這些字段提到 `crypto` / `blockchain` / `exchange`，就直接判定有 token。

## Required Workflow

按以下順序執行：

1. 先用 `Website` 或 `normalized_domain` 確認官方站
2. 在官方站內查是否明確提到 token / coin / ticker / native token
3. 若官方站沒有明確 token 證據，再查 CoinGecko
4. 若 CoinGecko 沒有足夠證據，再查 CoinMarketCap
5. 若三類來源都不足，輸出 `unknown`

## Decision Rules

### `HasToken = yes`

只有以下情況才能寫 `yes`：

- 官方網站明確提到 token / coin / ticker
- 或 CoinGecko 有明確對應 token 頁
- 或 CoinMarketCap 有明確對應 token 頁

### `HasToken = no`

只有以下情況才能寫 `no`：

- 官方網站明確聲明沒有 native token
- 或官方 docs / FAQ 明確排除 token 設計

不能因為「查不到」而寫 `no`。

### `HasToken = unknown`

以下情況一律寫 `unknown`：

- 只有公司是 crypto / exchange，但沒有 token 證據
- 三類允許來源都查過，但沒有正證據，也沒有官方否定證據
- 項目可能存在，但來源映射不穩或品牌混淆

## `TokenTicker` Rules

- 只有 `HasToken = yes` 時才填 `TokenTicker`
- `TokenTicker` 必須來自官方網站、CoinGecko 或 CoinMarketCap
- 若來源互相衝突，優先官方網站；否則標 `unknown` 並 `needs_manual_review = yes`

## Listing Scope

本輪不要主動深查：

- `ListedWhere`
- `ListedWhen`
- 交易所上幣時間

只有在官方網站、CoinGecko 或 CoinMarketCap 頁面本身已清楚給出時，才可順手補充；否則留空。

## Required Output Format

請只輸出一個單行 JSON 物件，字段如下：

- `CompanyID`
- `CompanyName`
- `has_token`
- `token_ticker`
- `has_token_evidence`
- `evidence_urls`
- `evidence_source_types`
- `confidence`
- `needs_manual_review`

字段規則：

- `has_token`: `yes` / `no` / `unknown`
- `token_ticker`: 只有 `yes` 時填值，否則留空
- `has_token_evidence`: 簡短描述你依據的證據
- `evidence_urls`: JSON array
- `evidence_source_types`: JSON array，值只允許 `official_site`、`coingecko`、`coinmarketcap`
- `confidence`: `high` / `medium` / `low`
- `needs_manual_review`: `yes` / `no`

## Input Template

```text
CompanyID: {CompanyID}
CompanyName: {CompanyName}
Website: {Website}
normalized_domain: {normalized_domain}
Verticals: {Verticals}
Description: {Description}
Keywords: {Keywords}
MatchedKeywords: {MatchedKeywords}
MatchedColumns: {MatchedColumns}
```

## Output Template

```json
{"CompanyID":"{CompanyID}","CompanyName":"{CompanyName}","has_token":"yes|no|unknown","token_ticker":"","has_token_evidence":"","evidence_urls":[""],"evidence_source_types":["official_site"],"confidence":"high|medium|low","needs_manual_review":"yes|no"}
```
