# import os
# from groq import Groq

# from dotenv import load_dotenv
# load_dotenv()
# client = Groq(api_key=os.environ.get("GROQ_API_KEY"))

# # 2. تحديد مسار الملف (تأكد من صحة المسار في ويندوز)
# filename = "arabic_legal_voice.mp3" 

# # 3. فتح الملف وإرساله للمعالجة
# if os.path.exists(filename):
#     with open(filename, "rb") as file:
#         # ملاحظة: استخدمنا transcriptions وليس translations للحصول على نص عربي
#         transcription = client.audio.transcriptions.create(
#             file=(filename, file.read()), 
#             model="whisper-large-v3", 
#             # model = "whisper-large-v3-turbo"
#             prompt="نص قانوني حول القانون المدني، الرجاء الالتزام بالفصحى", # توجيه النموذج للسياق
#             language="ar", # تحديد اللغة العربية
#             response_format="json",
#             temperature=0.0  
#         )
        
#         # 4. طباعة النص المستخرج بالعربية
#         print("النص المستخرج من Groq:")
#         print("-" * 30)
#         print(transcription.text)
#         print("-" * 30)
# else:
#     print(f"خطأ: الملف {filename} غير موجود في المسار المحدد.")

