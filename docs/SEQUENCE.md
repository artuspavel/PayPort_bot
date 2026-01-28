# Sequence Diagram (текстовое описание)

## 1. Респондент → Анкета

```
User → Bot: /start <invite_code>
Bot → User: "Device verification" + WebApp button
User → WebApp: open /fingerprint
WebApp → /api/fingerprint: send fingerprint data
Fingerprint server → DB: save fingerprint
Fingerprint server → User: Continue button (fallback)
User → Bot: web_app_data (verified, fp_id)
Bot → DB: start questionnaire
Bot → User: Question 1
...
User → Bot: Answer 31
Bot → DB: complete questionnaire
Bot → Operator: docx + fingerprint info + matches
```

## 2. Оператор → Invite

```
Operator → Bot: /start
Bot → Operator: menu
Operator → Bot: "Create invite"
Bot → Operator: select language
Operator → Bot: optional description
Bot → DB: create invite
Bot → Operator: invite link
```

## 3. Админ → Просмотр анкет

```
Admin → Bot: /start
Bot → Admin: admin menu
Admin → Bot: "All questionnaires"
Bot → DB: fetch all questionnaires
Bot → Admin: list with filters
```

