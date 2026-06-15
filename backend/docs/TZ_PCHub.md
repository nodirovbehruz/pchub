# 📋 Техническое задание: PCHub

> SaaS-платформа управления игровым клубом. Клон SmartShell. Адаптирован под PCHub.
>
> **Источники:** SmartShell API (`apidoc.smartshell.gg`) + 50+ HTML-страниц справки (`d:/PC/картинки/`). Детальные выписки — в `docs/tz_research/group{1..9}_*.md`.

---

## 1. Архитектура — 4 уровня

```
┌──────────────────────────────────────────────────────────────┐
│ 1. ПЛАТФОРМА (PCHub Inc.) — мы                                │
│    • Все клубы, MRR, поддержка                                │
│    • Доступ: is_platform_admin=True                           │
├──────────────────────────────────────────────────────────────┤
│ 2. ВЛАДЕЛЕЦ КЛУБА — наш клиент                                │
│    • Один или несколько клубов (Сеть клубов)                  │
│    • ЛК владельца (отдельный экран)                           │
│    • Подписка: Free / Trial / Starter / Business              │
├──────────────────────────────────────────────────────────────┤
│ 3. СОТРУДНИКИ КЛУБА                                          │
│    • Роли: Менеджер / Оператор / Бухгалтер / Сисадмин /       │
│      Маркетолог / Другой                                      │
│    • Через ClubMembership(user, club, role, is_active)        │
├──────────────────────────────────────────────────────────────┤
│ 4. КЛИЕНТЫ И ГОСТИ                                            │
│    • Регистрируются в Шелле (десктоп) или мобильке SmartGamer │
│    • Депозит в деньгах (₽), бонусы отдельно                   │
└──────────────────────────────────────────────────────────────┘
```

