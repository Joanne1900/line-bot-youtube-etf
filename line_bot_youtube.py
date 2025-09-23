#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
LINE Bot YouTube ETF 搜尋機器人
功能：
1. 透過 LINE 查詢 YouTube ETF 熱門影片
2. 支援語音和文字指令
3. 自動回傳排行榜和連結
"""

import os
import json
import pandas as pd
from datetime import datetime, timedelta
import pytz
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

from flask import Flask, request, abort
from linebot import LineBotApi, WebhookHandler
from linebot.exceptions import InvalidSignatureError
from linebot.models import (
    MessageEvent, TextMessage, TextSendMessage,
    QuickReply, QuickReplyButton, MessageAction,
    FlexSendMessage, BubbleContainer, BoxComponent,
    TextComponent, ButtonComponent, URIAction,
    CarouselContainer, SeparatorComponent
)

# LINE Bot 設定
LINE_CHANNEL_SECRET = 'YOUR_LINE_CHANNEL_SECRET'
LINE_CHANNEL_ACCESS_TOKEN = 'YOUR_LINE_CHANNEL_ACCESS_TOKEN'

# YouTube API 設定
YOUTUBE_API_KEY = 'YOUR_YOUTUBE_API_KEY'

app = Flask(__name__)
line_bot_api = LineBotApi(LINE_CHANNEL_ACCESS_TOKEN)
handler = WebhookHandler(LINE_CHANNEL_SECRET)

class YouTubeETFBot:
    def __init__(self, api_key):
        self.api_key = api_key
        self.youtube = build('youtube', 'v3', developerKey=api_key)
        
    def get_recent_etf_videos(self, hours_ago=48, max_results=10, sort_by='viewCount'):
        """獲取最近ETF相關影片"""
        try:
            # 計算時間範圍
            taiwan_tz = pytz.timezone('Asia/Taipei')
            now = datetime.now(taiwan_tz)
            time_ago = now - timedelta(hours=hours_ago)
            published_after = time_ago.strftime('%Y-%m-%dT%H:%M:%SZ')
            
            etf_queries = ["台灣ETF", "ETF投資", "元大0050", "高股息ETF"]
            all_videos = []
            
            for query in etf_queries[:2]:  # 限制查詢數量
                try:
                    search_request = self.youtube.search().list(
                        part='snippet',
                        q=query,
                        type='video',
                        order=sort_by,
                        publishedAfter=published_after,
                        regionCode='TW',
                        maxResults=8
                    )
                    search_response = search_request.execute()
                    
                    video_ids = [item['id']['videoId'] for item in search_response['items']]
                    
                    if video_ids:
                        videos_request = self.youtube.videos().list(
                            part='snippet,statistics',
                            id=','.join(video_ids)
                        )
                        videos_response = videos_request.execute()
                        
                        for item in videos_response['items']:
                            video_info = self._extract_video_info(item)
                            if self._is_etf_related(video_info):
                                all_videos.append(video_info)
                                
                except Exception as e:
                    print(f"搜尋錯誤: {e}")
                    continue
            
            # 去重複
            unique_videos = {v['video_id']: v for v in all_videos}
            result_videos = list(unique_videos.values())
            
            # 排序並返回
            result_videos.sort(key=lambda x: int(x['view_count']), reverse=True)
            return result_videos[:max_results]
            
        except Exception as e:
            print(f"API 錯誤: {e}")
            return []
    
    def get_etf_videos_by_engagement(self, hours_ago=48, max_results=10):
        """獲取互動數最高的ETF影片"""
        videos = self.get_recent_etf_videos(hours_ago, max_results*2, 'viewCount')
        
        for video in videos:
            video['engagement_score'] = int(video['like_count']) + int(video['comment_count']) * 2
            video['engagement_rate'] = video['engagement_score'] / max(int(video['view_count']), 1) * 100
        
        videos.sort(key=lambda x: x['engagement_score'], reverse=True)
        return videos[:max_results]
    
    def _extract_video_info(self, item):
        """提取影片資訊"""
        snippet = item['snippet']
        statistics = item.get('statistics', {})
        
        return {
            'video_id': item['id'],
            'title': snippet['title'][:80] + '...' if len(snippet['title']) > 80 else snippet['title'],
            'channel_title': snippet['channelTitle'][:30],
            'published_at': snippet['publishedAt'],
            'view_count': statistics.get('viewCount', '0'),
            'like_count': statistics.get('likeCount', '0'),
            'comment_count': statistics.get('commentCount', '0'),
            'url': f"https://www.youtube.com/watch?v={item['id']}",
            'thumbnail': snippet['thumbnails']['high']['url']
        }
    
    def _is_etf_related(self, video_info):
        """檢查是否為ETF相關影片"""
        title = video_info['title'].lower()
        channel = video_info['channel_title'].lower()
        
        etf_keywords = [
            'etf', '0050', '0056', '台灣50', '高股息', 
            '元大', '富邦', '投資', '理財', '股市'
        ]
        
        exclude_keywords = [
            'poetry', 'music', 'dance', 'game', 'funny'
        ]
        
        has_etf = any(keyword in title for keyword in etf_keywords)
        has_exclude = any(keyword in title or keyword in channel for keyword in exclude_keywords)
        
        return has_etf and not has_exclude
    
    def _format_number(self, num):
        """格式化數字"""
        num = int(num)
        if num >= 1000000:
            return f"{num/1000000:.1f}M"
        elif num >= 1000:
            return f"{num/1000:.1f}K"
        return str(num)

# 初始化 YouTube Bot
youtube_bot = YouTubeETFBot(YOUTUBE_API_KEY)

def create_etf_carousel(videos, title="ETF 熱門影片"):
    """創建 LINE Carousel 訊息"""
    if not videos:
        return TextSendMessage(text="抱歉，沒有找到相關的ETF影片 😅")
    
    bubbles = []
    for i, video in enumerate(videos[:5]):  # 最多5個
        bubble = BubbleContainer(
            hero={
                "type": "image",
                "url": video['thumbnail'],
                "size": "full",
                "aspectRatio": "16:9",
                "aspectMode": "cover"
            },
            body=BoxComponent(
                layout="vertical",
                spacing="sm",
                contents=[
                    TextComponent(
                        text=f"#{i+1}",
                        weight="bold",
                        size="sm",
                        color="#1DB446"
                    ),
                    TextComponent(
                        text=video['title'],
                        weight="bold",
                        size="md",
                        wrap=True,
                        maxLines=2
                    ),
                    TextComponent(
                        text=video['channel_title'],
                        size="sm",
                        color="#666666",
                        wrap=True
                    ),
                    SeparatorComponent(margin="md"),
                    BoxComponent(
                        layout="vertical",
                        spacing="sm",
                        margin="md",
                        contents=[
                            BoxComponent(
                                layout="baseline",
                                spacing="sm",
                                contents=[
                                    TextComponent(text="👀", size="sm", flex=1),
                                    TextComponent(
                                        text=youtube_bot._format_number(video['view_count']),
                                        size="sm", flex=4, color="#666666"
                                    )
                                ]
                            ),
                            BoxComponent(
                                layout="baseline",
                                spacing="sm",
                                contents=[
                                    TextComponent(text="👍", size="sm", flex=1),
                                    TextComponent(
                                        text=youtube_bot._format_number(video['like_count']),
                                        size="sm", flex=4, color="#666666"
                                    )
                                ]
                            )
                        ]
                    )
                ]
            ),
            footer=BoxComponent(
                layout="vertical",
                spacing="sm",
                contents=[
                    ButtonComponent(
                        action=URIAction(label="觀看影片", uri=video['url']),
                        style="primary",
                        color="#1DB446"
                    )
                ]
            )
        )
        bubbles.append(bubble)
    
    return FlexSendMessage(
        alt_text=f"{title} Top {len(bubbles)}",
        contents=CarouselContainer(contents=bubbles)
    )

def create_quick_reply():
    """創建快速回覆按鈕"""
    return QuickReply(
        items=[
            QuickReplyButton(
                action=MessageAction(label="📊 觀看次數排行", text="觀看次數")
            ),
            QuickReplyButton(
                action=MessageAction(label="🔥 互動數排行", text="互動數")
            ),
            QuickReplyButton(
                action=MessageAction(label="⏰ 24小時內", text="24小時")
            ),
            QuickReplyButton(
                action=MessageAction(label="📅 一週內", text="一週")
            ),
            QuickReplyButton(
                action=MessageAction(label="❓ 說明", text="說明")
            )
        ]
    )

@app.route("/callback", methods=['POST'])
def callback():
    signature = request.headers['X-Line-Signature']
    body = request.get_data(as_text=True)
    
    try:
        handler.handle(body, signature)
    except InvalidSignatureError:
        abort(400)
    
    return 'OK'

@handler.add(MessageEvent, message=TextMessage)
def handle_message(event):
    user_message = event.message.text.lower()
    
    try:
        if any(keyword in user_message for keyword in ['嗨', 'hi', 'hello', '你好', '開始']):
            reply_text = """🤖 YouTube ETF 搜尋機器人

