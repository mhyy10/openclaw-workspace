---
name: scrapegraph
description: >
  AI-powered web scraping using ScrapeGraphAI + MIMO V2.5 Pro. Extract structured data from any webpage with natural language prompts. Use when: (1) user asks to scrape/crawl/extract data from a URL, (2) user wants to parse webpage content into JSON/structured format, (3) user mentions web scraping, data extraction, or crawling tasks. Triggers: "爬取", "抓取", "爬虫", "scrape", "extract from URL", "crawl", "抓数据", "提取网页".
---

# ScrapeGraphAI - AI 智能爬虫

基于 ScrapeGraphAI + MIMO V2.5 Pro 的智能网页数据提取工具。

## 快速使用

```bash
python3 <skill_dir>/scripts/scraper.py "<URL>" "<提取任务描述>" [-o output.json]
```

参数：
- `URL` — 目标网页地址
- 提取任务 — 用自然语言描述要提取什么数据
- `-o, --output` — 可选，结果保存为 JSON 文件

## 示例

```bash
# 提取新闻
python3 <skill_dir>/scripts/scraper.py "https://news.example.com" "提取前10条新闻标题和摘要"

# 提取产品信息
python3 <skill_dir>/scripts/scraper.py "https://shop.example.com" "提取商品名、价格、评分" -o products.json

# 提取名言/引语
python3 <skill_dir>/scripts/scraper.py "https://quotes.toscrape.com" "提取前5条名言、作者和标签"
```

## 工作流程

1. **抓取网页** — 使用 requests 获取 HTML（自动处理编码）
2. **提取文本** — 清理 HTML 标签，保留可读文本
3. **AI 提取** — MIMO V2.5 Pro 根据 prompt 提取结构化数据
4. **输出结果** — 返回 JSON 格式，可选保存到文件

## 输出格式

```json
{
  "url": "目标URL",
  "prompt": "提取任务",
  "result": { ... },
  "reasoning": "MIMO推理过程",
  "metadata": {
    "model": "mimo-v2.5-pro",
    "tokens": { ... },
    "elapsed_seconds": 14.7
  }
}
```

## 注意事项

- 使用小米官方 API（自动从 OpenClaw 配置读取）
- MIMO 是推理模型，会消耗 reasoning_tokens
- 沙箱环境部分外网受限，本地运行效果更好
- 对于需要 JavaScript 渲染的页面，文本提取可能不完整
