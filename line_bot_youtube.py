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
from linebot.v3 import WebhookHandler
from linebot.v3.exceptions import InvalidSignatureError
from linebot.v3.messaging import (
    Configuration, ApiClient, MessagingApi,
    ReplyMessageRequest, PushMessageRequest, TextMessage, FlexMessage,
    QuickReply, QuickReplyItem, MessageAction,
    FlexBubble, FlexBox, FlexText, FlexButton,
    FlexCarousel, FlexSeparator, FlexImage, URIAction
)
from linebot.v3.webhooks import MessageEvent, TextMessageContent

# LINE Bot 設定
LINE_CHANNEL_SECRET = os.environ.get('LINE_CHANNEL_SECRET', 'your_channel_secret')
LINE_CHANNEL_ACCESS_TOKEN = os.environ.get('LINE_CHANNEL_ACCESS_TOKEN', 'your_access_token')

# YouTube API 設定
YOUTUBE_API_KEY = os.environ.get('YOUTUBE_API_KEY', 'your_youtube_api_key')

app = Flask(__name__)

# LINE Bot v3 配置
configuration = Configuration(access_token=LINE_CHANNEL_ACCESS_TOKEN)
api_client = ApiClient(configuration)
line_bot_api = MessagingApi(api_client)
handler = WebhookHandler(LINE_CHANNEL_SECRET)

class YouTubeETFBot:
    def __init__(self, api_key):
        self.api_key = api_key
        self.youtube = build('youtube', 'v3', developerKey=api_key)
        
        
