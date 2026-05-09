#!/usr/bin/env python3
"""
WeChat Publisher - 微信公众号自动化发文工具

用法:
  python3 publisher.py draft --title "标题" --topic "主题"
  python3 publisher.py draft --title "标题" --content "内容"
  python3 publisher.py cover --image /path/to/image.jpg
  python3 publisher.py publish --media_id "xxx"
  python3 publisher.py schedule --media_id "xxx" --time "2026-05-10 09:00"
  python3 publisher.py list
"""

import os
import sys
import json
import time
import argparse
import requests
from pathlib import Path
from typing import Optional, Dict, Any, List


# ========== 配置 ==========

CONFIG_PATH = Path.home() / ".openclaw" / "wechat_config.json"
OPENCLAW_CONFIG = Path.home() / ".openclaw" / "openclaw.json"

API_BASE = "https://api.weixin.qq.com/cgi-bin"


def load_wechat_config() -> Dict[str, str]:
    """加载公众号配置"""
    if not CONFIG_PATH.exists():
        raise FileNotFoundError(
            f"找不到配置文件: {CONFIG_PATH}\n"
            f"请创建配置文件，格式：\n"
            f'{{"app_id": "your_app_id", "app_secret": "your_app_secret"}}'
        )
    
    with open(CONFIG_PATH) as f:
        cfg = json.load(f)
    
    if not cfg.get("app_id") or not cfg.get("app_secret"):
        raise ValueError("配置文件缺少 app_id 或 app_secret")
    
    return cfg


def load_mimo_config() -> Dict[str, str]:
    """从 OpenClaw 配置加载小米 API"""
    if not OPENCLAW_CONFIG.exists():
        raise FileNotFoundError(f"找不到 OpenClaw 配置: {OPENCLAW_CONFIG}")
    
    with open(OPENCLAW_CONFIG) as f:
        cfg = json.load(f)
    
    xiaomi = cfg.get("models", {}).get("providers", {}).get("xiaomi", {})
    if not xiaomi or not xiaomi.get("apiKey"):
        raise ValueError("未找到小米 API 配置")
    
    return {
        "api_key": xiaomi["apiKey"],
        "base_url": xiaomi["baseUrl"].rstrip("/"),
        "model": "mimo-v2.5-pro"
    }


# ========== 微信 API ==========

class WeChatAPI:
    """微信公众号 API 封装"""
    
    def __init__(self, app_id: str, app_secret: str):
        self.app_id = app_id
        self.app_secret = app_secret
        self._access_token = None
        self._token_expires = 0
    
    def get_access_token(self) -> str:
        """获取 access_token（自动缓存和刷新）"""
        if self._access_token and time.time() < self._token_expires:
            return self._access_token
        
        url = f"{API_BASE}/token"
        params = {
            "grant_type": "client_credential",
            "appid": self.app_id,
            "secret": self.app_secret
        }
        
        resp = requests.get(url, params=params, timeout=10)
        data = resp.json()
        
        if "access_token" not in data:
            raise RuntimeError(f"获取 access_token 失败: {data}")
        
        self._access_token = data["access_token"]
        self._token_expires = time.time() + data.get("expires_in", 7200) - 300
        
        return self._access_token
    
    def create_draft(self, title: str, content: str, author: str = "", digest: str = "", 
                     thumb_media_id: str = "") -> Dict[str, Any]:
        """创建草稿"""
        token = self.get_access_token()
        url = f"{API_BASE}/draft/add?access_token={token}"
        
        # 构建图文消息
        article = {
            "title": title,
            "author": author,
            "digest": digest,
            "content": content,
            "content_source_url": "",
            "need_open_comment": 0,
            "only_fans_can_comment": 0
        }
        
        if thumb_media_id:
            article["thumb_media_id"] = thumb_media_id
        
        payload = {"articles": [article]}
        
        resp = requests.post(url, json=payload, timeout=30)
        return resp.json()
    
    def upload_thumb(self, image_path: str) -> Dict[str, Any]:
        """上传封面图（临时素材）"""
        token = self.get_access_token()
        url = f"{API_BASE}/media/upload?access_token={token}&type=image"
        
        with open(image_path, "rb") as f:
            files = {"media": (Path(image_path).name, f, "image/jpeg")}
            resp = requests.post(url, files=files, timeout=30)
        
        return resp.json()
    
    def upload_permanent_image(self, image_path: str) -> Dict[str, Any]:
        """上传永久图片素材"""
        token = self.get_access_token()
        url = f"{API_BASE}/material/add_material?access_token={token}&type=image"
        
        with open(image_path, "rb") as f:
            files = {"media": (Path(image_path).name, f, "image/jpeg")}
            resp = requests.post(url, files=files, timeout=30)
        
        return resp.json()
    
    def publish(self, media_id: str) -> Dict[str, Any]:
        """发布草稿"""
        token = self.get_access_token()
        url = f"{API_BASE}/freepublish/submit?access_token={token}"
        
        payload = {"media_id": media_id}
        resp = requests.post(url, json=payload, timeout=30)
        return resp.json()
    
    def get_draft_list(self, offset: int = 0, count: int = 20) -> Dict[str, Any]:
        """获取草稿列表"""
        token = self.get_access_token()
        url = f"{API_BASE}/draft/batchget?access_token={token}"
        
        payload = {"offset": offset, "count": count, "no_content": 0}
        resp = requests.post(url, json=payload, timeout=30)
        return resp.json()
    
    def delete_draft(self, media_id: str) -> Dict[str, Any]:
        """删除草稿"""
        token = self.get_access_token()
        url = f"{API_BASE}/draft/delete?access_token={token}"
        
        payload = {"media_id": media_id}
        resp = requests.post(url, json=payload, timeout=30)
        return resp.json()
    
    def get_material_count(self) -> Dict[str, Any]:
        """获取素材总量"""
        token = self.get_access_token()
        url = f"{API_BASE}/material/get_materialcount?access_token={token}"
        
        resp = requests.get(url, timeout=10)
        return resp.json()


