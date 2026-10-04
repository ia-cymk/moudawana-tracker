import os
import json
from google import genai
from google.genai import types

# جلب المفتاح السري من إعدادات GitHub
API_KEY = os.environ.get("GEMINI_API_KEY")
client = genai.Client(api_key=API_KEY)

def update_news():
    print("جاري جلب أحدث مستجدات مدونة الأسرة...")
    
    prompt = """
    أنت راصد إخباري وباحث قانوني متخصص في تتبع مستجدات تعديل مدونة الأسرة في المغرب.
    ابحث في الويب عن أحدث المستجدات الرسمية.
    شروط صارمة:
    1. اعتمد فقط على: البلاغات الملكية، وكالة المغرب العربي للأنباء (MAP)، الأمانة العامة للحكومة (SGG)، وزارة العدل، والمصادر الموثوقة جداً.
    2. استبعد أي شائعات، تكهنات، أو آراء غير رسمية.
    3. أرجع النتيجة على شكل مصفوفة JSON صالحة (Array of objects) فقط، بدون أي نصوص إضافية، حيث كل كائن يحتوي على:
       - date: (تاريخ الصدور)
       - source: (الجهة المصدرة)
       - title: (عنوان الإجراء)
       - description: (تفاصيل الإجراء)
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
        
        # التأكد من صحة الـ JSON المسترجع
        try:
            json_data = json.loads(response.text)
            
            # حفظ النتيجة في ملف data.json
            with open("data.json", 'w', encoding='utf-8') as f:
                json.dump(json_data, f, ensure_ascii=False, indent=4)
            print("تم تحديث ملف data.json بنجاح.")
        except json.JSONDecodeError:
            print("الرد المستلم ليس بصيغة JSON صالحة.")
            
    except Exception as e:
        print(f"حدث خطأ أثناء التواصل مع API: {e}")

if __name__ == "__main__":
    update_news()
