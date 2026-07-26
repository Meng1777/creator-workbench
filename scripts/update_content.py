#!/usr/bin/env python3
"""
每日热点采集 + AI改写 + 更新 Gist

环境变量依赖:
- GIST_ID: 目标 Gist ID (可选，如果未提供则打印到控制台)
- GIST_TOKEN: 有 gist 写入权限的 GitHub Token
- AI_API_KEY: AI API 密钥 (支持 OpenAI / DeepSeek / 兼容格式)
- AI_API_BASE: 可选，AI API 基础 URL
- AI_MODEL: 可选，模型名称 (默认 deepseek-chat)
- NICHE_KEYWORDS: 赛道关键词，逗号分隔
- WECHAT_SOURCES: 公众号文章/专辑链接，逗号分隔

输出格式 (JSON，写入 Gist):
{
  "updated_at": "ISO8601",
  "hot_boards": [...],
  "ideas": [{title, tags[], description, keyword} x10],
  "recreate": [{hot_title, angle, platform} x10]
}
"""

import json
import os
import re
import sys
import time
import traceback
from datetime import datetime, timezone, timedelta
from urllib.parse import quote, urlencode

import requests
from bs4 import BeautifulSoup

LOG_FILE = "update.log"

def log(msg):
    ts = datetime.now(tz=timezone(timedelta(hours=8))).strftime("%Y-%m-%d %H:%M:%S")
    line = f"[{ts}] {msg}"
    print(line)
    with open(LOG_FILE, "a", encoding="utf-8") as f:
        f.write(line + "\n")


def fetch_hot_boards():
    """从 uapis.cn 获取多平台热榜，返回合并后的热点列表"""
    platforms = [
        ("douyin", "抖音"),
        ("weibo", "微博"),
        ("bilibili", "B站"),
        ("zhihu", "知乎"),
        ("toutiao", "今日头条"),
    ]
    hot_boards = []
    for type_key, name in platforms:
        try:
            url = f"https://uapis.cn/api/v1/misc/hotboard?type={type_key}&limit=20"
            r = requests.get(url, timeout=30)
            r.raise_for_status()
            data = r.json()
            items = data.get("data", []) or data.get("list", []) or data.get("results", []) or []
            # uapis 返回格式可能不同，兼容处理
            if not isinstance(items, list):
                items = []
            for i, item in enumerate(items[:15]):
                title = item.get("title") or item.get("word") or ""
                hot = item.get("hot") or item.get("hot_value") or 0
                link = item.get("url") or item.get("link") or ""
                if not title:
                    continue
                hot_boards.append({
                    "platform": type_key,
                    "platform_name": name,
                    "title": title.strip(),
                    "hot": hot,
                    "url": link,
                    "rank": i + 1,
                })
        except Exception as e:
            log(f"获取 {name} 热榜失败: {e}")
    log(f"共采集 {len(hot_boards)} 条热点")
    return hot_boards


def fetch_wechat_article(url):
    """使用 UA 伪装获取微信文章正文"""
    headers = {
        "User-Agent": (
            "Mozilla/5.0 (Linux; Android 10; SM-G960U) "
            "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.120 "
            "Mobile Safari/537.36 MicroMessenger/8.0.0"
        )
    }
    try:
        r = requests.get(url, headers=headers, timeout=30)
        r.raise_for_status()
        soup = BeautifulSoup(r.text, "html.parser")
        # 提取标题
        title = ""
        if soup.title:
            title = soup.title.string or ""
        title = re.sub(r"- 微信公众号", "", title).strip()
        # 提取正文
        content = ""
        # 微信文章正文通常在 #js_content
        content_div = soup.find("div", id="js_content")
        if content_div:
            paragraphs = []
            for p in content_div.find_all(["p", "section"]):
                text = p.get_text(strip=True)
                if text and len(text) > 5:
                    paragraphs.append(text)
            content = "\n".join(paragraphs[:30])  # 限制长度
        else:
            # fallback
            texts = [t.strip() for t in soup.get_text().splitlines() if len(t.strip()) > 10]
            content = "\n".join(texts[:30])
        return {"title": title, "url": url, "content": content[:3000]}
    except Exception as e:
        log(f"采集微信文章失败 {url}: {e}")
        return None


def fetch_wechat_sources():
    """获取所有配置的微信文章/专辑内容"""
    sources = os.environ.get("WECHAT_SOURCES", "").strip()
    if not sources:
        log("未配置 WECHAT_SOURCES")
        return []
    results = []
    for url in [s.strip() for s in sources.split(",") if s.strip()]:
        article = fetch_wechat_article(url)
        if article:
            results.append(article)
        time.sleep(1)  # 礼貌请求
    log(f"共采集 {len(results)} 篇微信文章")
    return results


def call_ai_api(prompt, api_key, api_base, model):
    """调用 AI API，返回文本内容"""
    # 默认使用 DeepSeek 兼容格式
    if not api_base:
        api_base = "https://api.deepseek.com/v1"
    if not model:
        model = "deepseek-chat"

    url = f"{api_base.rstrip('/')}/chat/completions"
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {api_key}",
    }
    payload = {
        "model": model,
        "messages": [
            {"role": "system", "content": "你是一位短视频选题策划专家，擅长把热点转化为可执行的短视频选题和二创角度。必须返回纯JSON格式，不要包含其他文字。"},
            {"role": "user", "content": prompt}
        ],
        "temperature": 0.8,
        "max_tokens": 4000,
    }

    try:
        r = requests.post(url, headers=headers, json=payload, timeout=120)
        r.raise_for_status()
        result = r.json()
        content = result["choices"][0]["message"]["content"]
        # 去除 markdown 代码块
        content = re.sub(r"^```json\s*", "", content.strip())
        content = re.sub(r"```\s*$", "", content.strip())
        return content
    except Exception as e:
        log(f"AI API 调用失败: {e}")
        return None


