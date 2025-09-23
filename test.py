# -*- coding: utf-8 -*-
"""
Created on Tue Sep 23 22:45:26 2025

@author: user
"""

#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
快速測試程式 - 測試 YouTube API 和核心功能
不需要 LINE Bot 設定，直接測試搜尋功能
"""

import os
from datetime import datetime, timedelta
from googleapiclient.discovery import build

try:
    from dotenv import load_dotenv
    load_dotenv()
    print("✅ 成功載入 .env 檔案")
except ImportError:
    print("⚠️  python-dotenv 未安裝，使用系統環境變數")

# YouTube API 設定
YOUTUBE_API_KEY = os.getenv('AIzaSyATaXT_Izy9Br1dc89ETbJdWr23QwIRLRU', 'AIzaSyATaXT_Izy9Br1dc89ETbJdWr23QwIRLRU')

def test_youtube_api():
    """測試 YouTube API 連接"""
    print("🧪 測試 YouTube API 連接...")
    
    if YOUTUBE_API_KEY == 'YOUR_YOUTUBE_API_KEY':
        print("❌ YouTube API 金鑰未設定")
        return False
    
    try:
        youtube = build('youtube', 'v3', developerKey=YOUTUBE_API_KEY)
        
        # 簡單測試搜尋
        request = youtube.search().list(
            part='snippet',
            q='0050',
            type='video',
            maxResults=1
        )
        response = request.execute()
        
        if response['items']:
            print("✅ YouTube API 連接成功")
            print(f"   測試影片: {response['items'][0]['snippet']['title']}")
            return True
        else:
            print("❌ YouTube API 無搜尋結果")
            return False
            
    except Exception as e:
        print(f"❌ YouTube API 錯誤: {e}")
        return False

def test_etf_search():
    """測試 ETF 搜尋功能"""
    print("\n🔍 測試 ETF 搜尋功能...")
    
    try:
        youtube = build('youtube', 'v3', developerKey=YOUTUBE_API_KEY)
        
        # 搜尋最近 48 小時的 ETF 影片
        now = datetime.now()
        time_ago = now - timedelta(hours=48)
        published_after = time_ago.strftime('%Y-%m-%dT%H:%M:%SZ')
        
        search_request = youtube.search().list(
            part='snippet',
            q='台灣ETF OR 0050 OR 0056',
            type='video',
            order='viewCount',
            publishedAfter=published_after,
            regionCode='TW',
            maxResults=3
        )
        search_response = search_request.execute()
        
        video_ids = [item['id']['videoId'] for item in search_response['items']]
        
        if video_ids:
            # 獲取詳細資訊
            videos_request = youtube.videos().list(
                part='snippet,statistics',
                id=','.join(video_ids)
            )
            videos_response = videos_request.execute()
            
            print("✅ 找到以下 ETF 相關影片:")
            for i, item in enumerate(videos_response['items'], 1):
                title = item['snippet']['title']
                channel = item['snippet']['channelTitle']
                views = item['statistics'].get('viewCount', '0')
                
                print(f"\n{i}. 📺 {title[:60]}...")
                print(f"   👤 {channel}")
                print(f"   👀 {format_number(int(views))} 觀看")
                print(f"   🔗 https://www.youtube.com/watch?v={item['id']}")
            
            return True
        else:
            print("⚠️  沒有找到最近的 ETF 影片")
            return False
            
    except Exception as e:
        print(f"❌ ETF 搜尋錯誤: {e}")
        return False

def format_number(num):
    """格式化數字"""
    if num >= 1000000:
        return f"{num/1000000:.1f}M"
    elif num >= 1000:
        return f"{num/1000:.1f}K"
    return str(num)

def test_line_bot_setup():
    """測試 LINE Bot 設定"""
    print("\n🤖 檢查 LINE Bot 設定...")
    
    LINE_CHANNEL_SECRET = os.getenv('LINE_CHANNEL_SECRET', 'YOUR_LINE_CHANNEL_SECRET')
    LINE_CHANNEL_ACCESS_TOKEN = os.getenv('LINE_CHANNEL_ACCESS_TOKEN', 'YOUR_LINE_CHANNEL_ACCESS_TOKEN')
    
    secret_ok = LINE_CHANNEL_SECRET != 'YOUR_LINE_CHANNEL_SECRET' and len(LINE_CHANNEL_SECRET) > 10
    token_ok = LINE_CHANNEL_ACCESS_TOKEN != 'YOUR_LINE_CHANNEL_ACCESS_TOKEN' and len(LINE_CHANNEL_ACCESS_TOKEN) > 50
    
    print(f"LINE_CHANNEL_SECRET: {'✅ 已設定' if secret_ok else '❌ 未設定或無效'}")
    print(f"LINE_CHANNEL_ACCESS_TOKEN: {'✅ 已設定' if token_ok else '❌ 未設定或無效'}")
    
    if secret_ok and token_ok:
        print("✅ LINE Bot 設定完整，可以開始測試機器人")
        return True
    else:
        print("⚠️  LINE Bot 設定不完整，只能測試 YouTube 搜尋功能")
        return False

def main():
    print("🚀 LINE Bot YouTube ETF 快速測試")
    print("="*50)
    
    # 測試 YouTube API
    youtube_ok = test_youtube_api()
    
    if youtube_ok:
        # 測試搜尋功能
        search_ok = test_etf_search()
    else:
        search_ok = False
    
    # 檢查 LINE Bot 設定
    line_ok = test_line_bot_setup()
    
    print("\n" + "="*50)
    print("📋 測試結果總結:")
    print(f"YouTube API: {'✅ 通過' if youtube_ok else '❌ 失敗'}")
    print(f"ETF 搜尋功能: {'✅ 通過' if search_ok else '❌ 失敗'}")
    print(f"LINE Bot 設定: {'✅ 完整' if line_ok else '⚠️  不完整'}")
    
    if youtube_ok and search_ok and line_ok:
        print("\n🎉 所有測試通過！你可以開始部署 LINE Bot 了")
        print("💡 下一步：使用 ngrok 測試完整的 LINE Bot 功能")
    elif youtube_ok and search_ok:
        print("\n⚠️  YouTube 功能正常，但需要設定 LINE Bot 金鑰")
        print("💡 請先完成 LINE Developers Console 的設定")
    else:
        print("\n❌ 測試失敗，請檢查設定")
        print("💡 確保 YouTube API 金鑰有效且網路連接正常")

if __name__ == "__main__":
    main()