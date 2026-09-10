# Схема бази даних

Цей документ описує цільову структуру PostgreSQL-бази для Telegram-бота Intima. Візуалізацію схеми можна відкрити або оновити у [dbdiagram.io](https://dbdiagram.io/home), вставивши DBML-код із розділу нижче.

> DBML-схема є документацією структури даних і не містить паролів, токенів чи `DATABASE_URL`.

## Таблиці

### `users`

Telegram-користувачі бота. Запис створюється під час першої дії користувача, зокрема при виконанні `/couple`.

- `id` — внутрішній унікальний ідентифікатор користувача.
- `telegram_id` — унікальний ID користувача в Telegram.
- `username`, `first_name` — необов’язкові дані профілю Telegram.
- `created_at` — дата й час створення запису.

### `categories`

Розділи бота: AI-сексолог, профіль пари, сумісність, картки для розмов, check-in, вправи та insights.

- `id` — унікальний ідентифікатор категорії.
- `code` — унікальний технічний код, наприклад `couple_profile`.
- `title` — назва, яку бачить користувач.
- `description` — короткий опис розділу.
- `created_at` — дата й час створення категорії.

### `couples`

Пари, створені користувачем через команду `/couple`.

- `id` — унікальний ID пари, який бот повертає користувачу.
- `created_by_user_id` — користувач, який створив пару.
- `title` — назва або опис пари, наприклад «Анна та Максим».
- `status` — поточний стан запису, наприклад `active`.
- `created_at` — дата й час створення.

### `couple_members`

Учасники пари. Таблиця дає змогу пов’язати одну пару з одним або двома користувачами Telegram без дублювання даних.

- `couple_id` — пара, до якої належить учасник.
- `user_id` — користувач-учасник.
- `role` — роль у парі, наприклад `partner`.
- `joined_at` — дата й час приєднання.

Комбінація `couple_id` і `user_id` унікальна: одного користувача не можна додати до тієї самої пари двічі.

### `user_transactions`

Історія операцій (дій) користувача у боті. Це не фінансові транзакції: запис відображає, яку функцію бот використав користувач.

- `user_id` — користувач, який виконав дію.
- `category_id` — розділ бота, у якому відбулася дія.
- `couple_id` — пов’язана пара, якщо дія стосується пари.
- `action_type` — тип дії, наприклад `menu_opened`, `card_viewed` або `exercise_started`.
- `selected_profile` — обраний режим: індивідуальний або для пари.
- `content_summary` — короткий опис картки, вправи чи сценарію.
- `created_at` — дата й час операції.

## Зв’язки

- Один `user` може створити багато `couples` через `couples.created_by_user_id`.
- Одна `couple` може мати багато записів у `couple_members`.
- Один `user` може бути учасником багатьох `couples` через `couple_members`.
- Один `user` може мати багато `user_transactions`.
- Одна `category` може бути пов’язана з багатьма `user_transactions`.
- Одна `couple` може бути пов’язана з багатьма `user_transactions`; для індивідуальних дій це поле може бути порожнім.

## DBML для dbdiagram

```dbml
Table users {
  id bigint [pk, increment]
  telegram_id bigint [not null, unique]
  username varchar
  first_name varchar
  created_at timestamp [not null, default: `now()`]
}

Table categories {
  id bigint [pk, increment]
  code varchar [not null, unique]
  title varchar [not null]
  description text
  created_at timestamp [not null, default: `now()`]
}

Table couples {
  id bigint [pk, increment]
  created_by_user_id bigint [not null]
  title varchar
  status varchar [not null, default: 'active']
  created_at timestamp [not null, default: `now()`]
}

Table couple_members {
  id bigint [pk, increment]
  couple_id bigint [not null]
  user_id bigint [not null]
  role varchar [not null, default: 'partner']
  joined_at timestamp [not null, default: `now()`]

  indexes {
    (couple_id, user_id) [unique]
  }
}

Table user_transactions {
  id bigint [pk, increment]
  user_id bigint [not null]
  category_id bigint [not null]
  couple_id bigint
  action_type varchar [not null]
  selected_profile varchar
  content_summary text
  created_at timestamp [not null, default: `now()`]
}

Ref: couples.created_by_user_id > users.id
Ref: couple_members.couple_id > couples.id
Ref: couple_members.user_id > users.id
Ref: user_transactions.user_id > users.id
Ref: user_transactions.category_id > categories.id
Ref: user_transactions.couple_id > couples.id
```

Наразі бот створює та використовує таблиці `users` і `couples`. Решта таблиць описують наступні функції та будуть додані до коду, коли відповідні сценарії бота з’являться.
