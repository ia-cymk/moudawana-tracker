import os
import json
from datetime import datetime
import email.utils
from xml.sax.saxutils import escape
from google import genai
from google.genai import types

API_KEY = os.environ.get("GEMINI_API_KEY")
client = genai.Client(api_key=API_KEY)

def update_news():
    print("جاري التحقق من الأخبار القديمة...")
    
    existing_data = []
    if os.path.exists("data.json"):
        try:
            with open("data.json", 'r', encoding='utf-8') as f:
                content = f.read()
                if content.strip():
                    existing_data = json.loads(content)
        except Exception as e:
            print(f"لم يتم العثور على أرشيف سابق: {e}")

    print("جاري جلب وتحليل أحدث مستجدات مدونة الأسرة...")
    
    prompt = """
    أنت راصد إخباري ومحلل قانوني متخصص في تتبع مستجدات تعديل مدونة الأسرة في المغرب.
    ابحث في الويب عن أحدث المستجدات الرسمية. اعتمد فقط على المصادر الموثوقة (البلاغات الملكية، وكالة الأنباء MAP، الحكومة، وزارة العدل) واستبعد الشائعات تماماً.
    
    قم بتحليل الخبر واستخرج منه البيانات التالية. أرجع النتيجة على شكل مصفوفة JSON صالحة (Array of objects) فقط، بدون نصوص إضافية، بحيث يحتوي كل كائن على:
       - date: (تاريخ الصدور كنص، مثال: "4 أكتوبر 2026")
       - source: (الجهة المصدرة)
       - title: (عنوان الإجراء)
       - description: (شرح مبسط وموضوعي للإجراء في سطرين)
       - summary: (ملخص دقيق ومباشر في جملة واحدة فقط)
       - tags: (مصفوفة من 2 إلى 3 كلمات مفتاحية دقيقة، مثال: ["الحضانة", "تعديل قانوني"])
       - status: (طبيعة الإجراء، اختر واحدة من: "مقترح"، "مسودة"، "فتوى"، "قرار نهائي"، "نقاش عام")
       - link: (رابط المصدر)
    """
    
    try:
        response = client.models.generate_content(
            model='gemini-2.5-flash',
            contents=prompt,
            config=types.GenerateContentConfig(
                tools=[{"google_search": {}}], 
                response_mime_type="application/json",
            )
        )
        
        try:
            new_data = json.loads(response.text)
            
            added_count = 0
            existing_links = [item.get('link', '') for item in existing_data]
            existing_titles = [item.get('title', '') for item in existing_data]
            
            current_iso_time = datetime.now().isoformat()
            
            for item in new_data:
                if 'title' in item and 'link' in item:
                    if item.get('link') not in existing_links and item.get('title') not in existing_titles:
                        item['summary'] = item.get('summary', item.get('description', 'لا يوجد ملخص متاح.'))
                        item['tags'] = item.get('tags', ['مدونة الأسرة'])
                        item['status'] = item.get('status', 'مستجد')
                        item['timestamp'] = current_iso_time
                        
                        existing_data.insert(0, item)
                        added_count += 1
            
            if added_count > 0:
                # حفظ JSON
                with open("data.json", 'w', encoding='utf-8') as f:
                    json.dump(existing_data, f, ensure_ascii=False, indent=4)
                
                # حفظ النسخة الاحتياطية
                if not os.path.exists("backups"):
                    os.makedirs("backups")
                backup_date = datetime.now().strftime("%Y-%m-%d")
                backup_filename = f"backups/data_backup_{backup_date}.json"
                with open(backup_filename, 'w', encoding='utf-8') as bf:
                    json.dump(existing_data, bf, ensure_ascii=False, indent=4)
                    
                print(f"نجاح: تمت إضافة {added_count} خبر، وتم أخذ نسخة احتياطية.")
            else:
                print("لم يتم العثور على أخبار جديدة. الأرشيف بأمان ولم يتغير.")
                
        except json.JSONDecodeError:
            print("الرد المستلم ليس بصيغة JSON صالحة.")
            
    except Exception as e:
        print(f"حدث خطأ أثناء التواصل مع API: {e}")

    # --- نظام توليد خلاصة الأخبار (RSS Feed) ---
    if existing_data:
        try:
            print("جاري تحديث ملف خلاصة الأخبار (RSS)...")
            rss_items = ""
            # سنكتفي بآخر 50 خبراً في ملف الـ RSS ليكون خفيفاً وسريعاً
            for item in existing_data[:50]:
                title = escape(item.get('title', 'بدون عنوان'))
                link = escape(item.get('link', 'https://ia-cymk.github.io/moudawana-tracker/'))
                desc = escape(item.get('summary', item.get('description', '')))
                
                # تحويل التاريخ لصيغة RSS العالمية (RFC 822)
                pub_date_xml = ""
                if 'timestamp' in item:
                    try:
                        dt = datetime.fromisoformat(item['timestamp'])
                        pub_date_xml = f"<pubDate>{email.utils.format_datetime(dt)}</pubDate>"
                    except:
                        pass
                
                # إضافة الهاشتاجات كأقسام (Categories)
                categories = "".join([f"<category>{escape(tag)}</category>" for tag in item.get('tags', [])])

                rss_items += f"""
                <item>
                    <title>{title}</title>
                    <link>{link}</link>
                    <description>{desc}</description>
                    {pub_date_xml}
                    {categories}
                </item>"""

            # الهيكل الأساسي لملف XML
            rss_feed = f"""<?xml version="1.0" encoding="UTF-8" ?>
<rss version="2.0">
<channel>
    <title>راصد مدونة الأسرة | المنصة الرسمية</title>
    <link>https://ia-cymk.github.io/moudawana-tracker/</link>
    <description>تتبع مسار تعديل مدونة الأسرة بالمغرب من المصادر الموثوقة.</description>
    <language>ar</language>
    {rss_items}
</channel>
</rss>"""
            
            with open("rss.xml", 'w', encoding='utf-8') as f:
                f.write(rss_feed)
            print("تم إنشاء/تحديث ملف rss.xml بنجاح.")
        except Exception as e:
            print(f"حدث خطأ أثناء إنشاء ملف RSS: {e}")

if __name__ == "__main__":
    update_news()
