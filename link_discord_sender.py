import time
import requests

# 1. ضع رابط الـ Webhook الخاص بك هنا
WEBHOOK_URL = "https://discord.com/api/webhooks/1532707425126191138/GIlmQkKvepyuAjXBHQKtgIeXo0MMjd8z1ghxZTzlUnYf45savt31nLYKFTuWNOpUsZua"

# 2. اسم الملف الذي يحتوي على الروابط
FILE_NAME = "playlist_links.txt"

# 3. التأخير الزمني بين كل رسالة ورسالة (بالثواني) لتجنب الـ Rate Limit
DELAY_SECONDS = 2

def send_links_to_discord():
    links = []
    
    # قراءة الروابط من الملف
    with open(FILE_NAME, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            # التأكد من أن السطر يحتوي على رابط يوتيوب
            if line.startswith("https://"):
                links.append(line)

    print(f"📌 تم العثور على {len(links)} رابط. جاري البدء في الإرسال...\n")

    # إرسال كل رابط في رسالة منفصلة
    for index, link in enumerate(links, start=1):
        payload = {
            "content": link
        }
        
        response = requests.post(WEBHOOK_URL, json=payload)
        
        if response.status_code in [200, 204]:
            print(f"✅ [{index}/{len(links)}] تم إرسال الرابط بنجاح: {link}")
        else:
            print(f"❌ [{index}/{len(links)}] فشل الإرسال (رمز الخطأ: {response.status_code})")
            
        # الانتظار بين الرسائل لتجنب حظر ديسكورد المؤقت
        time.sleep(DELAY_SECONDS)

    print("\n🎉 اكتمل إرسال جميع الروابط!")

if __name__ == "__main__":
    send_links_to_discord()