**Подкомпоненты:**
- **Панель управления** (наш React-фронт) — операционная админка
- **ЛК владельца** (наш React-фронт, отдельный маршрут `/cabinet`) — управление клубами, подписками
- **Шелл (Shell)** — клиентское десктоп-приложение (C# уже есть)
- **SmartGamer-аналог** — мобильное приложение клиентов (опционально, фаза 2+)
- **Kiosk** — киоск самообслуживания (опционально, фаза 3)

---

## 2. Модели данных

### 2.1 Уже реализовано в PCHub
- `CustomUser` (UUID PK, phone, email, password, user_type, hardware_id, last_activity)
- `Club` (name, разбитый адрес, owner FK, is_trial, trial_until, contact_*)
- `ClubMembership` (user, club, role, is_active)
- `ComputerGroup` (name, slug, club FK, color, position, is_active)
- `Computer` (name, slug, pc_number, hardware_id, owner, group FK, специ, position_x/y, status, last_seen)
- `ComputerMetrics` (CPU/RAM/диск/сеть, индекс по computer+timestamp)
- `ComputerCommand` (очередь команд install/lock/reboot/WOL и т.д.)
- `ComputerGame` (M2M ПК↔Game с install_path)
- `Game` (с категориями, тегами, executable_path, arguments)
- `GameSession` (account, game, computer, total_hours, current_session_start, session_status)
- `GuestSession` (computer, start/end_time, rate_per_hour, total_amount)
- `ClubAccount` (Steam-логины и т.д.)
- `UserBalance` (minutes_remaining)
- `Payment` (user, computer, admin, amount_paid, minutes_added, payment_method)
- `Shift` (admin, opened_at, closed_at, initial_cash, closing_cash, cash_revenue, card_revenue)
- `TariffPlan` (4 типа, schedule_days/start/end, valid_until_time, life_days, флаги)
- `TariffPrice` (tariff, group, period day/night, price)
- `Product` / `Cart` / `CartItem` / `Order` / `OrderItem`

### 2.2 Требуется добавить (по приоритету)

**P0 — критично:**
- **`Computer.club FK → Club`** (прямая связь для tenant-изоляции — сейчас только через group)
- **`Booking`**: `id, club, hosts:M2M, client FK, from, to, status (ACTIVE/FINISHED/CANCELED/REDEEMED), startsIn, comment, hard_booking bool, created_at`. Одна бронь может включать несколько ПК.
- **`ClientSession`** — операторская сессия клиента на ПК (заменит/дополнит GameSession для биллинга):
  - `client FK, hosts:M2M, duration_minutes, elapsed, time_left, payment FK, postpaid bool, total_cost, status (PLANNED/ACTIVE/FINISHED/CANCELLED), started_at, finished_at, canceled_at`
- **`UserBalance` расширить**: `deposit_money (decimal)` отдельно от `minutes_remaining`. Базовая валюта — деньги, минуты — частный случай зачисления.
- **`OperationLog`** — единая лента операций (продажа, отмена, открытие/закрытие смены, изменения настроек, авторизации сотрудников, сеансы).

**P1 — важно:**
- **`ClubNetwork`** (name, owner FK, max_discount, sync_apps bool) — сеть клубов одного владельца с общим депозитом.
- **`SubscriptionPlan`** (name: Free/Starter/Business, max_pcs, monthly_price, features_json).
- **`ClubSubscription`** (club, plan FK, started_at, expires_at, payment_status).
- **`PromisedPayment`** (clubsubscription, granted_at, due_at, fixed_amount=500₽, status). Отложка оплаты подписки на 7 дней.
- **`Discount`** (name, percent, telegram_notify, schedule, is_active).
- **`Promocode`** (code, reward_type [discount/deposit_topup/bonus], value, applies_to_clients [all/group/specific], applies_to_items [tariffs/products/services/combos], usage_limit, valid_until, channels [admin/mobile/shell], is_active).
- **`Cashback`** (deposit_threshold, accrual_type [percent/fixed], value, valid_until_optional).
- **`Achievement`** (name, trigger_type [reg/topup_single/topup_total/spend_single/spend_total/hours_in_club], threshold, reward_type [discount/bonus_deposit/none], reward_value, icon, created_at).
- **`UserAchievement`** (user, achievement, unlocked_at).
- **`ClientGroup`** (name 2–16, percent_discount 0..100, club). Клиент в одной группе.
- **`UserClubProfile`** (user, club, deposit_money, bonus_balance, personal_discount, group FK, status, comments, last_visit). Депозит у клиента **per-club**, не глобальный.
- **`Notification`** (user FK, club, type, body, sent_at, read_at).
- **`CashOrder`** (shift, type [PKO/RKO], amount, comment, admin).
- **`Review`** (client, computer, shift, rating 1-5, comment, tip_amount, is_anonymous, is_read, created_at).
- **`AdminCall`** (client, computer, shift, called_at, answered_at). Кнопка «Позвать админа».

**P2 — желательно:**
- **`Service`** (name 2-50, price, applies_discount, barcode opt). Отдельная модель от Product (Product = склад, Service = виртуальная услуга).
- **`ProductGroup`** (name 2-50, schedule_days, schedule_start/end, show_in_shell). Группа с расписанием продаж.
- **`Combo`** (name, club, group_fk_required_if_tariff, tariff:opt, products:M2M, services:M2M, base_price, sale_price, applies_discount).
- **`StockOperation`** (product, type [income/outcome], qty, comment, admin, shift, created_at).
- **`Task`** (assigned_to, title, body, is_active, club, created_at, finished_at). Виджет «Задачи» на дашборде.
- **`News`** (club, title 2-40, body, button_text, button_url, is_published, start_at, end_at, cover_image). Показывается в шелле и мобильке.
- **`ShellTheme`** (club, logo, primary_color, accent_color, splash_screen [Soft/SnowFlake/SmartLockTV], background, screensaver).
- **`ShellSecurity`** (club, vd_password, hidden_drives [list], blocked_apps [list of {name, window_class}], block_external_storage, block_chrome_downloads).
- **`Integration`** (club, type [telegram/cloudpayments/sbp/kaspi_qr/kaspi_online/stripe/kkm], config_json, is_active).
- **`Hotkey/HardwareController`** (контроллер консолей — для фазы 3).

---

## 3. API

### 3.1 Стек
- **GraphQL** (graphene-django) — основной канал для frontend (тарифы, сессии, ПК, лояльность). Совпадает со SmartShell.
- **REST DRF** — для бытовых CRUD (клубы, группы ПК, товары) и интеграции с C# Shell.
- **JWT** (simplejwt) с access 60м / refresh 7д — уже есть.
- **Tenant-изоляция:** на каждом запросе backend читает `active_club_id` из заголовка `X-Club-Id` или JWT-claim и фильтрует все queries по нему. **Без этого оператор клуба А увидит данные клуба Б.**

### 3.2 Endpoints (минимум для MVP)

**Accounts/Clubs:**
- `POST /api/v1/accounts/login/` (phone+password+hardware_id) → JWT
- `POST /api/v1/accounts/logout/` (refresh)
- `GET /api/v1/accounts/profile/`
- `GET /api/v1/clubs/my/` — клубы текущего юзера (owner+memberships)
- `POST /api/v1/clubs/` — создание клуба (для ЛК владельца)
- `GET/PATCH/DELETE /api/v1/clubs/<id>/`
- `GET /api/v1/clubs/<id>/verify/` — статус верификации

**Computers/Groups:**
- `GET/POST /api/v1/computers/groups/?club=<id>` ✅ уже есть
- `GET/PATCH/DELETE /api/v1/computers/groups/<id>/` ✅
- `GET /api/v1/computers/?club=<id>&group=<id>` ✅
- `POST /api/v1/computers/register/` (C# Shell)
- `POST /api/v1/computers/<id>/heartbeat/`
- `POST /api/v1/computers/metrics/`

**Tariffs/Shop:**
- `GET/POST /api/v1/billing/tariffs/?club=<id>` ✅
- `GET/PATCH/DELETE /api/v1/billing/tariffs/<id>/` ✅
- `GET/POST /api/v1/shops/products/`
- `GET/POST /api/v1/shops/services/`
- `GET/POST /api/v1/shops/combos/`
- `POST /api/v1/shops/products/<id>/stock/` (income/outcome)

**Sessions/Bookings (GraphQL):**
- `mutation startClientSession(pcId, userId?, tariffId, paymentMethod, amountPaid?)`
- `mutation stopSession(pcId)`
- `mutation transferSession(fromPc, toPc)`
- `mutation extendSession(sessionId, tariffId)`
- `mutation penalizeSession(sessionId, minutesToRemove)`
- `mutation createBooking(hosts:[Int!], clientId?, from, to, comment?)`
- `mutation cancelBooking(bookingId)`
- `query bookings(clubId, from?, to?)` — таймлайн

**Payments/Shifts:**
- `mutation openShift(clubId, initialCash)`
- `mutation closeShift(closingCash, notes?)`
- `query currentShift(clubId)` ✅
- `mutation topupDeposit(clientId, amount, method, promocode?)`
- `mutation refundPayment(paymentId)`
- `mutation createCashOrder(type, amount, comment)` — ПКО/РКО

**Loyalty:**
- `GET/POST /api/v1/loyalty/discounts/`
- `GET/POST /api/v1/loyalty/promocodes/`
- `GET/POST /api/v1/loyalty/cashback/`
- `GET/POST /api/v1/loyalty/achievements/`

**Reports:**
- `query salesReport(from, to, byCategory)`
- `query workshiftsReport(from, to, byAdmin)`
- `query clientsReport`
- `query equipmentLoadReport`

### 3.3 GraphQL-типы (см. также `memory/smartshell_api_reference.md`)

Совместимы со SmartShell-схемой для совместимости интеграций:
- `Host` (наш Computer): id, alias, coord_x/y, group_id, online, shell_mode, locked, last_online
- `HostGroup`: id, title, customization{color, background, screensaver}, hosts[]
- `Tariff`: id, title, duration, lifetime, per_minute, has_fixed_finish_time, price_list[], schedules[], sell_schedules[], pausable, highlighted, sort
- `Booking`: id, hosts[], client, from, to, status, startsIn
- `ClientSession`: id, client, hosts[], duration, elapsed, time_left, payment, postpaid, total_cost, status, seances[]
- `Payment`: id, client, method, status, sum, card_sum, cash_sum, cashback, items[], is_refunded
- `Workshift`: id, worker, created_at, finished_at, money, payments[], cashOrders[]

---

## 4. Frontend — экраны и компоненты

### 4.1 Прелогин (`Login.jsx` — уже частично готов ✅)
**3 шага в одном wizard:**
1. **Вход** — телефон (+71234567890) + пароль + кнопка глаза
2. **Выбор клуба** — поиск + список карточек: `имя · адрес · "Нет смены"/badge · Trial-badge`. Кнопка «Выбрать клуб»
3. **Открытие смены** — поле «Наличных в кассе» + блок выбранного клуба + кнопки «Открыть смену» / «Продолжить без смены» / «Выбрать другой клуб»

### 4.2 Sidebar (точный порядок SmartShell)
```
Дашборд
Компьютеры
Карта клуба
Бронирование
Магазин                    [только при открытой смене]
Платежи
Клиенты
Логи
─── (разделитель)
Товары и услуги ▾
   Тарифы
   Товары
   Услуги
   Комбо-наборы
Система лояльности ▾
   Скидки
   Промокоды
   Кешбэк
   Достижения
Сотрудники
Отзывы клиентов
Контент ▾
   Приложения (Игры)
   Новости
Аналитика (Отчёты)
Настройки
─── (низ)
Чат поддержки
```

### 4.3 ТопБар
- Лого PCHub слева
- Заголовок страницы
- `+` quick-actions
- Поиск клиента (по логину/телефону)
- «Вызовы» (бейдж новых вызовов администратора)
- Селектор клуба (если у юзера несколько) — например, «My Gaming Center ▾»
- Профиль с дропдауном (выход, сменить язык, сменить тему)
- При открытой смене — индикатор «Касса 1500 ₽» + кнопка «Закрыть смену»

### 4.4 Основные экраны

| Страница | Статус | Что должно быть |
|---|---|---|
| **Дашборд** | ✅ есть (доработать) | 8 виджетов (см. §6.2) |
| **Компьютеры** | ❌ заглушка | Таблица с колонками (см. §6.3) |
| **Карта клуба** | 🟡 частично | Свободное полотно + drag&drop + ПКМ-меню (см. §6.4) |
| **Бронирование** | 🟡 timeline есть | Добавить модал создания (см. §6.6) |
| **Магазин** | ❌ нет | POS трёхколоночный (см. §6.7) |
| **Платежи** | ❌ заглушка | Журнал смены + фильтры + отмена |
| **Клиенты** | ✅ есть | Доработать карточку (бонусы, скидки) |
| **Логи** | ❌ заглушка | Универсальный поиск событий |
| **Тарифы** | ✅ готово | 4 карточки цвета по типу |
| **Товары** | ✅ есть | Доработать (штрихкод, акциз, маркировка) |
| **Услуги** | 🟡 общая с товарами | Выделить отдельно |
| **Комбо-наборы** | ❌ нет | Конструктор набора |
| **Система лояльности** | ❌ заглушка | 4 подраздела |
| **Сотрудники** | ✅ есть | Доработать роли до 6 |
| **Отзывы клиентов** | ❌ заглушка | Лента с модерацией |
| **Контент → Приложения** | ❌ заглушка | CRUD игр + группы + Microsoft Store |
| **Контент → Новости** | ❌ нет | Создание новостей с обложкой |
| **Аналитика** | 🟡 базовая | 6 типов отчётов |
| **Настройки** | ❌ нет | 6 вкладок |

### 4.5 ЛК владельца (`/cabinet` — отдельный модуль)
- Список «Мои клубы» (карточки) + табы «Все клубы / Сеть клубов»
- Кнопки «Добавить клуб» / «Создать сеть клубов»
- Форма создания клуба (поля: название, сайт, страна, город, часовой пояс, улица, дом, контактное лицо, чекбоксы соглашения)
- Управление подпиской (Trial → Starter/Business, продление, обещанный платёж)
- Реквизиты организации и ПОПД (ИНН с автозаполнением, бенефициар)
- Профиль клуба: график работы, оборудование, услуги, фото
- Верификация клуба (название, адрес — валидация Яндекс.Картами, соцсеть)

---

## 5. Бизнес-логика по разделам

### 5.1 Прелогин (флоу)
1. Юзер вводит phone+password → POST login → backend ищет user через `Q(username=phone) | Q(phone=phone)`
2. Если успех — JWT в localStorage
3. GET `/clubs/my/` — backend возвращает клубы где юзер owner ИЛИ active member через ClubMembership
4. Юзер выбирает клуб → сохраняем `active_club_id` в localStorage
5. GET `/billing/current-shift?club=<id>` — если открытой смены нет → шаг 3 (открыть смену)
6. Юзер вводит initial_cash → POST `openShift` → создаётся Shift с club_id
7. Альтернатива: «Продолжить без смены» — заходим в систему, но магазин/платежи заблокированы
8. После — переход на дашборд

### 5.2 Дашборд (8 виджетов)

1. **Информация о смене** — оператор/роль, время открытия, выручка наличные+карта, текущие наличные в кассе
2. **Выручка по категориям** — карточки: тарифы / товары / услуги / пополнения депозита
3. **Бонусные пополнения и траты** *(Business)* — bonus_topups, deposit_spends
4. **Состояние хостов** — total / online / active sessions (guest+client) / maintenance / high-access / shell-disabled
5. **Активные и завершённые задачи** — Task model, чекбокс для смены статуса, ПКМ редактирование/удаление
6. **Оказанные услуги и проданные товары** — табы услуги/товары
7. **Активные пользователи** *(Business)* — топ по часам, депозит, последнее посещение
8. **Группы аккаунтов и занятые аккаунты** *(Business)* — Steam/Epic аккаунты, кнопка освободить

### 5.3 Компьютеры — таблица (`/computers`)
**Колонки:** № · Название (до 12 симв) · Статус [Занят/Свободен/Выключен/В обслуживании/Нет связи] · Бронь · Логин клиента · Тариф · Начало сеанса · Планируемое окончание · Часов осталось · Активное приложение · Версия шелла

**Правая панель состояния по клику:** CPU, RAM, GPU, HDD/SSD, занятость дисков, MAC, активное приложение, комментарий.

**Bulk-выделение:** Shift (область) / Ctrl (точечно) / чекбокс «Выбрать все» в зале. Допустимые bulk-действия: продажа тарифа (в рамках одного зала), уведомление, питание.

### 5.4 Карта клуба (`/map`) — **главный экран оператора**

**Два режима:**
- **Обычный** — управление сеансами, ПКМ-меню
- **Технический** — редактирование (drag&drop ПК/декора)

**В техническом режиме палитра:**
- Инструменты (выбор, подписи)
- Стены (конфигурации, стрелки)
- Хосты (ПК, консоль, VR, автосимулятор, бильярд, настольные)
- Доп. зоны (ресепшен, гардероб, туалет, лаунж, бар, кухня)
- «Создание групп хостов» / выход

**Сверху карты — критичные счётчики:** «Высокий доступ — N», «Нет связи — N», «Снят шелл — N», «В обслуживании — N»

**ПКМ-меню (11 пунктов с status-dependent enabled):**
1. Выбрать тариф
2. Постоплата (Postpay)
3. Пополнить депозит
4. Бронирование ▸ (Забронировать / Список бронирований)
5. Штраф ▸ (-15м / -30м / Свой)
6. Смена места
7. Завершить сеанс
8. Уведомление
9. Электропитание ▸ (Включить / Выключить / Перезагрузить / Выйти в Windows)
10. Управление ПК ▸ (Обслуживание / Подключиться / Просмотр экрана / Выполнить / Заметка / Запретить онлайн-бронь / Редактировать / Удалить)
11. Шелл ▸ (Поделиться логами / Высокий доступ / Отключить шелл)

**Цвета статусов (точно как SmartShell):**
- `#808080` Выключен / Заблокирован клиентом
- `#00CC00` Включён (без сеанса)
- `#6666FF` Активный сеанс / Есть бронь — мы используем `#8B5CF6` для активного фиолетового
- `#FF9900` В обслуживании / Изменена конфигурация
- `#FF0000` Высокий доступ / Нет связи / Снят шелл

**Bulk-выделение** на карте: мышью областью + Ctrl на отдельных.

### 5.5 Сессии и сеансы
**`ClientSession` — основная сущность сеанса** (НЕ путать с GameSession по конкретной игре):
- Создаётся при «Выбрать тариф» из ПКМ-меню
- Поля: client (или null=гость), hosts[], duration, payment, status
- Списание depositum: для PER_MINUTE — каждую минуту шедулер; для FIXED — сразу при покупке; для PACKAGE — сразу при покупке; для SUBSCRIPTION — отдельная сущность

**Семь действий с сеансом:**
- Старт (через тариф или постоплату)
- Продление (FIXED/PACKAGE/PER_MINUTE — добавляет время)
- Пауза (только если tariff.pausable=true)
- Возобновление
- Штраф (минус N минут — клиент видит уведомление; PER_MINUTE штрафовать нельзя)
- Пересадка (смена места — в рамках группы)
- Завершение (force-stop)

### 5.6 Бронирование
**Booking-модель:** хосты[], клиент?, от, до, статус (ACTIVE/FINISHED/CANCELED/REDEEMED), comment.
- Видно клиенту за 12 часов до начала (в шелле)
- Запрет старта сеанса, пересекающего бронь
- При наступлении времени брони — PER_MINUTE/FIXED сеансы клиента автозавершаются
- Жёсткое бронирование — флаг в настройках, дополнительный буфер

**Онлайн-бронирование (мобильное приложение):**
- Включается в Настройки → SmartGamer
- Параметры: мин/макс время, бесплатная отмена за N часов, штраф за позднюю отмену в %
- На уровне ПК — флаг «Запретить онлайн-бронь»

### 5.7 Магазин (POS, **`/shop`**)
**Только при открытой смене.** Трёхколоночный layout как на скрине `Магазин.png`:

**Левая колонка — карточка клиента:**
- Поиск/выбор клиента (логин/телефон)
- Аватар, имя, бейдж «Клиент»
- Кнопка «Пополнить депозит»
- Три поля: 💰 Депозит ₽ / ⭐ Бонусы / % Скидка
- Раскрывающиеся: Подробнее о клиенте · Комментарий · Несгораемый тариф · Заблокировать
- Список скидок клиента (Пятница 10%, Новая 20%, Открытие 50%)
- Поле «Промокод» + кнопка «Применить»

**Центр — каталог:**
- Табы: **Товары / Услуги / Комбо-наборы**
- Поиск + табличный вид (название · группа · кол-во на складе · цена)
- Клик добавляет в корзину (повторный — увеличивает qty)
- Кнопка «Внесение на склад» вверху справа

**Правая колонка — корзина:**
- Список позиций с +/- qty
- Раскрывающиеся «Скидка» / «Время окончания»
- Способы оплаты: 💵 Наличные / 💳 Карта / 🏦 Депозит / ➗ Разделить (composite-split)
- Кнопка «Оплатить XXX ₽»

### 5.8 Тарифы (4 типа)
Полностью реализовано в backend ✅, frontend ✅. См. `group5_tariffs_shop.md` §1.

| Тип | Длительность | Срок жизни | Старт | Продление | Online-бронь | Сохр. остаток |
|---|---|---|---|---|---|---|
| FIXED | задаётся | — | с покупки | FIXED/PACKAGE | да | до конца |
| PACKAGE | по графику | — | с покупки | FIXED/PACKAGE | да | да |
| PER_MINUTE | 1 мин | — | с покупки | автомат. | нет | списан в депозит |
| SUBSCRIPTION | задаётся | задаётся | покупка/автопрод./логин | абонементом | нет | да до TTL |

**Информационные иконки в карточке:** 🌙 ночной · % скидки · 👁 виден в шелле · 💰 виден оператору · ⭐ выделен · 📅 праздники · ✈️ Telegram · 🗓 онлайн-бронь.

### 5.9 Платежи (`/payments`)
**Журнал смены:** № · дата/время · категория [тариф/пополнение/товар/услуга/штраф] · клиент · способ оплаты · сумма · статус.

**Способы оплаты:** наличные / карта / депозит / бонусы (composite-split = разделить).

**ПКО/РКО (Кассовые ордера):** через быстрое меню оператора → тип + сумма + комментарий → «Внести/Изъять». Привязывается к Shift.

**Отмена платежа:** включается в Настройках → панель управления → «Отмена платежей» с таймером. Внутри окна оператор/менеджер/владелец отменяют. Ограничение: только последний платёж за тарифы.

**Перевод средств между депозитами** *(Business)*: клиент в шелле «Перевод депозита» → выбор клуба-источника в сети → перевод. Требует Сеть клубов + флаг в настройках.

**Чаевые администратору**: списываются с реального депозита (не бонусы), привязываются к последнему активному админу.

**Обещанный платёж**: отложка подписки на 7 дней за 500 ₽. После 7 дней без оплаты → Free. После 37 дней → блок.

### 5.10 Клиенты (`/clients`)
**Главная страница:** виджеты количества клиентов и групп · поиск (логин/телефон) · фильтр по группам · виджет суммы всех депозитов · CSV-экспорт (только владелец).

**Таблица:** никнейм · телефон · последнее посещение · персональная скидка · группа · депозит · статус · дата регистрации.

**Карточка клиента** (двойной клик):
- Краткая статистика
- История покупок (дата, оператор, наименование, способ, сумма)
- Поля депозита и скидки (редактируемые карандашом)
- Комментарии (важные — с восклицательным знаком в окне продажи)
- Абонементы

**ClientGroup:** название (2-16 симв.) · скидка 0-100% · клиент в одной группе. Персональная и групповая не суммируются — берётся максимум.

### 5.11 Сотрудники (`/workers`) — 6 ролей
- **Менеджер** — управление тарифами/товарами/лояльностью/финансами
- **Оператор** — клиенты, сеансы, платежи
- **Бухгалтер** — отчёты, кассовые ордера, движение товаров
- **Сисадмин** — железо, хосты, клубные аккаунты
- **Маркетолог** — клиенты, лояльность
- **Другой** — без прав, гибко настраивается в Business

Поиск пользователя по последним 4 цифрам телефона (юзер должен сначала зарегистрироваться в шелле).

В **Business** — таблица прав ДА/НЕТ для каждой роли.

### 5.12 Игры и приложения (`Контент → Приложения`)
**Карточка игры:**
- Название (2-50 Unicode)
- Путь к игре (обязат., до 3 альт.)
- Аргумент CLI
- Рабочая директория (автозаполнение)
- Группа клубных аккаунтов (Starter/Business)
- Возрастное ограничение (PEGI/ESRB)
- Запуск от admin (флаг)
- Запуск без сеанса (для бесплатных утилит)
- Обложка (мин. 256×384, опт. 600×900, ≤250 KB, .jpg/.png)
- Путь к иконке (.ico/.exe)

**Microsoft Store**: PowerShell → `Get-StartApps` → копируем AppID → путь `shell:AppsFolder/<AppID>`.

**Создание ярлыков из Шелла** (Ctrl+Alt+P): на ПК клиента в режиме редактирования.

**Таблица путей:** Steam, Epic Games, Riot Client (для Runeterra/LoL/Valorant), Battle.net, EA App, Uplay, Discord, DayZ/Arma 3, SteelSeries GG. См. `group4_games.md`.

**Обновление игр (служебный тариф):** менеджер создаёт тариф «Обновление. Служебный» на 1 час, 0 ₽, скрыт из шелла. Оператор продаёт как гостевую сессию и запускает обновление.

### 5.13 Клубные аккаунты (`/club-accounts`)
**Starter/Business.** Создание группы → выбор лаунчера (Steam/Epic) → добавление пар логин/пароль. Привязка к игре в её карточке. При запуске игры клиенту автоматически выдаётся свободный аккаунт.

**Статусы аккаунта:** Активен · Свободен · В использовании (с указанием ПК) · Забанен.

### 5.14 Система лояльности (4 подраздела)

**Скидки** (`/discounts`): name · percent · telegram_notify · schedule · is_active.

**Промокоды** (`/promo-codes`): name · reward_type (discount/deposit_topup/bonus_topup) · value · clients (specific/group/all) · usage_limit · items (tariffs/products/services/combos) · channels (admin/mobile/shell) · is_active · period. Один промокод = один раз на клиента.

**Кешбэк** (`/cashback`): deposit_threshold · accrual_type (percent/fixed) · value · valid_until_opt. Нельзя две записи с одинаковым порогом. Промокоды не учитываются. При возврате — кешбэк списывается.

**Достижения** (`/achievements`): name · trigger_type (registration / topup_single / topup_total / spend_single / spend_total / hours_in_club) · threshold · reward_type · reward_value · icon. Один раз на клиента, нельзя редактировать (только пересоздать).

### 5.15 Отзывы клиентов (`/reviews`)
Клиент после сеанса видит модал: рейтинг 1-5 · комментарий · контакты · опц. чаевые. Аноним. возможен. Включается в Настройки → Шелл.

Менеджер видит ленту: оценка · ПК · дата · текст · чаевые · модерация (Не прочитано → Прочитано). Опц. Telegram-уведомления.

**Вызов администратора**: кнопка «Позвать админа» в шелле. Оператор смены получает уведомление. Rate-limit 1 минута.

### 5.16 Настройки (6 вкладок)

**Панель управления:**
- Основные параметры клуба (поминутный тариф по умолчанию, тарифы выходного дня)
- Параметры сеансов (мин/макс длительность, автопродление)
- Параметры лояльности
- Параметры смен (часы, валюта)
- Отмена платежей (вкл + период)

**Шелл:** разрешение экрана · автозапуск · параметры приложений · отзывы вкл/выкл · чаевые вкл/выкл + список сумм.

**Безопасность** (см. §5.17).

**Кастомизация:** цвета темы (9+ предустановок) · акцентный · доп.цвет · постер клуба · заставки [Soft / SnowFlake / SmartLockTV] · превью предзагрузочного экрана.

**SmartGamer (онлайн-бронирование):**
- Мин/макс время брони (час)
- Время после сеанса до возможности брони (мин)
- Самостоятельная отмена клиентом (вкл/выкл)
- Бесплатная отмена за N часов
- Штраф в %
- Показывать загруженность
- Бронирование нескольких ПК на пересекающемся времени
- Рейтинг игроков

**Интеграции:**
- **Telegram** — токен бота + выбор типов событий
- **Kkm-Server** (касса) — модель ККТ + СНО + категории
- **CloudPayments** — public_id, secret
- **СБП** (РФ) — merchant_id
- **Kaspi QR / Kaspi-онлайн** (Казахстан)
- **Stripe** (международные)

### 5.17 Безопасность шелла
**Пароль высокого доступа (ВД):** дефолт `pasw0rd`, должен быть изменён. Открывает Ctrl+Alt+P в шелле.

**TightVNC:** удалённое управление (несовместимо с CCBvolt).

**Скрытие дисков:** список локальных дисков, недоступных в шелле и из лаунчеров.

**Блокировка приложений и окон:** таблица с двумя колонками — `Название` (например `*SmartShell*` — wildcard) и `Класс окна` (`CabinetWClass`, `ConsoleWindowClass`). Готовые шаблоны: Проводник, командная строка, диалоги открытия файлов, браузеры.

**Запрет внешних накопителей:** USB/HDD/телефоны.

**Запрет скачивания Chrome.**

Применение: при выключенном ПК — после включения; при включённом — Ctrl+Alt+Del → Выйти → перезапуск шелла.

### 5.18 Аналитика (отчёты, `/reports`)
6 типов:
- **По сменам** — выручка по сменам/операторам, часы, бонусы, возвраты
- **Обзорный** — выручка по категориям (тариф/товар/услуга) + способам оплаты (нал/безнал/онлайн/бонусы), загрузка, топ позиций
- **По клиентам** — дата регистрации, скидка, баланс, средний чек
- **По посетителям** — уникальные, новые, гости vs клиенты
- **По занятости оборудования** — рабочие часы хоста, выручка с ПК
- **По играм и приложениям**

### 5.19 Логи (`/logs`)
Период · категория · переключатель «все/текущая смена» · универсальная строка поиска (телефон, товар, имя ПК).

Структура события: **субъект (кто) → объект (над кем) → действие → время**.

Категории: питание ПК · продажа · отмена продажи · сеансы (старт/конец/пересадка) · изменения БД (клиенты/сотрудники/тарифы/товары/услуги/скидки/ПК) · авторизация · кассовая смена.

---

## 6. Интеграции (Business тариф)

| Интеграция | Что | Когда нужна |
|---|---|---|
| **Telegram** | Уведомления о событиях (продажа, остатки, отзывы) | Базовая, P0 |
| **CloudPayments** | Онлайн-платежи клиентов (карта) | P1 |
| **СБП** | Оплата из шелла/мобильки (РФ) | P1 (РФ) |
| **Kaspi QR / Kaspi-онлайн** | Казахстан | P2 |
| **Stripe** | Международные платежи | P3 |
| **Kkm-Server** | Касса (ККТ): Атол, Штрих-М, RR-Electro, ЭЛВЕС, Ритейл, Dreamkas Viki-Print, КИТ/КАСБИ | P2 (для РФ) |
| **Эквайринг** | TTK2, СБРФ, INPAS, UCS, ARCUS-2 | P3 |
| **Telegram-бот клиентов** | `@*_auth_bot` — авторизация, коды, мои клубы | P2 |
| **SmartGamer-аналог** | Мобильное приложение клиентов | P3 (отдельный проект) |
| **Контроллер консолей** | Реле питания PS/Xbox через Wi-Fi | P3 |

---

## 7. Безопасность и tenant-изоляция

### 7.1 Изоляция данных
**Каждый запрос к API ОБЯЗАТЕЛЬНО фильтруется по `active_club_id`.**

Реализация:
1. Middleware читает `X-Club-Id` из заголовка или `club` из JWT-claim
2. Проверяет что user — owner или active member этого клуба
3. Все QuerySet'ы фильтруются: `Computer.objects.filter(club_id=request.current_club_id)`
4. GraphQL-резолверы тоже фильтруют
5. Только `is_platform_admin` юзер обходит фильтр

### 7.2 JWT
- access 60 минут, refresh 7 дней (ротация активна)
- Blacklist при logout
- Защита от параллельной сессии: `is_active_session` + `active_hardware_id`

### 7.3 Шелл-безопасность
См. §5.17 — это уровень клиента (Windows), не нашего бэка.

---

## 8. Горячие клавиши

### Шелл
| Комбинация | Действие |
|---|---|
| Ctrl + Alt + F10 | Диспетчер задач в шелл |
| Ctrl + Alt + P | Высокий доступ / деактивация |
| Win + D | Открыть шелл / свернуть окна |
| Esc | Закрыть модал |

### Панель управления
| Комбинация | Действие |
|---|---|
| Ctrl + Alt + S | Включить/выключить выделенные ПК |
| Ctrl + Alt + D | Окно пополнения депозита |
| Ctrl + Alt + B | Окно бронирования |
| Ctrl + Alt + G | Окно магазина |
| Ctrl + Alt + L | Сменить язык |

---

## 9. Текущее состояние PCHub (на 2026-05-26)

### ✅ Готово
- **Backend модели:** User, Club, ClubMembership, ComputerGroup, Computer, ComputerMetrics, Game, GameSession, GuestSession, ClubAccount, TariffPlan(v2 с 4 типами), TariffPrice, Product, Cart, Order, UserBalance, Payment, Shift
- **Backend API:**
  - REST: `/accounts/login`, `/accounts/profile`, `/clubs/my/`, `/computers/groups/`, `/billing/tariffs/` (CRUD)
  - GraphQL: computers, tariffs, currentShift, openShift, closeShift, startSession, stopSession
- **Frontend:** Login wizard (3 шага), ClubMap с зонами, Tariffs (4 карточки), Dashboard (базовый), Clients (CRUD), Employees, Products
- **Seed-команды:** `seed_demo_clubs` (admin/admin123, 2 клуба, 4 группы), `seed_demo_computers` (10 ПК), `seed_demo_tariffs` (4 тарифа × 4 цены)
- **Django Admin** — оставляем для нас как dev-инструмент, не показываем клиентам

### 🟡 Частично готово
- Карта клуба — нет ПКМ-меню, нет свободного полотна (drag&drop), нет компактных плиток
- Sidebar — порядок не точно совпадает со SmartShell
- Login на phone, но 8 ролей пока только 5

### ❌ Не реализовано (см. §10)

---

## 10. Roadmap

### Фаза 1 — Фундамент (тенант-изоляция + критичные модели)
- [ ] `Computer.club FK → Club` + миграция данных
- [ ] Middleware tenant-изоляции (фильтр всех запросов по active_club_id)
- [ ] Модели `Booking`, `ClientSession`, `ClientGroup`, `UserClubProfile` (deposit_money per-club)
- [ ] Модели `CashOrder`, `OperationLog`, `Review`, `AdminCall`, `Notification`
- [ ] Расширение `UserBalance` — отдельные поля для денег и бонусов

### Фаза 2 — Карта клуба + Сессии
- [ ] Свободное полотно карты (drag&drop ПК, сохранение position_x/y)
- [ ] ПКМ-меню с 11 пунктами (status-dependent enabled)
- [ ] Компактные плитки ПК (номер + power, без подписей)
- [ ] Цвета статусов под эталон
- [ ] Bulk-выделение (Ctrl/Shift)
- [ ] Список бронирований + модал создания брони
- [ ] Сессия: start/extend/penalty/transfer/stop

### Фаза 3 — Магазин (POS) + Биллинг
- [ ] Trichromy POS layout
- [ ] Услуги — отдельная модель и страница
- [ ] Комбо-наборы — модель + UI
- [ ] Группы товаров с расписанием
- [ ] Штрихкод
- [ ] ПКО/РКО (CashOrder)
- [ ] Composite-split оплата
- [ ] Отмена платежа

### Фаза 4 — Лояльность
- [ ] Скидки CRUD
- [ ] Промокоды CRUD + применение при продаже
- [ ] Кешбэк (правила и начисление)
- [ ] Достижения (триггеры и награды)

### Фаза 5 — Контент
- [ ] Игры/приложения (CRUD с обложками, группами, возрастом, путями альт.)
- [ ] Клубные аккаунты UI (есть модель)
- [ ] Новости (CRUD)
- [ ] Microsoft Store helper

### Фаза 6 — Настройки + Безопасность
- [ ] 6 вкладок Настроек
- [ ] ShellTheme
- [ ] ShellSecurity (блокировка приложений, скрытие дисков)
- [ ] Кастомизация шелла

### Фаза 7 — Интеграции
- [ ] Telegram уведомления
- [ ] CloudPayments
- [ ] СБП
- [ ] Kaspi
- [ ] Касса (Kkm-Server)

### Фаза 8 — ЛК Владельца
- [ ] Маршрут `/cabinet`
- [ ] Мои клубы / Сеть клубов
- [ ] Создание клуба (форма с разбитым адресом)
- [ ] Верификация клуба
- [ ] Реквизиты и ПОПД
- [ ] Подписка (Trial → Starter/Business, обещанный платёж)
- [ ] ClubNetwork + перевод между депозитами

### Фаза 9 — Отчёты и логи
- [ ] 6 типов отчётов
- [ ] Универсальный лог событий

### Фаза 10 — Platform Admin (наш супер-админ)
- [ ] Список всех клубов
- [ ] MRR/выручка/новые регистрации
- [ ] Управление подписками
- [ ] Поддержка/тикеты

### Фаза 11+ — Опционально
- [ ] SmartGamer-аналог (мобильное приложение клиента)
- [ ] SmartKiosk (киоск самообслуживания)
- [ ] Контроллер консолей (hardware)
- [ ] Честный знак (CRPT маркировка)
- [ ] Multi-локализация (en/kz/uz)

---

## 11. Правила работы (для AI и команды)

**При работе над любым разделом:**
1. ОБЯЗАТЕЛЬНО открывать релевантные HTML из `d:/PC/картинки/` и встроенные в них фото
2. Сверять дизайн со скриншотами SmartShell (не только текст)
3. Tenant-изоляция — с первого дня (никаких глобальных QuerySet'ов без фильтра по клубу)
4. Django Admin — только для нас (разработки), не показывать клиентам
5. Все клиентские интерфейсы — на React
6. Главный канал API — GraphQL (совместимо со SmartShell-схемой)
7. Деньги — основная валюта депозита, бонусы — отдельно. НЕ минуты как было раньше

**Принцип постепенной проверки:** каждый раздел — Backend (модель → миграция → API) → Frontend → seed → визуальная проверка против скриншота SmartShell.

---

## 📚 Источники

- **`docs/tz_research/group1_clubs_employees.md`** — Регистрация ЛК, Верификация, Реквизиты, Профиль клуба, Сеть, Сотрудники, Меню
- **`docs/tz_research/group2_clients.md`** — Клиенты, регистрация, восстановление пароля
- **`docs/tz_research/group3_computers_sessions.md`** — Карта клуба, таблица ПК, ПКМ-меню, цвета, клубные аккаунты, автозапуск, пересадка
- **`docs/tz_research/group4_games.md`** — Игры, возраст, Microsoft Store, ярлыки, таблица путей, обновление
- **`docs/tz_research/group5_tariffs_shop.md`** — Тарифы (4 типа), Магазин, Товары, Услуги, Комбо, Подакциз, Штрихкод, Честный знак, Настройки
- **`docs/tz_research/group6_payments.md`** — Платежи, ПКО/РКО, Обещанный платёж, Онлайн-пополнение, Отмена, Перевод депозита, Чаевые, ККТ ошибки
- **`docs/tz_research/group7_booking_loyalty.md`** — Бронирование, Лояльность (4 модуля), Вызов админа, Отзывы
- **`docs/tz_research/group8_integrations_api.md`** — Интеграции, ККТ, Telegram-бот, SmartGamer, SmartKiosk, Контроллер, API, Аналитика, Логи
- **`docs/tz_research/group9_misc.md`** — Дашборд (8 виджетов), Домашняя страница (6 блоков), Новости, Ошибки контроллера, Горячие клавиши, **Глоссарий (90+ терминов)**
- **`memory/smartshell_api_reference.md`** — GraphQL-типы из apidoc.smartshell.gg
- **`d:/PC/картинки/*.html`** — 50+ HTML-страниц справки SmartShell (читать вместе со встроенными `<img>`)

---

*Документ собран автоматически на основе глубокого исследования SmartShell-документации. Версия 1.0 — 2026-05-26.*