我可以幫你搜尋最新的台灣ETF相關影片！

📱 使用方式：
• 「觀看次數」- 最多觀看的ETF影片
• 「互動數」- 最多互動的ETF影片  
• 「24小時」- 過去24小時的影片
• 「一週」- 過去一週的影片
• 「說明」- 查看詳細說明

🎯 或直接點擊下方按鈕開始！"""
            
            line_bot_api.reply_message(
                event.reply_token,
                TextSendMessage(text=reply_text, quick_reply=create_quick_reply())
            )
            
        elif '觀看次數' in user_message or 'view' in user_message:
            videos = youtube_bot.get_recent_etf_videos(hours_ago=48, max_results=5)
            carousel = create_etf_carousel(videos, "48小時內觀看次數排行")
            line_bot_api.reply_message(event.reply_token, carousel)
            
        elif '互動' in user_message or 'engagement' in user_message:
            videos = youtube_bot.get_etf_videos_by_engagement(hours_ago=48, max_results=5)
            carousel = create_etf_carousel(videos, "48小時內互動數排行")
            line_bot_api.reply_message(event.reply_token, carousel)
            
        elif '24小時' in user_message or '24' in user_message:
            videos = youtube_bot.get_recent_etf_videos(hours_ago=24, max_results=5)
            carousel = create_etf_carousel(videos, "24小時內ETF熱門影片")
            line_bot_api.reply_message(event.reply_token, carousel)
            
        elif '一週' in user_message or '7天' in user_message or '週' in user_message:
            videos = youtube_bot.get_recent_etf_videos(hours_ago=168, max_results=5)  # 7*24=168
            carousel = create_etf_carousel(videos, "一週內ETF熱門影片")
            line_bot_api.reply_message(event.reply_token, carousel)
            
        elif '說明' in user_message or 'help' in user_message:
            help_text = """📖 功能說明