# ========== MIMO 内容生成 ==========

def generate_article(topic: str, title: str = "", style: str = "professional", 
                     mimo_config: Dict[str, str] = None) -> Dict[str, str]:
    """用 MIMO V2.5 Pro 生成文章"""
    
    style_prompts = {
        "professional": "专业严谨、逻辑清晰、数据支撑",
        "casual": "轻松活泼、口语化、贴近生活",
        "humorous": "幽默诙谐、段子手风格、有趣有料",
        "story": "故事叙述、引人入胜、有代入感",
        "tutorial": "教程指南、步骤清晰、干货满满"
    }
    
    style_desc = style_prompts.get(style, style_prompts["professional"])
    
    prompt = f"""请为公众号写一篇文章。

主题：{topic}
{f'标题：{title}' if title else '请自拟一个吸引人的标题'}
风格：{style_desc}

要求：
1. 标题要吸引人，适合公众号传播
2. 开头要有 hook，吸引读者继续看
3. 内容结构清晰，有小标题分段
4. 结尾要有总结或引导互动
5. 字数 800-1500 字
6. 用 Markdown 格式

请返回 JSON 格式：
{{
  "title": "文章标题",
  "digest": "摘要（50字以内）",
  "content": "文章内容（Markdown格式）",
  "author": "作者名（可选）"
}}"""

    url = f"{mimo_config['base_url']}/chat/completions"
    headers = {
        "Authorization": f"Bearer {mimo_config['api_key']}",
        "Content-Type": "application/json"
    }
    payload = {
        "model": mimo_config["model"],
        "messages": [{"role": "user", "content": prompt}],
        "max_tokens": 4096,
        "temperature": 0.7
    }
    
    resp = requests.post(url, headers=headers, json=payload, timeout=120)
    
    if resp.status_code != 200:
        raise RuntimeError(f"MIMO API 调用失败: HTTP {resp.status_code}")
    
    data = resp.json()
    content = data["choices"][0]["message"]["content"]
    
    # 提取 JSON
    if "```" in content:
        parts = content.split("```")
        for part in parts:
            part = part.strip()
            if part.startswith("json"):
                part = part[4:].strip()
            if part.startswith("{"):
                try:
                    return json.loads(part)
                except json.JSONDecodeError:
                    continue
    
    # 尝试直接解析
    try:
        return json.loads(content)
    except json.JSONDecodeError:
        return {
            "title": title or topic,
            "digest": content[:50],
            "content": content,
            "author": ""
        }


