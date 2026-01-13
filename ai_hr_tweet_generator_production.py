#!/usr/bin/env python3
import os
import json
import requests
from datetime import datetime
import anthropic

# Google Apps Script URL
SPREADSHEET_WEBHOOK = "https://script.google.com/macros/s/AKfycbxaAwqsszgBeOcuacwN9I54z9YtRzapVK1yUNLC9WCBThRVQKiisdqOZh8EjSHeJa8h/exec"

SEARCH_QUERIES = [
    "AI Agent 採用 人材 2025",
    "AIエージェント 人事 HR",
    "採用AI 自動化 最新",
]

PROMPT = """
あなたは「AI×採用」領域の専門家として、Xでインプレッションの高い投稿を作成するプロです。

以下のニュースから最もバズりそうなものを1つ選び、投稿を3パターン作成してください。

## ニュース一覧
{news_json}

## Xアルゴリズムの重要ポイント（2025年最新）
- 短文や一文のコンテンツはプッシュされない
- 高労力のコンテンツを優先
→ 「量より質」「短文より長文」が正解

## 投稿作成ルール
1. 文字数: 500〜1000文字程度
2. 構成: 冒頭フック → 本文・考察 → 読者へのアクション → 元ネタURL
3. 具体的な数字を入れる（ソースにない数字は使わない）
4. 独自の視点を加える（なぜ重要か、影響予測、取るべきアクション）
5. 適度に改行、箇条書きも可
6. ハッシュタグは最大2つ
7. 「私」「弊社」は使わない

## 投稿者ペルソナ
- AI×採用領域の専門家
- 転職者向けAIエージェントサービスを運営
- 1,500件以上のキャリア面談実績

## 出力形式（JSON）
{{
  "selected_news": "ニュースタイトル",
  "selected_news_url": "URL",
  "reason": "選んだ理由（50字以内）",
  "posts": [
    {{"text": "投稿本文（末尾にURL含む）", "format_type": "フォーマット名", "hook": "冒頭フック"}}
  ]
}}
"""

def fetch_news(queries):
    api_key = os.environ.get("TAVILY_API_KEY")
    if not api_key:
        raise ValueError("TAVILY_API_KEY not set")
    
    all_news = []
    seen = set()
    
    for query in queries:
        try:
            r = requests.post("https://api.tavily.com/search", json={
                "api_key": api_key,
                "query": query,
                "search_depth": "advanced",
                "max_results": 5,
                "exclude_domains": ["youtube.com", "twitter.com", "x.com"]
            })
            r.raise_for_status()
            for item in r.json().get("results", []):
                if item["url"] not in seen:
                    seen.add(item["url"])
                    all_news.append({
                        "title": item.get("title", ""),
                        "summary": item.get("content", "")[:300],
                        "url": item.get("url", "")
                    })
        except Exception as e:
            print(f"⚠️ Search error: {e}")
    
    return all_news[:10]

def generate_posts(news):
    client = anthropic.Anthropic()
    prompt = PROMPT.format(news_json=json.dumps(news, ensure_ascii=False, indent=2))
    
    msg = client.messages.create(
        model="claude-sonnet-4-20250514",
        max_tokens=4000,
        messages=[{"role": "user", "content": prompt}]
    )
    
    text = msg.content[0].text
    if "```json" in text:
        text = text.split("```json")[1].split("```")[0]
    else:
        text = text[text.find("{"):text.rfind("}")+1]
    
    return json.loads(text)

def send_to_spreadsheet(result):
    """結果をGoogleスプレッドシートに送信"""
    posts = result.get("posts", [])
    
    data = {
        "timestamp": datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
        "selected_news": result.get("selected_news", ""),
        "selected_news_url": result.get("selected_news_url", ""),
        "reason": result.get("reason", ""),
        "post1": posts[0].get("text", "") if len(posts) > 0 else "",
        "post2": posts[1].get("text", "") if len(posts) > 1 else "",
        "post3": posts[2].get("text", "") if len(posts) > 2 else "",
    }
    
    try:
        r = requests.post(SPREADSHEET_WEBHOOK, json=data)
        print(f"✅ スプレッドシートに送信完了")
        print(f"   レスポンス: {r.text}")
    except Exception as e:
        print(f"❌ スプレッドシート送信エラー: {e}")

def main():
    print(f"\n{'='*60}")
    print(f"🚀 AI採用ニュース → 投稿生成")
    print(f"📅 {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"{'='*60}\n")
    
    print("📥 ニュース取得中...")
    news = fetch_news(SEARCH_QUERIES)
    print(f"   → {len(news)}件取得\n")
    
    if not news:
        print("❌ ニュースが取得できませんでした")
        return
    
    for i, n in enumerate(news, 1):
        print(f"   {i}. {n['title'][:50]}...")
    
    print("\n⏳ 投稿生成中...")
    result = generate_posts(news)
    
    print(f"\n{'='*60}")
    print(f"📰 選択: {result.get('selected_news')}")
    print(f"🔗 URL: {result.get('selected_news_url')}")
    print(f"💡 理由: {result.get('reason')}")
    print(f"{'='*60}")
    
    for i, post in enumerate(result.get("posts", []), 1):
        print(f"\n【案{i}】{post.get('format_type')}")
        print(f"フック: {post.get('hook')}")
        print("-" * 60)
        print(post.get("text"))
        print(f"\n→ {len(post.get('text', ''))}文字")
    
    # スプレッドシートに送信
    print("\n📤 スプレッドシートに送信中...")
    send_to_spreadsheet(result)

if __name__ == "__main__":
    main()
