---
name: wechat-publisher
description: >
  微信公众号自动化发文工具。支持文章生成、排版美化、草稿创建、素材管理、定时发布。使用当：(1) 用户要求发公众号文章，(2) 用户想生成/发布公众号内容，(3) 用户提到公众号排版、草稿、发布。触发词：公众号、微信发文、公众号发布、公众号排版、weChat publish、wechat article。
---

# WeChat Publisher - 公众号自动化发文

基于微信公众号 API 的自动化发文工具，配合 MIMO V2.5 Pro 生成内容。

## 前置配置

需要在 `~/.openclaw/wechat_config.json` 中配置公众号凭证：

```json
{
  "app_id": "your_app_id",
  "app_secret": "your_app_secret"
}
```

获取方式：微信公众平台 → 开发 → 基本配置

## 快速使用

```bash
# 生成文章并创建草稿
python3 <skill_dir>/scripts/publisher.py draft \
  --title "文章标题" \
  --topic "文章主题/关键词" \
  --style "专业/轻松/幽默"

# 直接用已有内容创建草稿
python3 <skill_dir>/scripts/publisher.py draft \
  --title "文章标题" \
  --content "文章内容（Markdown）"

# 上传封面图
python3 <skill_dir>/scripts/publisher.py cover \
  --image /path/to/image.jpg

# 发布草稿
python3 <skill_dir>/scripts/publisher.py publish \
  --media_id "草稿media_id"

# 定时发布
python3 <skill_dir>/scripts/publisher.py schedule \
  --media_id "草稿media_id" \
  --time "2026-05-10 09:00"

# 查看草稿列表
python3 <skill_dir>/scripts/publisher.py list
```

## 工作流程

1. **内容生成** — MIMO V2.5 Pro 根据主题生成文章（标题、正文、摘要）
2. **排版转换** — Markdown → 公众号富文本格式
3. **创建草稿** — 通过 API 创建草稿到公众号后台
4. **素材管理** — 上传封面图、获取素材列表
5. **发布/定时** — 立即发布或设置定时发布

## 文章风格选项

| 风格 | 说明 |
|------|------|
| `professional` | 专业严谨，适合商务/技术类 |
| `casual` | 轻松活泼，适合生活/娱乐类 |
| `humorous` | 幽默诙谐，适合段子/吐槽类 |
| `story` | 故事叙述，适合案例/经历类 |
| `tutorial` | 教程指南，适合教程/干货类 |

## 输出格式

```json
{
  "status": "success",
  "action": "draft_created",
  "data": {
    "media_id": "xxx",
    "title": "文章标题",
    "url": "预览链接"
  }
}
```

## 注意事项

- 公众号每天推送次数有限（服务号4次/月，订阅号1次/天）
- access_token 有效期 2 小时，脚本会自动刷新
- 图片需要先上传获取 media_id 才能在文章中使用
- 草稿不会自动发布，需要手动调用 publish 或 schedule
