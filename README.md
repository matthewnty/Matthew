# Matthew

## Stock news tracking flow (US social buzz stocks like GME)

### 1) Goal
Track high-attention US stocks (for example: GME, AMC, TSLA) from social/news signals every day, then send links to Discord and/or Signal.

### 2) Suggested daily flow
1. **Collect symbols to watch**
   - Static watchlist: GME, AMC, TSLA, NVDA, etc.
   - Dynamic social buzz: Reddit (r/wallstreetbets), X/Twitter trend feeds, market-news APIs.
2. **Pull news + social posts**
   - Use APIs (for example: Finnhub, NewsAPI, Alpha Vantage, Reddit API).
   - Filter by ticker, keyword, language, and last 24 hours.
3. **Rank and deduplicate**
   - Score by mentions/upvotes/engagement + recency.
   - Remove duplicate links and low-quality sources.
4. **Generate summary**
   - Output top N items per stock:
     - Headline
     - Source
     - Short reason (why trending)
     - Link
5. **Send to channels**
   - **Discord**: send message through Discord webhook.
   - **Signal**: send via `signal-cli` (or a bridge service) if your setup supports it.
6. **Schedule**
   - Run once daily (for example 9:00 AM ET) and optionally an evening update.

### 3) Can GitHub internal functions automate this?
Yes, mostly with **GitHub Actions**:
- Use a **scheduled workflow** (`cron`) to run daily.
- Store API keys/webhooks in **GitHub Secrets**.
- Run script in Actions to fetch/rank/summarize.
- Post directly to **Discord webhook** from the workflow.

**Signal note:** GitHub Actions does not provide native Signal integration.
You can still do it with an external bridge or self-hosted runner + `signal-cli`.

---

## 廣東話版本（Cantonese）

### 1) 目標
每日追蹤美股入面喺社交媒體同新聞好多人講嘅股票（例如 GME、AMC、TSLA），再將連結發去 Discord / Signal，方便你喺同一個 channel 跟進。

### 2) 建議流程（每日）
1. **準備監察股票清單**
   - 固定名單：GME、AMC、TSLA、NVDA 等
   - 動態熱門股：Reddit（r/wallstreetbets）、X/Twitter 熱門趨勢、財經新聞 API
2. **抓取新聞同社交貼文**
   - 用 API（例如 Finnhub、NewsAPI、Alpha Vantage、Reddit API）
   - 以股票代號／關鍵字／語言／24 小時內做篩選
3. **排序同去重**
   - 按提及次數、upvote、互動量同時間新鮮度做評分
   - 去除重複 link 同低質來源
4. **整理摘要**
   - 每隻股票輸出 Top N：
     - 標題
     - 來源
     - 點解會熱（簡短原因）
     - 連結
5. **發送去通知渠道**
   - **Discord**：用 Discord webhook 發送
   - **Signal**：用 `signal-cli` 或 bridge（視乎你嘅環境）
6. **排程**
   - 每日固定時間跑一次（例如美東早上 9 點），可加黃昏更新

### 3) GitHub 內置功能可唔可以做到自動化？
**可以，大部分可以用 GitHub Actions 完成：**
- 用 `cron` 做每日排程
- 用 GitHub Secrets 儲存 API key / webhook
- 用 workflow script 做抓取、排序、摘要
- 直接發去 Discord webhook

**Signal 補充：**GitHub 本身冇內置 Signal 通知整合。
要發 Signal 通常要靠外部 bridge，或者 self-hosted runner 配 `signal-cli`。