"""        
    def get_recent_etf_videos(self, hours_ago=168, max_results=10, sort_by='viewCount'):
        #獲取最近ETF相關影片
        try:
            # 計算時間範圍
            taiwan_tz = pytz.timezone('Asia/Taipei')
            now = datetime.now(taiwan_tz)
            time_ago = now - timedelta(hours=hours_ago)
            published_after = time_ago.strftime('%Y-%m-%dT%H:%M:%SZ')
            
            etf_queries = ["台灣ETF", "ETF投資", "元大0050", "高股息ETF", "台湾ETF", "ETF投资", "高股息", "股票基金"]
            all_videos = []
            
            for query in etf_queries[:4]:  # 增加查詢數量
                try:
                    search_request = self.youtube.search().list(
                        part='snippet',
                        q=query,
                        type='video',
                        order=sort_by,
                        publishedAfter=published_after,
                        regionCode='TW',
                        maxResults=10
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
            
            # 去重複（以video_id為鍵，確保沒有重複影片）
            unique_videos = {v['video_id']: v for v in all_videos}
            result_videos = list(unique_videos.values())

            # 排序並返回，確保前N名無重複
            result_videos.sort(key=lambda x: int(x['view_count']), reverse=True)

            # 最終確認：再次檢查前N名是否有重複
            seen_ids = set()
            final_results = []
            for video in result_videos:
                if video['video_id'] not in seen_ids and len(final_results) < max_results:
                    seen_ids.add(video['video_id'])
                    final_results.append(video)

            return final_results
            
        except Exception as e:
            print(f"API 錯誤: {e}")
            return []
"""
    
    def get_etf_videos_by_engagement(self, hours_ago=72, max_results=12):
        """ETF日均觀看排行：篩選條件1+2，時間參數為3天，排序方式1的前12名影片"""
        return self.search_videos_unified(
            hours_ago=hours_ago,
            max_results=max_results,
            filter_etf=True,
            filter_taiwan_chinese=True,
            topic=None,
            sort_by='view_per_day',
            category_search=False
        )

    def get_etf_videos_by_special_categories(self, hours_ago=72, max_results=12):
        """教育分類日均排行：youtube新聞及教育分類，篩選條件2，時間參數為3天，排序方式1的前12名影片"""
        return self.search_videos_unified(
            hours_ago=hours_ago,
            max_results=max_results,
            filter_etf=False,
            filter_taiwan_chinese=True,
            topic=None,
            sort_by='view_per_day',
            category_search=True
        )

    def _calculate_view_per_day(self, video_info):
        """計算觀看次數/發布天數比率"""
        try:
            pub_time = datetime.fromisoformat(video_info['published_at'].replace('Z', '+00:00'))
            now = datetime.now(pub_time.tzinfo)
            days_since_publish = max((now - pub_time).days, 1)  # 至少1天避免除以0

            view_count = int(video_info['view_count'])
            return view_count / days_since_publish
        except:
            return 0

    def get_etf_videos_by_category(self, category_type, hours_ago=168, max_results=12):
        """各分類ETF：篩選條件1+2，主題相關的影片，時間參數為7天，排序方式1的前12名"""
        return self.search_videos_unified(
            hours_ago=hours_ago,
            max_results=max_results,
            filter_etf=True,
            filter_taiwan_chinese=True,
            topic=category_type,
            sort_by='view_per_day',
            category_search=False
        )

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
            '元大', '富邦', '投資', '理財', '股市',
            '台湾50', '投资', '理财', '股市', '基金'
        ]

        exclude_keywords = [
            'poetry', 'music', 'dance', 'game', 'funny'
        ]

        # 檢查是否包含中文字符
        def has_chinese(text):
            return any('\u4e00' <= char <= '\u9fff' for char in text)

        # 檢查是否包含日文字符
        def has_japanese(text):
            return any('\u3040' <= char <= '\u309f' or '\u30a0' <= char <= '\u30ff' for char in text)

        # 檢查是否包含韓文字符
        def has_korean(text):
            return any('\uac00' <= char <= '\ud7af' for char in text)

        # 排除特定頻道（用於ETF日均觀看排行）
        exclude_etf_channels = [
            '芝麻開門', '芝麻开门', 'sesame', 'zhima'
        ]

        has_etf = any(keyword in title for keyword in etf_keywords)
        has_exclude = any(keyword in title or keyword in channel for keyword in exclude_keywords)
        has_exclude_etf_channel = any(channel_name in channel.lower() or channel_name in title.lower()
                                     for channel_name in exclude_etf_channels)
        is_chinese = has_chinese(video_info['title']) or has_chinese(video_info['channel_title'])
        is_japanese = has_japanese(video_info['title']) or has_japanese(video_info['channel_title'])
        is_korean = has_korean(video_info['title']) or has_korean(video_info['channel_title'])

        return (has_etf and not has_exclude and not has_exclude_etf_channel and
                is_chinese and not is_japanese and not is_korean)

    def _is_taiwan_chinese_content(self, video_info):
        """篩選條件2：只要台灣地區的影片，排除日文、韓文、簡體中文、香港、新加坡地區影片"""
        title = video_info['title']
        channel = video_info['channel_title']

        # 檢查是否包含中文字符
        def has_chinese(text):
            return any('\u4e00' <= char <= '\u9fff' for char in text)

        # 檢查是否包含日文字符
        def has_japanese(text):
            return any('\u3040' <= char <= '\u309f' or '\u30a0' <= char <= '\u30ff' for char in text)

        # 檢查是否包含韓文字符
        def has_korean(text):
            return any('\uac00' <= char <= '\ud7af' for char in text)

        # 檢查是否包含簡體中文特有字符（與繁體明顯不同的簡化字）
        def has_simplified_chinese(text):
            simplified_chars = [
                '国', '经', '济', '车', '电', '华', '时', '实', '现', '发', '业', '报',
                '库', '团', '专', '从', '个', '为', '书', '会', '学', '应', '开', '关',
                '机', '进', '还', '过', '运', '门', '头', '面', '问', '题', '间', '样',
                '种', '动', '变', '须', '员', '让', '线', '听', '谈', '议', '记', '产',
                '总', '条', '只', '处', '费', '积', '历', '确', '响', '区', '传', '调',
                '证', '单', '亿', '万', '块', '钱', '价', '购', '买', '卖', '销', '贸',
                '计', '设', '备', '术', '技', '息', '信', '网', '站', '页'
            ]
            return any(char in text for char in simplified_chars)

        # 檢查是否包含非台灣地區特有詞彙
        def has_non_taiwan_terms(text):
            non_taiwan_terms = [
                # 香港澳門
                '港股', '恆指', '恆生', '港元', 'HKEX', '港交所', '澳門', '澳幣', '港幣',
                '香港', '廣東話', '粵語', '係', '咁', '嘅', '佢', '唔', '乜', '點解',
                '茶餐廳', '屋企', '返工', '收工', '巴士', '的士', '搭車',

                # 新加坡馬來西亞
                '新加坡', '馬來西亞', '星洲', '大馬', '新馬', '令吉', '新元', 'SGX', 'KLCI',
                '組屋', 'HDB', '小販中心', '巴剎',

                # 大陸用詞
                '人民幣', '滬深', '上證', '深證', '沪深', '人民币', '央行', '中行',
                '微信', '支付寶', '支付宝', '淘寶', '淘宝', '百度', '騰訊', '腾讯',
                '中国', '内地', '內地', '大陸', '大陆', '央視', '央视', '公安', '城管',
                '戶口', '户口', '身份證', '身份证', '居委會', '居委会'
            ]
            return any(term in text for term in non_taiwan_terms)

        # 基本語言檢查
        is_chinese = has_chinese(title) or has_chinese(channel)
        has_japanese = has_japanese(title) or has_japanese(channel)
        has_korean = has_korean(title) or has_korean(channel)
        has_simplified = has_simplified_chinese(title) or has_simplified_chinese(channel)
        has_non_taiwan = has_non_taiwan_terms(title) or has_non_taiwan_terms(channel)

        # 排除的娛樂內容關鍵字
        exclude_keywords = [
            'poetry', 'music', 'dance', 'game', 'funny', 'song', 'cover',
            '音樂', '歌曲', '舞蹈', '遊戲', '娛樂', '綜藝', '歌手', '演唱',
            '翻唱', '直播', 'live', 'stream', '聊天', 'chat'
        ]

        # 排除特定YouTuber頻道（用於教育分類）
        exclude_channels = [
            'RagaFinance財經台', 'ragafinance財經台', 'ragafinance', 'raga finance'
        ]

        has_exclude = any(keyword in title.lower() or keyword in channel.lower()
                         for keyword in exclude_keywords)

        has_exclude_channel = any(channel_name in channel.lower() or channel_name in title.lower()
                                 for channel_name in exclude_channels)

        # 台灣地區影片判定：
        # 1. 必須是中文內容
        # 2. 不能包含日文字符
        # 3. 不能包含韓文字符
        # 4. 不能包含簡體中文字符
        # 5. 不能包含非台灣地區詞彙
        # 6. 不能是娛樂內容
        # 7. 不能是被排除的特定頻道

        return (is_chinese and
                not has_japanese and
                not has_korean and
                not has_simplified and
                not has_non_taiwan and
                not has_exclude and
                not has_exclude_channel)

    def _matches_topic(self, video_info, topic):
        """檢查影片是否符合特定主題"""
        if not topic:
            return True

        title = video_info['title'].lower()
        channel = video_info['channel_title'].lower()

        topic_keywords = {
            'active': ['主動式', '主動型', 'AI', '科技', '全球', '國際', '新興', '成長', '價值', '新創', '雲端', '5G', '電動車', '綠能', 'ESG'],
            'allocation': ['資產配置', '平衡型', '多重資產', '多元資產', '安聯', '收益成長', '組合基金', '目標日期', '60/40', '策略配置', '混合型', '穩健型'],
            'market_cap': ['006208', '0050', '大盤', '加權', '市值', '規模', '大型股', '中型股', '台積電', '市值型'],
            'dividend': ['高股息', '0056', '配息', '00919', '00878', '00929', '00713', '00940', '高息'],
            'china_stock': ['0061', '006205', '006206', '006207', '00625k', '00633l', '00634r', '00636', '00636k', '00637l', '00638r', '00639', '00643', '00643k', '00650l', '00651r', '00655l', '00656r', '00665l', '00666r', '00700', '00703', '00739', '00743', '00752', '00753l', '00783', '008201', '00877', '00882', '00887', '陸股', '中國', '滬深', 'a股', '港股', '恆生']
        }

        keywords = topic_keywords.get(topic, [])
        return any(keyword in title or keyword in channel for keyword in keywords)

    def _calculate_engagement_ratio(self, video_info):
        """計算互動比率 = (按讚+留言)/觀看次數"""
        try:
            views = int(video_info['view_count'])
            likes = int(video_info['like_count'])
            comments = int(video_info['comment_count'])

            if views == 0:
                return 0

            return (likes + comments) / views
        except:
            return 0

    def search_videos_unified(self, hours_ago=168, max_results=12,
                             filter_etf=True, filter_taiwan_chinese=True,
                             topic=None, sort_by='view_per_day', category_search=False):
        """統一的影片搜尋函數

        Args:
            hours_ago: 時間範圍（小時）
            max_results: 最大結果數量
            filter_etf: 是否篩選ETF相關影片
            filter_taiwan_chinese: 是否篩選台灣中文影片
            topic: 主題篩選 ('active', 'allocation', 'market_cap', 'dividend', 'china_stock')
            sort_by: 排序方式 ('view_per_day', 'engagement_ratio')
            category_search: 是否使用分類搜尋（新聞及教育）
        """
        try:
            # 計算時間範圍
            taiwan_tz = pytz.timezone('Asia/Taipei')
            now = datetime.now(taiwan_tz)
            time_ago = now - timedelta(hours=hours_ago)
            published_after = time_ago.strftime('%Y-%m-%dT%H:%M:%SZ')

            all_videos = []

            if category_search:
                # 教育分類搜尋：直接從 YouTube 新聞及教育分類搜尋，不使用特定關鍵字
                search_queries = ["投資", "理財", "財經", "金融", "經濟"]
            elif topic:
                # 主題相關搜尋
                topic_base_queries = {
                    'active': ["主動式 ETF", "AI ETF", "科技 ETF", "全球 ETF"],
                    'allocation': ["資產配置 ETF", "平衡型 ETF", "多重資產 ETF", "安聯 ETF"],
                    'market_cap': ["0050 ETF", "006208 ETF", "大盤 ETF", "市值型 ETF"],
                    'dividend': ["高股息 ETF", "0056 ETF", "配息 ETF", "00919 ETF"],
                    'china_stock': ["陸股 ETF", "中國 ETF", "滬深 ETF", "A股 ETF"]
                }
                search_queries = topic_base_queries.get(topic, ["台灣ETF", "ETF投資"])
            else:
                # 一般ETF搜尋
                search_queries = ["台灣ETF", "ETF投資", "元大0050", "高股息ETF", "ETF 教育", "ETF 財經", "投資 教學", "理財 教學"]

            for query in search_queries:
                try:
                    if category_search:
                        # 教育分類搜尋：使用新聞與政治分類 (ID: 25) 和教育分類 (ID: 27)
                        search_request = self.youtube.search().list(
                            part='snippet',
                            q=query,
                            type='video',
                            order='viewCount',
                            publishedAfter=published_after,
                            regionCode='TW',
                            videoCategoryId='25',  # 新聞與政治分類
                            maxResults=5
                        )
                        search_response = search_request.execute()

                        # 也搜尋教育分類
                        search_request_edu = self.youtube.search().list(
                            part='snippet',
                            q=query,
                            type='video',
                            order='viewCount',
                            publishedAfter=published_after,
                            regionCode='TW',
                            videoCategoryId='27',  # 教育分類
                            maxResults=5
                        )
                        search_response_edu = search_request_edu.execute()

                        # 合併兩個搜尋結果
                        combined_items = search_response['items'] + search_response_edu['items']
                        search_response['items'] = combined_items
                    else:
                        # 一般搜尋
                        search_request = self.youtube.search().list(
                            part='snippet',
                            q=query,
                            type='video',
                            order='viewCount',
                            publishedAfter=published_after,
                            regionCode='TW',
                            maxResults=10
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

                            # 篩選條件檢查
                            passes_filter = True

                            if filter_etf and not self._is_etf_related(video_info):
                                passes_filter = False

                            if filter_taiwan_chinese and not self._is_taiwan_chinese_content(video_info):
                                passes_filter = False

                            if topic and not self._matches_topic(video_info, topic):
                                passes_filter = False

                            if passes_filter:
                                # 計算排序所需的數據
                                video_info['view_per_day'] = self._calculate_view_per_day(video_info)
                                video_info['engagement_score'] = int(video_info['like_count']) + int(video_info['comment_count']) * 2
                                video_info['engagement_rate'] = video_info['engagement_score'] / max(int(video_info['view_count']), 1) * 100
                                video_info['engagement_ratio'] = self._calculate_engagement_ratio(video_info)
                                all_videos.append(video_info)

                except Exception as e:
                    print(f"搜尋查詢 '{query}' 錯誤: {e}")
                    continue

            # 去重複（以video_id為鍵，確保沒有重複影片）
            unique_videos = {v['video_id']: v for v in all_videos}
            result_videos = list(unique_videos.values())

            # 根據排序方式排序
            if sort_by == 'engagement_ratio':
                result_videos.sort(key=lambda x: x.get('engagement_ratio', 0), reverse=True)
            else:  # 默認按日均觀看次數排序
                result_videos.sort(key=lambda x: x.get('view_per_day', 0), reverse=True)

            # 最終確認：再次檢查前N名是否有重複
            seen_ids = set()
            final_results = []
            for video in result_videos:
                if video['video_id'] not in seen_ids and len(final_results) < max_results:
                    seen_ids.add(video['video_id'])
                    final_results.append(video)

            return final_results

        except Exception as e:
            print(f"統一搜尋 API錯誤: {e}")
            return []

    def _format_number(self, num):
        """格式化數字"""
        num = int(num)
        if num >= 1000000:
            return f"{num/1000000:.1f}M"
        elif num >= 1000:
            return f"{num/1000:.1f}K"
        return str(num)

    def _format_publish_time(self, published_at):
        """格式化發布時間"""
        try:
            from datetime import datetime
            # YouTube API 返回的時間格式: 2023-10-15T10:30:00Z
            pub_time = datetime.fromisoformat(published_at.replace('Z', '+00:00'))
            now = datetime.now(pub_time.tzinfo)
            diff = now - pub_time

            if diff.days > 0:
                return f"{diff.days}天前"
            elif diff.seconds > 3600:
                hours = diff.seconds // 3600
                return f"{hours}小時前"
            else:
                minutes = diff.seconds // 60
                return f"{minutes}分鐘前"
        except:
            return "未知"

    def _calculate_engagement_rate(self, video_info):
        """計算互動率"""
        try:
            views = int(video_info['view_count'])
            likes = int(video_info['like_count'])
            comments = int(video_info['comment_count'])

            if views == 0:
                return "0%"

            engagement_rate = ((likes + comments) / views) * 100
            return f"{engagement_rate:.1f}%"
        except:
            return "N/A"

# 初始化 YouTube Bot
youtube_bot = YouTubeETFBot(YOUTUBE_API_KEY)

def create_etf_carousel(videos, title="ETF 熱門影片"):
    """創建 LINE Carousel 訊息"""
    if not videos:
        return TextMessage(text="抱歉，沒有找到相關的ETF影片 😅")

    bubbles = []
    for i, video in enumerate(videos[:10]):  # 最多10個
        bubble = FlexBubble(
            hero=FlexImage(
                url=video['thumbnail'],
                size="full",
                aspect_ratio="16:9",
                aspect_mode="cover"
            ),
            body=FlexBox(
                layout="vertical",
                spacing="sm",
                contents=[
                    FlexText(
                        text=f"#{i+1}",
                        weight="bold",
                        size="sm",
                        color="#1DB446"
                    ),
                    FlexText(
                        text=video['title'],
                        weight="bold",
                        size="md",
                        wrap=True,
                        max_lines=2
                    ),
                    FlexText(
                        text=video['channel_title'],
                        size="sm",
                        color="#666666",
                        wrap=True
                    ),
                    FlexSeparator(margin="md"),
                    FlexBox(
                        layout="vertical",
                        spacing="sm",
                        margin="md",
                        contents=[
                            FlexBox(
                                layout="baseline",
                                spacing="sm",
                                contents=[
                                    FlexText(text="👀", size="sm", flex=1),
                                    FlexText(
                                        text=youtube_bot._format_number(video['view_count']),
                                        size="sm", flex=4, color="#666666"
                                    )
                                ]
                            ),
                            FlexBox(
                                layout="baseline",
                                spacing="sm",
                                contents=[
                                    FlexText(text="👍", size="sm", flex=1),
                                    FlexText(
                                        text=youtube_bot._format_number(video['like_count']),
                                        size="sm", flex=4, color="#666666"
                                    )
                                ]
                            ),
                            FlexBox(
                                layout="baseline",
                                spacing="sm",
                                contents=[
                                    FlexText(text="📅", size="sm", flex=1),
                                    FlexText(
                                        text=youtube_bot._format_publish_time(video['published_at']),
                                        size="sm", flex=4, color="#666666"
                                    )
                                ]
                            ),
                            FlexBox(
                                layout="baseline",
                                spacing="sm",
                                contents=[
                                    FlexText(text="🔥", size="sm", flex=1),
                                    FlexText(
                                        text=youtube_bot._calculate_engagement_rate(video),
                                        size="sm", flex=4, color="#666666"
                                    )
                                ]
                            )
                        ]
                    )
                ]
            ),
            footer=FlexBox(
                layout="vertical",
                spacing="sm",
                contents=[
                    FlexButton(
                        text="觀看影片",
                        action=URIAction(label="觀看影片", uri=video['url']),
                        style="primary",
                        color="#1DB446"
                    )
                ]
            )
        )
        bubbles.append(bubble)

    return FlexMessage(
        alt_text=f"{title} Top {len(bubbles)}",
        contents=FlexCarousel(contents=bubbles)
    )

def create_engagement_carousel(videos, title="ETF 互動排行"):
    """創建包含日均觀看次數和互動比率的 LINE Carousel 訊息"""
    if not videos:
        return TextMessage(text="抱歉，沒有找到相關的ETF影片 😅")

    bubbles = []
    for i, video in enumerate(videos[:12]):  # LINE限制最多12個項目
        bubble = FlexBubble(
            hero=FlexImage(
                url=video['thumbnail'],
                size="full",
                aspect_ratio="16:9",
                aspect_mode="cover"
            ),
            body=FlexBox(
                layout="vertical",
                spacing="sm",
                contents=[
                    FlexText(
                        text=f"#{i+1}",
                        weight="bold",
                        size="sm",
                        color="#FF4081"
                    ),
                    FlexText(
                        text=video['title'],
                        weight="bold",
                        size="md",
                        wrap=True,
                        max_lines=2
                    ),
                    FlexText(
                        text=video['channel_title'],
                        size="sm",
                        color="#666666",
                        wrap=True
                    ),
                    FlexSeparator(margin="md"),
                    FlexBox(
                        layout="vertical",
                        spacing="sm",
                        margin="md",
                        contents=[
                            FlexBox(
                                layout="baseline",
                                spacing="sm",
                                contents=[
                                    FlexText(text="📊", size="sm", flex=1),
                                    FlexText(
                                        text=f"{video.get('view_per_day', 0):.0f} 次/天",
                                        size="sm", flex=4, color="#FF4081", weight="bold"
                                    )
                                ]
                            ),
                            FlexBox(
                                layout="baseline",
                                spacing="sm",
                                contents=[
                                    FlexText(text="🔥", size="sm", flex=1),
                                    FlexText(
                                        text=f"{video.get('engagement_rate', 0):.2f}%",
                                        size="sm", flex=4, color="#FF4081", weight="bold"
                                    )
                                ]
                            ),
                            FlexBox(
                                layout="baseline",
                                spacing="sm",
                                contents=[
                                    FlexText(text="👀", size="sm", flex=1),
                                    FlexText(
                                        text=youtube_bot._format_number(video['view_count']),
                                        size="sm", flex=4, color="#666666"
                                    )
                                ]
                            ),
                            FlexBox(
                                layout="baseline",
                                spacing="sm",
                                contents=[
                                    FlexText(text="📅", size="sm", flex=1),
                                    FlexText(
                                        text=youtube_bot._format_publish_time(video['published_at']),
                                        size="sm", flex=4, color="#666666"
                                    )
                                ]
                            )
                        ]
                    )
                ]
            ),
            footer=FlexBox(
                layout="vertical",
                spacing="sm",
                contents=[
                    FlexButton(
                        text="觀看影片",
                        action=URIAction(label="觀看影片", uri=video['url']),
                        style="primary",
                        color="#FF4081"
                    )
                ]
            )
        )
        bubbles.append(bubble)

    return FlexMessage(
        alt_text=f"{title} Top {len(bubbles)}",
        contents=FlexCarousel(contents=bubbles)
    )

def create_text_list(videos, title="ETF 影片清單"):
    """創建文字清單格式的影片列表"""
    if not videos:
        return "抱歉，沒有找到相關的ETF影片 😅"

    text_list = f"📋 {title}\n\n"

    for i, video in enumerate(videos[:12], 1):
        # 格式化觀看次數
        views = youtube_bot._format_number(video['view_count'])
        # 格式化發布時間
        time_str = youtube_bot._format_publish_time(video['published_at'])
        # 計算日均觀看（如果有的話）
        daily_views = video.get('view_per_day', 0)

        # 排名顯示（前3名特殊標記）
        if i == 1:
            rank_emoji = "🥇"
        elif i == 2:
            rank_emoji = "🥈"
        elif i == 3:
            rank_emoji = "🥉"
        else:
            rank_emoji = f"#{i}"

        text_list += f"{rank_emoji} {video['title']}\n"
        text_list += f"📺 {video['channel_title']}\n"
        text_list += f"👀 {views} 次觀看"

        # 如果有日均觀看數據，顯示它
        if daily_views > 0:
            text_list += f" (📊 {daily_views:.0f}/天)"

        text_list += f" | ⏰ {time_str}\n"
        text_list += f"🔗 {video['url']}\n\n"

    # 添加提示訊息
    text_list += "💡 點擊連結即可觀看影片！"

    return text_list

def create_quick_reply():
    """創建快速回覆按鈕"""
    return QuickReply(
        items=[
            QuickReplyItem(
                action=MessageAction(label="🚀 主動式ETF", text="主動式ETF")
            ),
            QuickReplyItem(
                action=MessageAction(label="⚖️ 資產配置ETF", text="資產配置ETF")
            ),
            QuickReplyItem(
                action=MessageAction(label="📈 市值型ETF", text="市值型ETF")
            ),
            QuickReplyItem(
                action=MessageAction(label="💰 高股息ETF", text="高股息ETF")
            ),
            QuickReplyItem(
                action=MessageAction(label="🇨🇳 陸股ETF", text="陸股ETF")
            ),
            QuickReplyItem(
                action=MessageAction(label="🔥 ETF日均觀看排行", text="ETF日均觀看排行")
            ),
            QuickReplyItem(
                action=MessageAction(label="🎓 教育分類日均排行", text="教育頻道")
            ),
            QuickReplyItem(
                action=MessageAction(label="❓ 說明", text="說明")
            )
        ]
    )

@app.route("/webhook", methods=['POST'])
def callback():
    signature = request.headers['X-Line-Signature']
    body = request.get_data(as_text=True)
    
    try:
        handler.handle(body, signature)
    except InvalidSignatureError:
        abort(400)
    
    return 'OK'

@handler.add(MessageEvent, message=TextMessageContent)
def handle_message(event):
    user_message = event.message.text.lower()
    
    try:
        if any(keyword in user_message for keyword in ['嗨', 'hi', 'hello', '你好', '開始']):
            reply_text = """🤖 YouTube ETF 搜尋機器人
我可以幫你搜尋最新的台灣ETF相關影片！

📱 使用方式：
• 「ETF日均觀看排行」- 2日內日均觀看次數最高的ETF影片
• 各類ETF分類選項- 7日內日均觀看排行
• 「教育分類」- 2日內教育頻道熱門影片
• 「說明」- 查看詳細說明
"""
            
            line_bot_api.reply_message(
                ReplyMessageRequest(
                    reply_token=event.reply_token,
                    messages=[TextMessage(text=reply_text, quick_reply=create_quick_reply())]
                )
            )
            

        elif '主動式' in user_message or '主動式etf' in user_message:
            # 立即回覆用戶正在處理中
            line_bot_api.reply_message(
                ReplyMessageRequest(
                    reply_token=event.reply_token,
                    messages=[TextMessage(text="🔍 搜尋7日內主動式ETF日均觀看排行中，請稍候...")]
                )
            )

            # 執行耗時的搜尋操作
            try:
                videos = youtube_bot.get_etf_videos_by_category('active', hours_ago=168, max_results=12)
                if videos:
                    carousel = create_engagement_carousel(videos, "主動式ETF 7日日均觀看排行前12名")
                    text_list = create_text_list(videos, "主動式ETF 7日日均觀看排行前12名")
                    tip_message = TextMessage(text="💡 試試其他分類：", quick_reply=create_quick_reply())
                    line_bot_api.push_message(
                        PushMessageRequest(
                            to=event.source.user_id,
                            messages=[carousel, TextMessage(text=text_list), tip_message]
                        )
                    )
                else:
                    line_bot_api.push_message(
                        PushMessageRequest(
                            to=event.source.user_id,
                            messages=[TextMessage(
                                text="🔍 目前沒有找到符合條件的主動式ETF影片，可能是：\n1. YouTube API配額已用完\n2. 近期沒有熱門主動式ETF影片\n\n請稍後再試或選擇其他分類！",
                                quick_reply=create_quick_reply()
                            )]
                        )
                    )
            except Exception as e:
                print(f"主動式ETF搜尋錯誤: {e}")
                line_bot_api.push_message(
                    PushMessageRequest(
                        to=event.source.user_id,
                        messages=[TextMessage(
                            text="⚠️ 搜尋時發生錯誤，請稍後再試或選擇其他分類！",
                            quick_reply=create_quick_reply()
                        )]
                    )
                )

        elif '資產配置' in user_message or '資產配置etf' in user_message:
            # 立即回覆用戶正在處理中
            line_bot_api.reply_message(
                ReplyMessageRequest(
                    reply_token=event.reply_token,
                    messages=[TextMessage(text="🔍 搜尋7日內資產配置ETF日均觀看排行中，請稍候...")]
                )
            )

            # 執行耗時的搜尋操作
            try:
                videos = youtube_bot.get_etf_videos_by_category('allocation', hours_ago=168, max_results=12)
                if videos:
                    carousel = create_engagement_carousel(videos, "資產配置ETF 7日日均觀看排行前12名")
                    text_list = create_text_list(videos, "資產配置ETF 7日日均觀看排行前12名")
                    tip_message = TextMessage(text="💡 試試其他分類：", quick_reply=create_quick_reply())
                    line_bot_api.push_message(
                        PushMessageRequest(
                            to=event.source.user_id,
                            messages=[carousel, TextMessage(text=text_list), tip_message]
                        )
                    )
                else:
                    line_bot_api.push_message(
                        PushMessageRequest(
                            to=event.source.user_id,
                            messages=[TextMessage(
                                text="🔍 目前沒有找到符合條件的資產配置ETF影片，可能是：\n1. YouTube API配額已用完\n2. 近期沒有熱門資產配置ETF影片\n\n請稍後再試或選擇其他分類！",
                                quick_reply=create_quick_reply()
                            )]
                        )
                    )
            except Exception as e:
                print(f"資產配置ETF搜尋錯誤: {e}")
                line_bot_api.push_message(
                    PushMessageRequest(
                        to=event.source.user_id,
                        messages=[TextMessage(
                            text="⚠️ 搜尋時發生錯誤，請稍後再試或選擇其他分類！",
                            quick_reply=create_quick_reply()
                        )]
                    )
                )

        elif '市值型' in user_message or '市值型etf' in user_message:
            # 立即回覆用戶正在處理中
            line_bot_api.reply_message(
                ReplyMessageRequest(
                    reply_token=event.reply_token,
                    messages=[TextMessage(text="🔍 搜尋7日內市值型ETF日均觀看排行中，請稍候...")]
                )
            )

            # 執行耗時的搜尋操作
            try:
                videos = youtube_bot.get_etf_videos_by_category('market_cap', hours_ago=168, max_results=12)
                if videos:
                    carousel = create_engagement_carousel(videos, "市值型ETF 7日日均觀看排行前12名")
                    text_list = create_text_list(videos, "市值型ETF 7日日均觀看排行前12名")
                    tip_message = TextMessage(text="💡 試試其他分類：", quick_reply=create_quick_reply())
                    line_bot_api.push_message(
                        PushMessageRequest(
                            to=event.source.user_id,
                            messages=[carousel, TextMessage(text=text_list), tip_message]
                        )
                    )
                else:
                    line_bot_api.push_message(
                        PushMessageRequest(
                            to=event.source.user_id,
                            messages=[TextMessage(
                                text="🔍 目前沒有找到符合條件的市值型ETF影片，可能是：\n1. YouTube API配額已用完\n2. 近期沒有熱門市值型ETF影片\n\n請稍後再試或選擇其他分類！",
                                quick_reply=create_quick_reply()
                            )]
                        )
                    )
            except Exception as e:
                print(f"市值型ETF搜尋錯誤: {e}")
                line_bot_api.push_message(
                    PushMessageRequest(
                        to=event.source.user_id,
                        messages=[TextMessage(
                            text="⚠️ 搜尋時發生錯誤，請稍後再試或選擇其他分類！",
                            quick_reply=create_quick_reply()
                        )]
                    )
                )

        elif '高股息' in user_message or '高股息etf' in user_message:
            # 立即回覆用戶正在處理中
            line_bot_api.reply_message(
                ReplyMessageRequest(
                    reply_token=event.reply_token,
                    messages=[TextMessage(text="🔍 搜尋7日內高股息ETF日均觀看排行中，請稍候...")]
                )
            )

            # 執行耗時的搜尋操作
            try:
                videos = youtube_bot.get_etf_videos_by_category('dividend', hours_ago=168, max_results=12)
                if videos:
                    carousel = create_engagement_carousel(videos, "高股息ETF 7日日均觀看排行前12名")
                    text_list = create_text_list(videos, "高股息ETF 7日日均觀看排行前12名")
                    tip_message = TextMessage(text="💡 試試其他分類：", quick_reply=create_quick_reply())
                    line_bot_api.push_message(
                        PushMessageRequest(
                            to=event.source.user_id,
                            messages=[carousel, TextMessage(text=text_list), tip_message]
                        )
                    )
                else:
                    line_bot_api.push_message(
                        PushMessageRequest(
                            to=event.source.user_id,
                            messages=[TextMessage(
                                text="🔍 目前沒有找到符合條件的高股息ETF影片，可能是：\n1. YouTube API配額已用完\n2. 近期沒有熱門高股息ETF影片\n\n請稍後再試或選擇其他分類！",
                                quick_reply=create_quick_reply()
                            )]
                        )
                    )
            except Exception as e:
                print(f"高股息ETF搜尋錯誤: {e}")
                line_bot_api.push_message(
                    PushMessageRequest(
                        to=event.source.user_id,
                        messages=[TextMessage(
                            text="⚠️ 搜尋時發生錯誤，請稍後再試或選擇其他分類！",
                            quick_reply=create_quick_reply()
                        )]
                    )
                )

        elif '陸股' in user_message or '陸股etf' in user_message or '中國' in user_message:
            # 立即回覆用戶正在處理中
            line_bot_api.reply_message(
                ReplyMessageRequest(
                    reply_token=event.reply_token,
                    messages=[TextMessage(text="🔍 搜尋7日內陸股ETF日均觀看排行中，請稍候...")]
                )
            )

            # 執行耗時的搜尋操作
            try:
                videos = youtube_bot.get_etf_videos_by_category('china_stock', hours_ago=168, max_results=12)
                if videos:
                    carousel = create_engagement_carousel(videos, "陸股ETF 7日日均觀看排行前12名")
                    text_list = create_text_list(videos, "陸股ETF 7日日均觀看排行前12名")
                    tip_message = TextMessage(text="💡 試試其他分類：", quick_reply=create_quick_reply())
                    line_bot_api.push_message(
                        PushMessageRequest(
                            to=event.source.user_id,
                            messages=[carousel, TextMessage(text=text_list), tip_message]
                        )
                    )
                else:
                    line_bot_api.push_message(
                        PushMessageRequest(
                            to=event.source.user_id,
                            messages=[TextMessage(
                                text="🔍 目前沒有找到符合條件的陸股ETF影片，可能是：\n1. YouTube API配額已用完\n2. 近期沒有熱門陸股ETF影片\n\n請稍後再試或選擇其他分類！",
                                quick_reply=create_quick_reply()
                            )]
                        )
                    )
            except Exception as e:
                print(f"陸股ETF搜尋錯誤: {e}")
                line_bot_api.push_message(
                    PushMessageRequest(
                        to=event.source.user_id,
                        messages=[TextMessage(
                            text="⚠️ 搜尋時發生錯誤，請稍後再試或選擇其他分類！",
                            quick_reply=create_quick_reply()
                        )]
                    )
                )

        elif 'ETF日均觀看排行' in user_message or '互動' in user_message or 'engagement' in user_message:
            # 立即回覆用戶正在處理中
            line_bot_api.reply_message(
                ReplyMessageRequest(
                    reply_token=event.reply_token,
                    messages=[TextMessage(text="🔍 搜尋3日內ETF日均觀看排行中，請稍候...")]
                )
            )

            # 執行耗時的搜尋操作
            try:
                videos = youtube_bot.get_etf_videos_by_engagement(hours_ago=72, max_results=12)
                if videos:
                    carousel = create_engagement_carousel(videos, "ETF 3日日均觀看排行前12名 (含互動比率)")
                    text_list = create_text_list(videos, "ETF 3日日均觀看排行前12名")
                    search_info = TextMessage(text="🔍 已完成搜尋3日內ETF影片，按日均觀看次數排序")
                    tip_message = TextMessage(text="💡 試試其他分類：", quick_reply=create_quick_reply())
                    line_bot_api.push_message(
                        PushMessageRequest(
                            to=event.source.user_id,
                            messages=[carousel, TextMessage(text=text_list), search_info, tip_message]
                        )
                    )
                else:
                    line_bot_api.push_message(
                        PushMessageRequest(
                            to=event.source.user_id,
                            messages=[TextMessage(
                                text="🔍 目前沒有找到符合條件的ETF影片，可能是：\n1. YouTube API配額已用完\n2. 近期沒有熱門ETF影片\n\n請稍後再試或選擇其他分類！",
                                quick_reply=create_quick_reply()
                            )]
                        )
                    )
            except Exception as e:
                print(f"ETF日均觀看搜尋錯誤: {e}")
                line_bot_api.push_message(
                    PushMessageRequest(
                        to=event.source.user_id,
                        messages=[TextMessage(
                            text="⚠️ 搜尋時發生錯誤，請稍後再試或選擇其他分類！",
                            quick_reply=create_quick_reply()
                        )]
                    )
                )


        elif '教育頻道' in user_message or '教育' in user_message:
            # 立即回覆用戶正在處理中
            line_bot_api.reply_message(
                ReplyMessageRequest(
                    reply_token=event.reply_token,
                    messages=[TextMessage(text="🔍 搜尋3日內教育分類日均觀看排行中，請稍候...")]
                )
            )

            # 執行耗時的搜尋操作
            try:
                videos = youtube_bot.get_etf_videos_by_special_categories(hours_ago=72, max_results=12)
                if videos:
                    carousel = create_engagement_carousel(videos, "教育分類 3日日均觀看排行前12名 (新聞+教育)")
                    text_list = create_text_list(videos, "教育分類 3日日均觀看排行前12名")
                    tip_message = TextMessage(text="💡 試試其他分類：", quick_reply=create_quick_reply())
                    line_bot_api.push_message(
                        PushMessageRequest(
                            to=event.source.user_id,
                            messages=[carousel, TextMessage(text=text_list), tip_message]
                        )
                    )
                else:
                    line_bot_api.push_message(
                        PushMessageRequest(
                            to=event.source.user_id,
                            messages=[TextMessage(
                                text="🔍 目前沒有找到符合條件的教育頻道影片，可能是：\n1. YouTube API配額已用完\n2. 教育分類中近期沒有相關影片\n3. 地區限制問題\n\n請稍後再試或選擇其他分類！",
                                quick_reply=create_quick_reply()
                            )]
                        )
                    )
            except Exception as e:
                print(f"教育頻道搜尋錯誤: {e}")
                line_bot_api.push_message(
                    PushMessageRequest(
                        to=event.source.user_id,
                        messages=[TextMessage(
                            text="⚠️ 教育頻道搜尋時發生錯誤，請稍後再試或選擇其他分類！",
                            quick_reply=create_quick_reply()
                        )]
                    )
                )

        elif '說明' in user_message or 'help' in user_message:
            help_text = """📖 功能說明

🔍 搜尋功能：
• ETF日均觀看排行：按日均觀看次數排序
• ETF分類搜尋：主動式、資產配置、市值型、高股息、陸股
• 教育頻道：教育和財經內容

💡 搜尋範圍：
• 台灣ETF相關影片
• 0050、0056等熱門ETF
• 投資理財頻道內容

⚡ 快速指令：
點擊下方按鈕或輸入「ETF日均觀看排行」即可快速搜尋！

🤖 隨時輸入「嗨」重新開始！"""
            
            line_bot_api.reply_message(
                ReplyMessageRequest(
                    reply_token=event.reply_token,
                    messages=[TextMessage(text=help_text, quick_reply=create_quick_reply())]
                )
            )

"""            
        else:
            # 默認搜尋觀看次數排行
            videos = youtube_bot.get_recent_etf_videos(hours_ago=48, max_results=10)
            if videos:
                carousel = create_etf_carousel(videos, "ETF熱門影片排行")
                tip_message = TextMessage(text="💡 試試其他選項：", quick_reply=create_quick_reply())
                line_bot_api.reply_message(
                    ReplyMessageRequest(
                        reply_token=event.reply_token,
                        messages=[carousel, tip_message]
                    )
                )
            else:
                line_bot_api.reply_message(
                    ReplyMessageRequest(
                        reply_token=event.reply_token,
                        messages=[TextMessage(
                            text="抱歉，目前沒有找到相關的ETF影片 😅\n\n請試試輸入「說明」查看使用方式！",
                            quick_reply=create_quick_reply()
                        )]
                    )
                )
"""
                
    except Exception as e:
        print(f"處理訊息錯誤: {e}")
        try:
            # 嘗試用 reply message，如果失敗再用 push message
            line_bot_api.reply_message(
                ReplyMessageRequest(
                    reply_token=event.reply_token,
                    messages=[TextMessage(
                        text="抱歉，處理請求時發生錯誤 😅\n請稍後再試或輸入「說明」查看使用方式！",
                        quick_reply=create_quick_reply()
                    )]
                )
            )
        except Exception as reply_error:
            print(f"回覆訊息也失敗，使用push message: {reply_error}")
            try:
                line_bot_api.push_message(
                    PushMessageRequest(
                        to=event.source.user_id,
                        messages=[TextMessage(
                            text="⚠️ 系統發生錯誤，請稍後再試！",
                            quick_reply=create_quick_reply()
                        )]
                    )
                )
            except Exception as push_error:
                print(f"Push message也失敗: {push_error}")

if __name__ == "__main__":
    # 開發環境
    app.run(host="0.0.0.0", port=5000, debug=True)
    
    # 生產環境 (使用 gunicorn)
    # gunicorn -w 4 -b 0.0.0.0:5000 line_bot_youtube:app