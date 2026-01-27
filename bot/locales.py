"""Localization strings for the bot."""

LANGUAGES = {
    "ru": "🇷🇺 Русский",
    "en": "🇬🇧 English",
    "ar": "🇸🇦 العربية"
}

# Example images for passport verification
PASSPORT_EXAMPLE_URL = "https://www.immi.gov.au/media/images/help/photo-id/passport-biographic-700.jpg"
SELFIE_EXAMPLE_URL = "https://www.jumio.com/content/uploads/selfie-id-verification.png"

# Bot interface messages
MESSAGES = {
    "ru": {
        # Questionnaire
        "welcome_questionnaire": "👋 Добро пожаловать в анкету!",
        "topic": "📝 Тема",
        "questions_count": "Вам предстоит ответить на {count} вопросов.",
        "answer_instruction": "Отвечайте текстовыми сообщениями.",
        "media_hint": "📎 Вы также можете отправлять фото, видео и документы.",
        "cancel_instruction": "Для отмены используйте /cancel",
        "lets_start": "Начинаем!",
        "question_of": "Вопрос {current} из {total}:",
        "empty_answer_warning": "⚠️ Пожалуйста, введите ответ текстом.",
        "photo_received": "✅ Фото получено!",
        "video_received": "✅ Видео получено!",
        "document_received": "✅ Документ получен!",
        "thank_you": "✅ **Спасибо за заполнение анкеты!**\n\nВаши ответы сохранены.",
        
        # Passport verification
        "verification_intro": "📋 **Осталось пройти верификацию личности**\n\nЭто необходимо для подтверждения вашей личности.",
        "passport_photo_request": "📸 **Шаг 1 из 2: Фото паспорта**\n\nПришлите фото страницы паспорта с вашими данными (страница с фотографией).\n\n✅ Требования:\n• Фото должно быть чётким и читаемым\n• Все данные должны быть видны полностью\n• Без бликов и размытия",
        "passport_photo_received": "✅ Фото паспорта получено!",
        "passport_selfie_request": "🎥 **Шаг 2 из 2: Селфи-видео с паспортом**\n\nЗапишите короткое видео (5-10 секунд), где вы:\n• Держите открытый паспорт на странице с фото рядом с лицом\n• Паспорт и лицо должны быть хорошо видны\n• Немного поверните голову влево и вправо",
        "passport_selfie_received": "✅ Видео получено!",
        "verification_complete": "🎉 **Верификация завершена!**\n\nСпасибо! Все ваши данные отправлены оператору для проверки.",
        "waiting_photo": "⚠️ Пожалуйста, отправьте фото паспорта.",
        "waiting_video": "⚠️ Пожалуйста, отправьте видео с паспортом.",
        
        # Operator notifications
        "new_questionnaire": "📄 **Новая заполненная анкета!**",
        "respondent": "👤 Респондент",
        "date": "📅 Дата",
        "verification_docs": "🔐 **Документы верификации**",
        "passport_photo_caption": "📸 Фото паспорта",
        "passport_selfie_caption": "🎥 Селфи-видео с паспортом",
        
        # Document
        "doc_title": "Анкета трейдера",
        "doc_generated_by": "Сгенерировано PayPort Questionnaire Bot",
        "no_answer": "Ответ не предоставлен",
        
        # Errors
        "questions_not_found": "❌ Ошибка: вопросы анкеты не найдены. Обратитесь к администратору.",
        "invalid_invite": "❌ Недействительная ссылка-приглашение.\nПопросите отправителя создать новую ссылку.",
    },
    "en": {
        # Questionnaire
        "welcome_questionnaire": "👋 Welcome to the questionnaire!",
        "topic": "📝 Topic",
        "questions_count": "You will need to answer {count} questions.",
        "answer_instruction": "Please respond with text messages.",
        "media_hint": "📎 You can also send photos, videos and documents.",
        "cancel_instruction": "Use /cancel to abort",
        "lets_start": "Let's begin!",
        "question_of": "Question {current} of {total}:",
        "empty_answer_warning": "⚠️ Please enter your answer as text.",
        "photo_received": "✅ Photo received!",
        "video_received": "✅ Video received!",
        "document_received": "✅ Document received!",
        "thank_you": "✅ **Thank you for completing the questionnaire!**\n\nYour answers have been saved.",
        
        # Passport verification
        "verification_intro": "📋 **Identity verification required**\n\nThis is necessary to confirm your identity.",
        "passport_photo_request": "📸 **Step 1 of 2: Passport photo**\n\nPlease send a photo of your passport data page (the page with your photo).\n\n✅ Requirements:\n• Photo must be clear and readable\n• All data must be fully visible\n• No glare or blur",
        "passport_photo_received": "✅ Passport photo received!",
        "passport_selfie_request": "🎥 **Step 2 of 2: Selfie video with passport**\n\nRecord a short video (5-10 seconds) where you:\n• Hold your open passport on the photo page next to your face\n• Both passport and face must be clearly visible\n• Slightly turn your head left and right",
        "passport_selfie_received": "✅ Video received!",
        "verification_complete": "🎉 **Verification complete!**\n\nThank you! All your data has been sent to the operator for review.",
        "waiting_photo": "⚠️ Please send a passport photo.",
        "waiting_video": "⚠️ Please send a video with your passport.",
        
        # Operator notifications
        "new_questionnaire": "📄 **New completed questionnaire!**",
        "respondent": "👤 Respondent",
        "date": "📅 Date",
        "verification_docs": "🔐 **Verification documents**",
        "passport_photo_caption": "📸 Passport photo",
        "passport_selfie_caption": "🎥 Selfie video with passport",
        
        # Document
        "doc_title": "Trader Questionnaire",
        "doc_generated_by": "Generated by PayPort Questionnaire Bot",
        "no_answer": "No answer provided",
        
        # Errors
        "questions_not_found": "❌ Error: questionnaire questions not found. Please contact the administrator.",
        "invalid_invite": "❌ Invalid invitation link.\nPlease ask the sender to create a new link.",
    },
    "ar": {
        # Questionnaire
        "welcome_questionnaire": "👋 مرحباً بك في الاستبيان!",
        "topic": "📝 الموضوع",
        "questions_count": "ستحتاج للإجابة على {count} سؤال.",
        "answer_instruction": "يرجى الرد بالرسائل النصية.",
        "media_hint": "📎 يمكنك أيضاً إرسال صور وفيديوهات ومستندات.",
        "cancel_instruction": "استخدم /cancel للإلغاء",
        "lets_start": "لنبدأ!",
        "question_of": "السؤال {current} من {total}:",
        "empty_answer_warning": "⚠️ يرجى إدخال إجابتك كنص.",
        "photo_received": "✅ تم استلام الصورة!",
        "video_received": "✅ تم استلام الفيديو!",
        "document_received": "✅ تم استلام المستند!",
        "thank_you": "✅ **شكراً لإكمال الاستبيان!**\n\nتم حفظ إجاباتك.",
        
        # Passport verification
        "verification_intro": "📋 **التحقق من الهوية مطلوب**\n\nهذا ضروري لتأكيد هويتك.",
        "passport_photo_request": "📸 **الخطوة 1 من 2: صورة جواز السفر**\n\nيرجى إرسال صورة لصفحة بيانات جواز سفرك (الصفحة التي تحتوي على صورتك).\n\n✅ المتطلبات:\n• يجب أن تكون الصورة واضحة وقابلة للقراءة\n• يجب أن تكون جميع البيانات مرئية بالكامل\n• بدون انعكاس أو ضبابية",
        "passport_photo_received": "✅ تم استلام صورة جواز السفر!",
        "passport_selfie_request": "🎥 **الخطوة 2 من 2: فيديو سيلفي مع جواز السفر**\n\nسجل فيديو قصير (5-10 ثواني) حيث:\n• تحمل جواز سفرك المفتوح على صفحة الصورة بجانب وجهك\n• يجب أن يكون جواز السفر والوجه مرئيين بوضوح\n• قم بتدوير رأسك قليلاً يميناً ويساراً",
        "passport_selfie_received": "✅ تم استلام الفيديو!",
        "verification_complete": "🎉 **اكتمل التحقق!**\n\nشكراً! تم إرسال جميع بياناتك للمشغل للمراجعة.",
        "waiting_photo": "⚠️ يرجى إرسال صورة جواز السفر.",
        "waiting_video": "⚠️ يرجى إرسال فيديو مع جواز سفرك.",
        
        # Operator notifications
        "new_questionnaire": "📄 **استبيان جديد مكتمل!**",
        "respondent": "👤 المستجيب",
        "date": "📅 التاريخ",
        "verification_docs": "🔐 **مستندات التحقق**",
        "passport_photo_caption": "📸 صورة جواز السفر",
        "passport_selfie_caption": "🎥 فيديو سيلفي مع جواز السفر",
        
        # Document
        "doc_title": "استبيان المتداول",
        "doc_generated_by": "تم إنشاؤه بواسطة PayPort Questionnaire Bot",
        "no_answer": "لم يتم تقديم إجابة",
        
        # Errors
        "questions_not_found": "❌ خطأ: لم يتم العثور على أسئلة الاستبيان. يرجى الاتصال بالمسؤول.",
        "invalid_invite": "❌ رابط دعوة غير صالح.\nيرجى طلب رابط جديد من المرسل.",
    }
}


def get_text(lang: str, key: str, **kwargs) -> str:
    """Get localized text by key."""
    text = MESSAGES.get(lang, MESSAGES["en"]).get(key, key)
    if kwargs:
        text = text.format(**kwargs)
    return text