def markdown_to_html(md_content: str) -> str:
    """Markdown → 公众号 HTML 格式"""
    import re
    
    html = md_content
    
    # 标题
    html = re.sub(r'^### (.+)$', r'<h3 style="font-size:18px;font-weight:bold;color:#333;margin:20px 0 10px;">\1</h3>', html, flags=re.MULTILINE)
    html = re.sub(r'^## (.+)$', r'<h2 style="font-size:22px;font-weight:bold;color:#333;margin:25px 0 15px;">\1</h2>', html, flags=re.MULTILINE)
    html = re.sub(r'^# (.+)$', r'<h1 style="font-size:26px;font-weight:bold;color:#333;margin:30px 0 20px;">\1</h1>', html, flags=re.MULTILINE)
    
    # 加粗和斜体
    html = re.sub(r'\*\*(.+?)\*\*', r'<strong>\1</strong>', html)
    html = re.sub(r'\*(.+?)\*', r'<em>\1</em>', html)
    
    # 列表
    html = re.sub(r'^\- (.+)$', r'<li style="margin:5px 0;">\1</li>', html, flags=re.MULTILINE)
    html = re.sub(r'^\d+\. (.+)$', r'<li style="margin:5px 0;">\1</li>', html, flags=re.MULTILINE)
    
    # 段落
    html = re.sub(r'\n\n', '</p><p style="margin:15px 0;line-height:1.8;font-size:16px;color:#333;">', html)
    
    # 包装
    html = f'<div style="padding:10px;font-family:-apple-system,BlinkMacSystemFont,sans-serif;"><p style="margin:15px 0;line-height:1.8;font-size:16px;color:#333;">{html}</p></div>'
    
    return html


# ========== 主命令 ==========

def cmd_draft(args):
    """创建草稿"""
    print("📝 创建公众号草稿")
    print("=" * 50)
    
    # 加载配置
    wechat_cfg = load_wechat_config()
    mimo_cfg = load_mimo_config()
    api = WeChatAPI(wechat_cfg["app_id"], wechat_cfg["app_secret"])
    
    # 生成或使用已有内容
    if args.content:
        print("📄 使用已有内容...")
        article = {
            "title": args.title,
            "content": args.content,
            "digest": args.content[:50],
            "author": args.author or ""
        }
    else:
        print(f"🤖 MIMO 生成文章...")
        print(f"   主题: {args.topic}")
        print(f"   风格: {args.style}")
        article = generate_article(
            topic=args.topic,
            title=args.title or "",
            style=args.style,
            mimo_config=mimo_cfg
        )
    
    # 转换为 HTML
    print("🎨 转换排版...")
    html_content = markdown_to_html(article.get("content", ""))
    
    # 上传封面图（如果有）
    thumb_media_id = ""
    if args.cover:
        print(f"🖼️  上传封面图: {args.cover}")
        cover_result = api.upload_thumb(args.cover)
        if "media_id" in cover_result:
            thumb_media_id = cover_result["media_id"]
            print(f"   ✅ 上传成功: {thumb_media_id}")
        else:
            print(f"   ⚠️  上传失败: {cover_result}")
    
    # 创建草稿
    print("📤 创建草稿...")
    result = api.create_draft(
        title=article.get("title", args.title),
        content=html_content,
        author=article.get("author", args.author or ""),
        digest=article.get("digest", ""),
        thumb_media_id=thumb_media_id
    )
    
    print("\n" + "=" * 50)
    if "media_id" in result:
        print("✅ 草稿创建成功！")
        print(f"   Media ID: {result['media_id']}")
        print(f"   标题: {article.get('title')}")
        output = {
            "status": "success",
            "action": "draft_created",
            "data": {
                "media_id": result["media_id"],
                "title": article.get("title"),
                "digest": article.get("digest")
            }
        }
    else:
        print(f"❌ 创建失败: {result}")
        output = {"status": "error", "data": result}
    
    if args.output:
        with open(args.output, "w", encoding="utf-8") as f:
            json.dump(output, f, indent=2, ensure_ascii=False)
        print(f"\n💾 结果已保存: {args.output}")
    
    return output


def cmd_cover(args):
    """上传封面图"""
    print(f"🖼️  上传封面图: {args.image}")
    print("=" * 50)
    
    wechat_cfg = load_wechat_config()
    api = WeChatAPI(wechat_cfg["app_id"], wechat_cfg["app_secret"])
    
    if args.permanent:
        print("📤 上传永久素材...")
        result = api.upload_permanent_image(args.image)
    else:
        print("📤 上传临时素材...")
        result = api.upload_thumb(args.image)
    
    if "media_id" in result:
        print(f"✅ 上传成功！")
        print(f"   Media ID: {result['media_id']}")
        return {"status": "success", "data": result}
    else:
        print(f"❌ 上传失败: {result}")
        return {"status": "error", "data": result}


