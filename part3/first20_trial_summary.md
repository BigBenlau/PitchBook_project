# 前 20 間公司試跑摘要

資料來源：
- `part2_build_crypto_candidate/output/crypto_company.csv`

本摘要已按新的 part3 判斷口徑修正。

## 修正後的核心原則

- `crypto 相關公司` 不等於 `有 token`
- `交易所` 不等於 `有發幣`
- 找不到 token 證據時，應標 `unknown`，不是 `no`
- 所有 `yes / no` 都應帶可檢查來源

## 前 20 間的整體觀察

- 大部分公司仍然是 relation 欄位帶進來的疑似誤抓
- 真正值得繼續查的只有少數
- 這說明 part3 必須先做主表快篩，再決定是否交 agent

## 需要保留的樣本

### Zebpay

- 可確認是 crypto 相關公司
- 可合理視為有對應的 crypto product / exchange project
- 但目前沒有足夠證據支持：
  - `HasToken = yes`
  - 或 `HasToken = no`

因此目前較合理的口徑是：

- `IsCryptoRelatedCompany = yes`
- `HasCryptoProject = yes`
- `HasToken = unknown`

參考來源：
- `https://www.zebpay.com/`
- `https://coinmarketcap.com/exchanges/zebpay/`

### Zikto / Insureum

- 目前仍是前 20 間裡最明確的 token 案例
- 可確認對應 project：`Insureum`
- 可確認 token ticker：`ISR`
- 可確認至少部分上市資訊

參考來源：
- `https://insureum.medium.com/introducing-insureum-the-blockchain-based-insurance-protocol-97991d22b2c3`
- `https://insureum.medium.com/insureums-4th-listing-bitforex-4f6b249d6957`
- `https://coinone.co.kr/info/notice/832`

### Streembit

- 主表與公開資料支持它是 blockchain / decentralized project
- 但 token 與 listing 證據還不夠
- 這家公司適合進下一輪 agent 深查

參考來源：
- `https://zovolt.com/`
- `https://streembit.github.io/`
- `https://docs.streembit.co/`

## 本輪方法上的問題與修正

### 問題 1

之前的快篩規則過度依賴 relation 命中，容易把普通公司一起帶進來。

修正：

- 快篩只拿主表欄位決定優先級
- relation 命中只作召回，不作最終判斷

### 問題 2

之前對 Zebpay 的口徑過快把「交易所」延伸成 token 結論。

修正：

- `exchange` 只支持 `crypto related` 或 `has project`
- 不支持 `has token`

### 問題 3

之前的部分否定結論其實是「沒找到證據」，不是「有反證」。

修正：

- part3 最終輸出必須強制保留 `unknown`
- 沒有證據時，不再寫 `no`

## 本輪結論

part3 應改成：

1. 主表快篩只做優先級，不做過度判斷
2. `crypto company`、`crypto project`、`token`、`listing` 分開查
3. 所有確認與否認都必須帶證據 URL
4. 找不到證據時，統一標 `unknown`
