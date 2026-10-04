import os
import json
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
    
    # --- هنا التعديل الجوهري في Prompt ---
    prompt = """
    أنت راصد إخباري ومحلل قانوني متخصص في تتبع مستجدات تعديل مدونة الأسرة في المغرب.
    ابحث في الويب عن أحدث المستجدات الرسمية. اعتمد فقط على المصادر الموثوقة (البلاغات الملكية، وكالة الأنباء MAP، الحكومة، وزارة العدل) واستبعد الشائعات تماماً.
    
    قم بتحليل الخبر واستخرج منه البيانات التالية. أرجع النتيجة على شكل مصفوفة JSON صالحة (Array of objects) فقط، بدون نصوص إضافية، بحيث يحتوي كل كائن على:
       - date: (تاريخ الصدور، مثال: "أكتوبر 2026")
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
            
            for item in new_data:
                # التحقق من أن الكائن الجديد يحتوي على البيانات الأساسية لتجنب الأخطاء
                if 'title' in item and 'link' in item:
                    if item.get('link') not in existing_links and item.get('title') not in existing_titles:
                        # التأكد من وجود الحقول الجديدة حتى لا ينهار الموقع إذا نسيها الذكاء الاصطناعي
                        item['summary'] = item.get('summary', item.get('description', 'لا يوجد ملخص متاح.'))
                        item['tags'] = item.get('tags', ['مدونة الأسرة'])
                        item['status'] = item.get('status', 'مستجد')
                        
                        existing_data.insert(0, item)
                        added_count += 1
            
            with open("data.json", 'w', encoding='utf-8') as f:
                json.dump(existing_data, f, ensure_ascii=False, indent=4)
                
            print(f"تم تحليل وتحديث الأرشيف بنجاح. تمت إضافة {added_count} خبر جديد.")
            
        except json.JSONDecodeError:
            print("الرد المستلم ليس بصيغة JSON صالحة.")
            
    except Exception as e:
        print(f"حدث خطأ أثناء التواصل مع API: {e}")

if __name__ == "__main__":
    update_news()
