#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
硬編碼版本 - YouTube ETF LINE Bot 測試程式
直接在程式中填入 API 金鑰，避免環境變數問題
"""

# 🔑 直接填入你的 API 金鑰（從 .env 檔案複製過來）
YOUTUBE_API_KEY = "AIzaSyATaXT_Izy9Br1dc89ETbJdWr23QwIRLRU"
LINE_CHANNEL_SECRET = "2182664bb8d79c7cc961fc763ef16f8b"
LINE_CHANNEL_ACCESS_TOKEN = "Jn4s9KLf2Bd4n7QAUNFOOXW3AmpSF3BujMcf66rC7J48OrCHSliELElg2wKES04D/+WasxjP4vjKXpo1//KLGZcmhPZohfnrvQYcH5eduFhCjyPm1RlTY+cZSgPT1PLlkUwROGWqulGdySo6rW+ecQdB04t89/1O/w1cDnyilFU="

from datetime import datetime, timedelta

def test_youtube_api():
    """測試 YouTube API"""
    print("🧪 測試 YouTube API...")
    
    try:
        from googleapiclient.discovery import build
        
        if not YOUTUBE_API_KEY or YOUTUBE_API_KEY == "YOUR_YOUTUBE_API_KEY":
            print("❌ YouTube API 金鑰未設定")
            return False
        
        youtube = build('youtube', 'v3', developerKey=YOUTUBE_API_KEY)
        
        # 測試搜尋
        request = youtube.search().list(
            part='snippet',
            q='0050 ETF',
            type='video',
            maxResults=3
        )
        response = request.execute()
        
        if response['items']:
            print("✅ YouTube API 連接成功！")
            print(f"   找到 {len(response['items'])} 個搜尋結果")
            for i, item in enumerate(response['items'], 1):
                title = item['snippet']['title'][:50]
                print(f"   {i}. {title}...")
            return True
        else:
            print("⚠️  API 可用但無搜尋結果")
            return True
            
    except ImportError as e:
        print(f"❌ 缺少套件: {e}")
        print("💡 請安裝: pip install google-api-python-client")
        return False
    except Exception as e:
        print(f"❌ YouTube API 錯誤: {e}")
        return False

def test_etf_search():
    """測試完整的 ETF 搜尋功能"""
    print("\n🔍 測試 ETF 影片搜尋...")
    
    try:
        from googleapiclient.discovery import build
        
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
            maxResults=5
        )
        search_response = search_request.execute()
        
        video_ids = [item['id']['videoId'] for item in search_response['items']]
        
        if video_ids:
            # 獲取詳細統計
            videos_request = youtube.videos().list(
                part='snippet,statistics',
                id=','.join(video_ids)
            )
            videos_response = videos_request.execute()
            
            print("✅ 找到最近的 ETF 影片:")
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
            print("⚠️  沒有找到最近 48 小時的 ETF 影片")
            print("💡 試試搜尋更長時間範圍...")
            
            # 嘗試搜尋一週內的影片
            time_ago = now - timedelta(days=7)
            published_after = time_ago.strftime('%Y-%m-%dT%H:%M:%SZ')
            
            search_request = youtube.search().list(
                part='snippet',
                q='ETF 台灣',
                type='video',
                order='viewCount',
                publishedAfter=published_after,
                regionCode='TW',
                maxResults=3
            )
            search_response = search_request.execute()
            
            if search_response['items']:
                print("✅ 找到一週內的 ETF 影片")
                
                # 獲取統計資料
                video_ids = [item['id']['videoId'] for item in search_response['items']]
                videos_request = youtube.videos().list(
                    part='snippet,statistics',
                    id=','.join(video_ids)
                )
                videos_response = videos_request.execute()
                
                for i, item in enumerate(videos_response['items'], 1):
                    title = item['snippet']['title']
                    channel = item['snippet']['channelTitle']
                    views = item['statistics'].get('viewCount', '0')
                    print(f"\n{i}. 📺 {title[:50]}...")
                    print(f"   👤 {channel}")
                    print(f"   👀 {format_number(int(views))} 觀看")
                
                return True
            else:
                print("❌ 完全沒有找到 ETF 相關影片")
                return False
            
    except Exception as e:
        print(f"❌ ETF 搜尋錯誤: {e}")
        return False

def test_line_bot():
    """測試 LINE Bot 設定"""
    print("\n🤖 測試 LINE Bot 設定...")
    
    # 檢查金鑰格式
    if not LINE_CHANNEL_SECRET or len(LINE_CHANNEL_SECRET) != 32:
        print("❌ LINE_CHANNEL_SECRET 格式不正確（應該是32字符）")
        return False
    
    if not LINE_CHANNEL_ACCESS_TOKEN or len(LINE_CHANNEL_ACCESS_TOKEN) < 100:
        print("❌ LINE_CHANNEL_ACCESS_TOKEN 格式不正確（應該很長）")
        return False
    
    print("✅ LINE Bot 金鑰格式正確")
    
    # 測試 LINE Bot SDK
    try:
        from linebot import LineBotApi, WebhookHandler
        
        line_bot_api = LineBotApi(LINE_CHANNEL_ACCESS_TOKEN)
        handler = WebhookHandler(LINE_CHANNEL_SECRET)
        
        print("✅ LINE Bot SDK 初始化成功")
        return True
    except ImportError:
        print("⚠️  line-bot-sdk 未安裝")
        print("💡 請安裝: pip install line-bot-sdk")
        return False
    except Exception as e:
        print(f"❌ LINE Bot 初始化錯誤: {e}")
        return False

def format_number(num):
    """格式化數字"""
    if num >= 1000000:
        return f"{num/1000000:.1f}M"
    elif num >= 1000:
        return f"{num/1000:.1f}K"
    return str(num)

def main():
    print("🚀 YouTube ETF LINE Bot 完整測試")
    print("=" * 50)
    
    print("🔑 使用的 API 金鑰:")
    print(f"YOUTUBE_API_KEY: {YOUTUBE_API_KEY[:10]}...({len(YOUTUBE_API_KEY)} 字符)")
    print(f"LINE_CHANNEL_SECRET: {LINE_CHANNEL_SECRET[:10]}...({len(LINE_CHANNEL_SECRET)} 字符)")
    print(f"LINE_CHANNEL_ACCESS_TOKEN: {LINE_CHANNEL_ACCESS_TOKEN[:10]}...({len(LINE_CHANNEL_ACCESS_TOKEN)} 字符)")
    
    # 執行所有測試
    youtube_basic = test_youtube_api()
    youtube_etf = test_etf_search() if youtube_basic else False
    line_ok = test_line_bot()
    
    print("\n" + "=" * 50)
    print("📋 測試結果總結:")
    print(f"✅ YouTube API 基本功能: {'通過' if youtube_basic else '失敗'}")
    print(f"✅ ETF 搜尋功能: {'通過' if youtube_etf else '失敗'}")
    print(f"✅ LINE Bot 設定: {'通過' if line_ok else '失敗'}")
    
    if youtube_basic and youtube_etf and line_ok:
        print("\n🎉 所有測試通過！")
        print("💡 你的 LINE Bot 功能完全正常")
        print("📱 下一步: 設定 ngrok 和 webhook")
        print("\n🔧 建議的部署步驟:")
        print("1. 下載並安裝 ngrok")
        print("2. 執行 LINE Bot 主程式")
        print("3. 用 ngrok 建立公開 URL")
        print("4. 在 LINE Developers Console 設定 webhook")
        print("5. 測試機器人功能")
        
    elif youtube_basic and youtube_etf:
        print("\n⚠️  YouTube 功能完全正常")
        print("💡 需要安裝 LINE Bot SDK")
        print("🚀 執行: pip install line-bot-sdk")
    else:
        print("\n❌ 有功能需要修復")
        if not youtube_basic:
            print("💡 檢查 YouTube API 金鑰和網路連接")
        if not line_ok:
            print("💡 檢查 LINE Bot 金鑰設定")
    
    print(f"\n🕒 測試完成時間: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

if __name__ == "__main__":
    main()