def cmd_publish(args):
    """发布草稿"""
    print(f"📢 发布草稿: {args.media_id}")
    print("=" * 50)
    
    wechat_cfg = load_wechat_config()
    api = WeChatAPI(wechat_cfg["app_id"], wechat_cfg["app_secret"])
    
    result = api.publish(args.media_id)
    
    if "publish_id" in result:
        print("✅ 发布成功！")
        print(f"   Publish ID: {result['publish_id']}")
        return {"status": "success", "data": result}
    else:
        print(f"❌ 发布失败: {result}")
        return {"status": "error", "data": result}


def cmd_schedule(args):
    """定时发布（记录到本地，需要配合 cron）"""
    print(f"⏰ 设置定时发布: {args.time}")
    print("=" * 50)
    
    schedule_file = Path.home() / ".openclaw" / "wechat_schedule.json"
    
    schedules = []
    if schedule_file.exists():
        with open(schedule_file) as f:
            schedules = json.load(f)
    
    schedule = {
        "media_id": args.media_id,
        "publish_at": args.time,
        "created_at": time.strftime("%Y-%m-%d %H:%M:%S"),
        "status": "pending"
    }
    schedules.append(schedule)
    
    with open(schedule_file, "w", encoding="utf-8") as f:
        json.dump(schedules, f, indent=2, ensure_ascii=False)
    
    print("✅ 定时任务已创建！")
    print(f"   Media ID: {args.media_id}")
    print(f"   发布时间: {args.time}")
    print(f"\n💡 提示: 需要配合 cron 任务在指定时间执行 publish 命令")
    
    return {"status": "success", "data": schedule}


def cmd_list(args):
    """查看草稿列表"""
    print("📋 公众号草稿列表")
    print("=" * 50)
    
    wechat_cfg = load_wechat_config()
    api = WeChatAPI(wechat_cfg["app_id"], wechat_cfg["app_secret"])
    
    result = api.get_draft_list(offset=args.offset, count=args.limit)
    
    if "item" in result:
        items = result["item"]
        print(f"共 {result.get('total_count', len(items))} 篇草稿\n")
        
        for i, item in enumerate(items, 1):
            content = item.get("content", {}).get("news_item", [{}])[0]
            print(f"{i}. {content.get('title', '无标题')}")
            print(f"   Media ID: {item.get('media_id', 'N/A')}")
            print(f"   更新时间: {time.strftime('%Y-%m-%d %H:%M', time.localtime(item.get('update_time', 0)))}")
            print()
        
        return {"status": "success", "data": result}
    else:
        print(f"❌ 获取失败: {result}")
        return {"status": "error", "data": result}


def main():
    parser = argparse.ArgumentParser(description="WeChat Publisher - 公众号自动化发文工具")
    subparsers = parser.add_subparsers(dest="command", help="可用命令")
    
    # draft 命令
    draft_parser = subparsers.add_parser("draft", help="创建草稿")
    draft_parser.add_argument("--title", required=True, help="文章标题")
    draft_parser.add_argument("--topic", help="文章主题（用于AI生成）")
    draft_parser.add_argument("--content", help="文章内容（Markdown格式）")
    draft_parser.add_argument("--style", default="professional", 
                              choices=["professional", "casual", "humorous", "story", "tutorial"],
                              help="文章风格")
    draft_parser.add_argument("--author", default="", help="作者名")
    draft_parser.add_argument("--cover", help="封面图路径")
    draft_parser.add_argument("-o", "--output", help="输出文件路径")
    
    # cover 命令
    cover_parser = subparsers.add_parser("cover", help="上传封面图")
    cover_parser.add_argument("--image", required=True, help="图片路径")
    cover_parser.add_argument("--permanent", action="store_true", help="上传为永久素材")
    
    # publish 命令
    publish_parser = subparsers.add_parser("publish", help="发布草稿")
    publish_parser.add_argument("--media_id", required=True, help="草稿 media_id")
    
    # schedule 命令
    schedule_parser = subparsers.add_parser("schedule", help="定时发布")
    schedule_parser.add_argument("--media_id", required=True, help="草稿 media_id")
    schedule_parser.add_argument("--time", required=True, help="发布时间 (YYYY-MM-DD HH:MM)")
    
    # list 命令
    list_parser = subparsers.add_parser("list", help="查看草稿列表")
    list_parser.add_argument("--offset", type=int, default=0, help="偏移量")
    list_parser.add_argument("--limit", type=int, default=20, help="数量")
    
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        sys.exit(1)
    
    commands = {
        "draft": cmd_draft,
        "cover": cmd_cover,
        "publish": cmd_publish,
        "schedule": cmd_schedule,
        "list": cmd_list
    }
    
    try:
        commands[args.command](args)
    except Exception as e:
        print(f"\n❌ 错误: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