def generate_content(hot_boards, wechat_articles):
    """生成10条选题灵感和10条二创角度"""
    api_key = os.environ.get("AI_API_KEY")
    niche_keywords = os.environ.get("NICHE_KEYWORDS", "柯基狗狗、穿搭、化妆、护肤")

    if not api_key:
        log("未配置 AI_API_KEY，使用示例数据")
        return generate_fallback(hot_boards)

    hot_text = "\n".join([
        f"{i+1}. [{h['platform_name']}] {h['title']} (热度{h['hot']})"
        for i, h in enumerate(hot_boards[:20])
    ])

    wechat_text = "\n\n".join([
        f"文章{i+1}: {a['title']}\n{a['content'][:500]}"
        for i, a in enumerate(wechat_articles[:3])
    ]) or "（未提供微信参考素材）"

    prompt = f"""你是一位短视频选题策划专家。请根据以下热点和素材，为用户生成内容。

用户赛道关键词：{niche_keywords}

热点数据（排名前20）：
{hot_text}

参考素材：
{wechat_text}

要求：
1. 生成10条选题灵感，每条包含：
   - title: 标题（不超过20字，吸引人点击）
   - tags: 3个标签（数组）
   - description: 1-2句话说明内容方向
   - keyword: 用于搜索抖音和B站的关键词
   内容必须贴合用户赛道关键词，不要直接复述热点，要给出差异化视角。

2. 生成10条二创角度，每条包含：
   - hot_title: 原热点标题
   - angle: 具体的改编切入点（30字以内）
   - platform: 推荐平台，只能是 "douyin" 或 "bilibili"
   要给出明确的反套路、垂直化、真实案例等改编方向。

输出严格为JSON格式，不要包含任何markdown代码块或其他文字，格式如下：
{{
  "ideas": [...],
  "recreate": [...]
}}"""

    content = call_ai_api(prompt, api_key, os.environ.get("AI_API_BASE"), os.environ.get("AI_MODEL"))
    if not content:
        return generate_fallback(hot_boards)

    try:
        parsed = json.loads(content)
        ideas = parsed.get("ideas", [])
        recreate = parsed.get("recreate", [])
        # 校验字段
        if not ideas or not recreate:
            raise ValueError("AI 返回为空")
        return {"ideas": ideas, "recreate": recreate}
    except Exception as e:
        log(f"AI 返回解析失败: {e}\n原始内容前500字: {content[:500] if content else '无'}")
        return generate_fallback(hot_boards)


def generate_fallback(hot_boards):
    """当 AI 不可用时，使用基于热点的简单模板生成"""
    ideas = []
    recreate = []
    for i, h in enumerate(hot_boards[:10]):
        ideas.append({
            "title": f"围绕「{h['title'][:10]}」做一条深度解读",
            "tags": [h['platform'], "热点", "解读"],
            "description": f"结合{h['platform_name']}热榜话题，从垂直赛道角度给出你的独特观点。",
            "keyword": h['title']
        })
    for i, h in enumerate(hot_boards[:10]):
        platform = "douyin" if i % 2 == 0 else "bilibili"
        recreate.append({
            "hot_title": h['title'],
            "angle": f"反套路分析：{h['title'][:10]}背后的真实原因",
            "platform": platform
        })
    return {"ideas": ideas, "recreate": recreate}


def update_gist(data, gist_id, token):
    """更新 GitHub Gist"""
    if not gist_id or not token:
        log(f"未配置 GIST_ID 或 GIST_TOKEN，输出到本地: {json.dumps(data, ensure_ascii=False, indent=2)[:500]}")
        return False

    url = f"https://api.github.com/gists/{gist_id}"
    headers = {
        "Authorization": f"token {token}",
        "Accept": "application/vnd.github.v3+json",
    }
    payload = {
        "files": {
            "data.json": {
                "content": json.dumps(data, ensure_ascii=False, indent=2)
            }
        }
    }

    try:
        r = requests.patch(url, headers=headers, json=payload, timeout=30)
        r.raise_for_status()
        log(f"Gist 更新成功: {r.json().get('html_url')}")
        return True
    except Exception as e:
        log(f"Gist 更新失败: {e}")
        return False


def main():
    # 清空日志
    with open(LOG_FILE, "w", encoding="utf-8") as f:
        f.write("\n")

    log("开始每日热点采集任务")

    # 1. 采集热榜
    hot_boards = fetch_hot_boards()

    # 2. 采集微信文章
    wechat_articles = fetch_wechat_sources()

    # 3. 生成内容
    generated = generate_content(hot_boards, wechat_articles)

    # 4. 组装数据
    data = {
        "updated_at": datetime.now(tz=timezone(timedelta(hours=8))).isoformat(),
        "hot_boards": hot_boards,
        "ideas": generated.get("ideas", []),
        "recreate": generated.get("recreate", []),
    }

    # 5. 更新 Gist
    gist_id = os.environ.get("GIST_ID")
    token = os.environ.get("GIST_TOKEN")
    success = update_gist(data, gist_id, token)

    if not success:
        # 保存到本地供调试
        with open("data.json", "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        log("已将数据写入本地 data.json")
        sys.exit(1)

    log("任务完成")


if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        log(f"脚本异常: {e}")
        traceback.print_exc()
        sys.exit(1)
