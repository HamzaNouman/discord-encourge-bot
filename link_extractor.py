import yt_dlp

def extract_playlist_links(playlist_url, output_file="playlist_links.txt"):
    # إعدادات yt-dlp لاستخراج البيانات فقط دون تحميل الفيديوهات
    ydl_opts = {
        'extract_flat': True,  # استخراج الروابط والمعلومات فقط (سريع جداً)
        'skip_download': True, # عدم تحميل الفيديوهات
        'quiet': False,
    }

    print("جاري جلب روابط قائمة التشغيل...")

    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        # استخراج معلومات البلاي ليست
        info = ydl.extract_info(playlist_url, download=False)

        if 'entries' in info:
            videos = list(info['entries'])
            
            # كتابة الروابط في الملف بالترتيب
            with open(output_file, "w", encoding="utf-8") as f:
                f.write(f"# قائمة تشغيل: {info.get('title', 'بدون عنوان')}\n")
                f.write(f"# إجمالي الفيديوهات: {len(videos)}\n\n")

                for index, entry in enumerate(videos, start=1):
                    # تكوين رابط الفيديو المباشر
                    video_id = entry.get('id')
                    video_title = entry.get('title', 'بدون عنوان')
                    video_url = f"https://www.youtube.com/watch?v={video_id}"

                    # كتابة الترقيم والعنوان والرابط
                    f.write(f"{index}. {video_title}\n")
                    f.write(f"{video_url}\n\n")

            print(f"✅ تم الحفظ بنجاح! تم استخراج {len(videos)} رابط في الملف: {output_file}")
        else:
            print("❌ لم يتم العثور على أي فيديوهات في الرابط المدخل.")

# --- ضع رابط قائمة التشغيل هنا ---
PLAYLIST_URL = "https://www.youtube.com/playlist?list=PLOjvW1C4hDCmd9j1Md5RL9w4dh4EQAj_5"

if __name__ == "__main__":
    extract_playlist_links(PLAYLIST_URL)