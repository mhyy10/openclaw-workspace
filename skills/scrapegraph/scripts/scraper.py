#!/usr/bin/env python3
"""
ScrapeGraphAI + MIMO V2.5 Pro 爬虫工具
使用小米官方 API 进行智能网页数据提取

用法:
  python3 scraper.py <url> <prompt> [--output result.json]
  
示例:
  python3 scraper.py "https://news.ycombinator.com" "提取前5条新闻标题和分数"
  python3 scraper.py "https://example.com" "提取所有产品信息" --output products.json
"""

import os
import sys
import json
import time
import argparse
import requests
from typing import Optional, Dict, Any
from pathlib import Path


# ========== 配置 ==========

def load_config() -> Dict[str, str]:
    """从 OpenClaw 配置加载小米 API 设置"""
    config_path = Path.home() / ".openclaw" / "openclaw.json"
    if not config_path.exists():
        raise FileNotFoundError(f"找不到配置文件: {config_path}")
    
    with open(config_path) as f:
        cfg = json.load(f)
    
    xiaomi = cfg.get("models", {}).get("providers", {}).get("xiaomi", {})
    if not xiaomi or not xiaomi.get("apiKey"):
        raise ValueError("未找到小米 API 配置，请先在 OpenClaw 中配置 xiaomi provider")
    
    return {
        "api_key": xiaomi["apiKey"],
        "base_url": xiaomi["baseUrl"].rstrip("/"),
        "model": "mimo-v2.5-pro"
    }


# ========== 网页抓取 ==========

def fetch_webpage(url: str, timeout: int = 30) -> str:
    """抓取网页内容"""
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    }
    
    try:
        resp = requests.get(url, headers=headers, timeout=timeout, verify=False)
        resp.raise_for_status()
        resp.encoding = resp.apparent_encoding or "utf-8"
        return resp.text
    except requests.RequestException as e:
        raise RuntimeError(f"抓取网页失败: {e}")


def extract_text_from_html(html: str, max_chars: int = 50000) -> str:
    """从 HTML 提取可读文本（简单实现，不依赖 BeautifulSoup）"""
    import re
    
    # 移除 script 和 style
    html = re.sub(r'<script[^>]*>.*?</script>', '', html, flags=re.DOTALL | re.IGNORECASE)
    html = re.sub(r'<style[^>]*>.*?</style>', '', html, flags=re.DOTALL | re.IGNORECASE)
    html = re.sub(r'<!--.*?-->', '', html, flags=re.DOTALL)
    
    # 保留有用的标签结构
    html = re.sub(r'<br\s*/?\s*>', '\n', html, flags=re.IGNORECASE)
    html = re.sub(r'</(p|div|tr|li|h[1-6])>', '\n', html, flags=re.IGNORECASE)
    html = re.sub(r'<(p|div|tr|li|h[1-6])[^>]*>', '', html, flags=re.IGNORECASE)
    
    # 移除所有其他标签
    html = re.sub(r'<[^>]+>', ' ', html)
    
    # 清理空白
    html = re.sub(r'\s+', ' ', html)
    html = re.sub(r'\n\s*\n', '\n\n', html)
    
    # 解码 HTML 实体
    html = html.replace('&amp;', '&')
    html = html.replace('&lt;', '<')
    html = html.replace('&gt;', '>')
    html = html.replace('&quot;', '"')
    html = html.replace('&#39;', "'")
    html = html.replace('&nbsp;', ' ')
    
    text = html.strip()
    if len(text) > max_chars:
        text = text[:max_chars] + "\n...(内容已截断)"
    
    return text


# ========== MIMO 调用 ==========

def call_mimo(
    prompt: str,
    config: Dict[str, str],
    max_tokens: int = 4096,
    temperature: float = 0,
    retries: int = 3
) -> Dict[str, Any]:
    """调用 MIMO V2.5 Pro API"""
    
    url = f"{config['base_url']}/chat/completions"
    headers = {
        "Authorization": f"Bearer {config['api_key']}",
        "Content-Type": "application/json"
    }
    payload = {
        "model": config["model"],
        "messages": [{"role": "user", "content": prompt}],
        "max_tokens": max_tokens,
        "temperature": temperature
    }
    
    for attempt in range(retries):
        try:
            resp = requests.post(url, headers=headers, json=payload, timeout=120)
            if resp.status_code == 200:
                return resp.json()
            
            if attempt < retries - 1:
                wait = (attempt + 1) * 5
                print(f"  ⚠️  HTTP {resp.status_code}，{wait}秒后重试...")
                time.sleep(wait)
            else:
                raise RuntimeError(f"API 调用失败 (HTTP {resp.status_code}): {resp.text[:500]}")
                
        except requests.Timeout:
            if attempt < retries - 1:
                print(f"  ⚠️  请求超时，重试中...")
                time.sleep(5)
            else:
                raise RuntimeError("API 调用超时")
    
    raise RuntimeError("所有重试都失败了")