🔍 搜尋功能：
• 觀看次數：按YouTube觀看次數排序
• 互動數：按按讚+留言數排序
• 24小時：只看最近一天的影片
• 一週：看最近七天的影片

💡 搜尋範圍：
• 台灣ETF相關影片
• 0050、0056等熱門ETF
• 投資理財頻道內容

⚡ 快速指令：
輸入「觀看次數」、「互動數」、「24小時」、「一週」即可快速搜尋！

🤖 隨時輸入「嗨」重新開始！"""
            
            line_bot_api.reply_message(
                event.reply_token,
                TextSendMessage(text=help_text, quick_reply=create_quick_reply())
            )
            
        else:
            # 默認搜尋觀看次數排行
            videos = youtube_bot.get_recent_etf_videos(hours_ago=48, max_results=5)
            if videos:
                carousel = create_etf_carousel(videos, "ETF熱門影片排行")
                line_bot_api.reply_message(event.reply_token, carousel)
            else:
                line_bot_api.reply_message(
                    event.reply_token,
                    TextSendMessage(
                        text="抱歉，目前沒有找到相關的ETF影片 😅\n\n請試試輸入「說明」查看使用方式！",
                        quick_reply=create_quick_reply()
                    )
                )
                
    except Exception as e:
        print(f"處理訊息錯誤: {e}")
        line_bot_api.reply_message(
            event.reply_token,
            TextSendMessage(
                text="抱歉，處理請求時發生錯誤 😅\n請稍後再試或輸入「說明」查看使用方式！",
                quick_reply=create_quick_reply()
            )
        )

if __name__ == "__main__":
    # 開發環境
    app.run(host="0.0.0.0", port=5000, debug=True)
    
    # 生產環境 (使用 gunicorn)
    # gunicorn -w 4 -b 0.0.0.0:5000 line_bot_youtube:app