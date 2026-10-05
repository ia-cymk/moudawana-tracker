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

    print("جاري جلب المستجدات الرسمية والشائعات...")
    
    prompt = """
    أنت راصد إخباري ومحلل قانوني متخصص في تتبع مستجدات تعديل مدونة الأسرة في المغرب.
    ابحث في الويب بدقة عن مسارين:
    1. المستجدات الرسمية: (البلاغات الملكية، الحكومة، وزارة العدل، البرلمان).
    2. الشائعات والأخبار الكاذبة أو المتداولة غير المؤكدة المنتشرة مؤخراً في شبكات التواصل أو المواقع غير الرسمية.
    
    قم بتحليل النتائج وأرجع مصفوفة JSON صالحة (Array of objects) فقط، بدون نصوص إضافية، بحيث يحتوي كل كائن على:
       - type: نوع الخبر (اختر حصراً: "رسمي" أو "إشاعة")
       - date: (تاريخ الصدور أو التداول كنص، مثال: "4 أكتوبر 2026")
       - source: (الجهة المصدرة للخبر الرسمي، أو مصدر الإشاعة مثل "منصات التواصل")
       - title: (عنوان الإجراء الرسمي أو عنوان الإشاعة)
       - description: (شرح الإجراء، أو تفاصيل الإشاعة ولماذا هي غير صحيحة)
       - summary: (ملخص دقيق في جملة واحدة)
       - tags: (مصفوفة كلمات مفتاحية)
       - status: (للأخبار الرسمية: "قرار نهائي"، "مقترح"... وللشائعات: "إشاعة غير مؤكدة"، "تم النفي رسمياً")
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
                        # تحديد نوع الخبر، وإذا لم يوجد نعتبره رسمياً افتراضياً
                        item['type'] = item.get('type', 'رسمي') 
                        item['status'] = item.get('status', 'مستجد')
                        item['timestamp'] = current_iso_time
                        
                        existing_data.insert(0, item)
                        added_count += 1
            
            if added_count > 0:
                with open("data.json", 'w', encoding='utf-8') as f:
                    json.dump(existing_data, f, ensure_ascii=False, indent=4)
                
                if not os.path.exists("backups"):
                    os.makedirs("backups")
                backup_date = datetime.now().strftime("%Y-%m-%d")
                backup_filename = f"backups/data_backup_{backup_date}.json"
                with open(backup_filename, 'w', encoding='utf-8') as bf:
                    json.dump(existing_data, bf, ensure_ascii=False, indent=4)
                    
                print(f"نجاح: تمت إضافة {added_count} خبر/إشاعة، وتم الحفظ.")
            else:
                print("لم يتم العثور على أي جديد.")
                
        except json.JSONDecodeError:
            print("الرد المستلم ليس بصيغة JSON صالحة.")
            
    except Exception as e:
        print(f"حدث خطأ أثناء التواصل: {e}")

    # (تم الإبقاء على نظام RSS يعمل بشكل طبيعي للأخبار الرسمية)
    if existing_data:
        try:
            rss_items = ""
            # سننشر فقط الأخبار الرسمية في الـ RSS لتجنب نشر الشائعات للمشتركين
            official_data = [item for item in existing_data if item.get('type', 'رسمي') == 'رسمي']
            for item in official_data[:50]:
                title = escape(item.get('title', 'بدون عنوان'))
                link = escape(item.get('link', 'https://ia-cymk.github.io/moudawana-tracker/'))
                desc = escape(item.get('summary', item.get('description', '')))
                pub_date_xml = ""
                if 'timestamp' in item:
                    try:
                        dt = datetime.fromisoformat(item['timestamp'])
                        pub_date_xml = f"<pubDate>{email.utils.format_datetime(dt)}</pubDate>"
                    except:
                        pass
                categories = "".join([f"<category>{escape(tag)}</category>" for tag in item.get('tags', [])])
                rss_items += f"<item><title>{title}</title><link>{link}</link><description>{desc}</description>{pub_date_xml}{categories}</item>"

            rss_feed = f"<?xml version=\"1.0\" encoding=\"UTF-8\" ?>\n<rss version=\"2.0\">\n<channel>\n<title>راصد مدونة الأسرة | المنصة الرسمية</title>\n<link>https://ia-cymk.github.io/moudawana-tracker/</link>\n<description>تتبع المستجدات الرسمية.</description>\n<language>ar</language>\n{rss_items}\n</channel>\n</rss>"
            with open("rss.xml", 'w', encoding='utf-8') as f:
                f.write(rss_feed)
        except Exception as e:
            print(f"خطأ RSS: {e}")

if __name__ == "__main__":
    update_news()