def extract_json_from_response(content: str) -> Any:
    """从响应中提取 JSON"""
    # 尝试直接解析
    try:
        return json.loads(content)
    except json.JSONDecodeError:
        pass
    
    # 尝试从 markdown 代码块提取
    if "```" in content:
        parts = content.split("```")
        for part in parts:
            part = part.strip()
            if part.startswith("json"):
                part = part[4:].strip()
            if part.startswith(("{", "[")):
                try:
                    return json.loads(part)
                except json.JSONDecodeError:
                    continue
    
    # 尝试找第一个 JSON 对象或数组
    import re
    json_match = re.search(r'(\{[\s\S]*\}|\[[\s\S]*\])', content)
    if json_match:
        try:
            return json.loads(json_match.group(1))
        except json.JSONDecodeError:
            pass
    
    return content


# ========== 主流程 ==========

def scrape(url: str, prompt: str, output_file: Optional[str] = None) -> Dict[str, Any]:
    """主爬取流程"""
    
    print("🕷️  ScrapeGraphAI + MIMO V2.5 Pro 智能爬虫")
    print("=" * 55)
    print(f"📎 目标: {url}")
    print(f"📝 任务: {prompt}")
    print("-" * 55)
    
    # 1. 加载配置
    print("⚙️  加载配置...")
    config = load_config()
    print(f"   API: {config['base_url']}")
    print(f"   模型: {config['model']}")
    
    # 2. 抓取网页
    print("\n🌐 抓取网页...")
    html = fetch_webpage(url)
    print(f"   原始大小: {len(html):,} 字符")
    
    # 3. 提取文本
    print("📄 提取文本...")
    text = extract_text_from_html(html)
    print(f"   可读文本: {len(text):,} 字符")
    
    # 4. 构建 prompt
    full_prompt = f"""请从以下网页内容中提取信息。

任务: {prompt}

要求:
1. 返回有效的 JSON 格式
2. 如果信息不存在，对应字段设为 null
3. 保持数据结构清晰

网页内容:
{text}"""

    # 5. 调用 MIMO
    print("\n🤖 调用 MIMO V2.5 Pro...")
    start_time = time.time()
    result = call_mimo(full_prompt, config)
    elapsed = time.time() - start_time
    
    content = result["choices"][0]["message"]["content"]
    reasoning = result["choices"][0]["message"].get("reasoning_content", "")
    usage = result.get("usage", {})
    
    print(f"   耗时: {elapsed:.1f}秒")
    print(f"   Tokens: {usage.get('total_tokens', 'N/A')} (推理: {usage.get('completion_tokens_details', {}).get('reasoning_tokens', 0)})")
    
    # 6. 解析结果
    print("\n📊 解析结果...")
    parsed = extract_json_from_response(content)
    
    output = {
        "url": url,
        "prompt": prompt,
        "result": parsed,
        "reasoning": reasoning[:500] if reasoning else None,
        "metadata": {
            "model": config["model"],
            "tokens": usage,
            "elapsed_seconds": round(elapsed, 2)
        }
    }
    
    # 7. 保存结果
    if output_file:
        with open(output_file, "w", encoding="utf-8") as f:
            json.dump(output, f, indent=2, ensure_ascii=False)
        print(f"\n💾 结果已保存: {output_file}")
    
    return output


def main():
    parser = argparse.ArgumentParser(
        description="ScrapeGraphAI + MIMO V2.5 Pro 智能爬虫",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  %(prog)s "https://news.ycombinator.com" "提取前5条新闻标题和分数"
  %(prog)s "https://example.com/products" "提取所有产品名称和价格" --output products.json
  %(prog)s "https://blog.example.com" "提取文章标题、作者和发布日期" -o articles.json
        """
    )
    parser.add_argument("url", help="目标网页 URL")
    parser.add_argument("prompt", help="提取任务描述")
    parser.add_argument("-o", "--output", help="输出文件路径 (JSON)")
    parser.add_argument("--max-tokens", type=int, default=4096, help="最大输出 tokens (默认 4096)")
    parser.add_argument("--timeout", type=int, default=30, help="网页抓取超时秒数 (默认 30)")
    
    args = parser.parse_args()
    
    try:
        result = scrape(args.url, args.prompt, args.output)
        
        print("\n" + "=" * 55)
        print("✅ 爬取完成！")
        print("=" * 55)
        print("\n📋 提取结果:")
        if isinstance(result["result"], (dict, list)):
            print(json.dumps(result["result"], indent=2, ensure_ascii=False))
        else:
            print(result["result"])
            
    except Exception as e:
        print(f"\n❌ 错误: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
