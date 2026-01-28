# ER‑диаграмма (логическая модель)

```
users
 ├─ id (PK)
 ├─ telegram_id (UNIQUE)
 ├─ username (UNIQUE)
 ├─ is_admin
 ├─ is_active
 └─ created_at

invites
 ├─ id (PK)
 ├─ operator_id (FK → users.id)
 ├─ invite_code (UNIQUE)
 ├─ description
 ├─ language
 └─ created_at

questionnaires
 ├─ id (PK)
 ├─ invite_id (FK → invites.id)
 ├─ respondent_telegram_id
 ├─ respondent_username
 ├─ respondent_name
 ├─ answers_json
 ├─ status
 ├─ created_at
 └─ completed_at

questions
 ├─ id (PK)
 ├─ order_num
 ├─ text (JSON: ru/en/ar)
 ├─ key (UNIQUE)
 └─ is_active

fingerprints
 ├─ id (PK)
 ├─ telegram_id
 ├─ questionnaire_id (FK → questionnaires.id)
 ├─ ip_address
 ├─ user_agent
 ├─ screen_resolution
 ├─ timezone
 ├─ language
 ├─ platform
 ├─ canvas_hash
 ├─ webgl_hash
 ├─ fonts_hash
 ├─ is_premium
 ├─ raw_data (JSON)
 └─ created_at

pending_verifications
 ├─ telegram_id (PK)
 ├─ invite_id (FK → invites.id)
 └─ created_at
```

## Связи

- `users (1) → (M) invites`
- `invites (1) → (M) questionnaires`
- `questionnaires (1) → (M) fingerprints`
- `invites (1) → (M) pending_verifications`

