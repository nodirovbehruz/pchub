# PCHub — оставшееся усиление перед/на проде

Эти пункты **нельзя выполнить из среды разработки** — нужны сервер, домен/сертификат,
правки инсталлятора и групповые политики Windows. Здесь — готовые шаги.

---

## 1. HTTPS / TLS (КРИТИЧНО — сейчас токены ходят по HTTP открытым текстом)

Шелл и API общаются по `http://173.212.221.131`. Любой в LAN клуба перехватывает JWT.

### Вариант A — домен + Let's Encrypt (рекомендуется)
```bash
# на сервере, нужен A-record домена на 173.212.221.131
sudo apt install -y certbot python3-certbot-nginx
sudo certbot --nginx -d pchub.example.com   # подставь домен
# certbot сам впишет ssl-конфиг и редирект 80→443
sudo systemctl reload nginx
```
Затем в Django `.env`:
```
SECURE_SSL_REDIRECT=True
SESSION_COOKIE_SECURE=True
CSRF_COOKIE_SECURE=True
SECURE_HSTS_SECONDS=31536000
ALLOWED_HOSTS=pchub.example.com,173.212.221.131,localhost,127.0.0.1
```
И в шелле `PCHub.User.Core/Configuration/ServerConfig.cs`:
```csharp
private const string ProdBaseUrl = "https://pchub.example.com";
```
пересобрать инсталлятор.

### Вариант B — только IP (самоподписанный, временно)
IP-сертификаты Let's Encrypt не выдаёт. Самоподписанный + доверие на каждом ПК — хуже,
но шифрует канал. Лучше получить домен.

---

## 2. Шелл — RCE через installer-URL (design-gated)
`CommandPollingService` скачивает и запускает `InstallerUrl` из команды без проверки.
Нельзя просто заблокировать чужие хосты (ломает Steam/CDN). Нужен один из:
- **Подпись команд**: бэкенд подписывает payload (HMAC ключом клуба/устройства), шелл проверяет.
- **SHA-256 в команде**: бэкенд кладёт ожидаемый хеш файла, шелл сверяет перед запуском.
- **Allowlist хостов** в настройках клуба, проверяемый шеллом.
Решение за продуктом — реализовать в backend `apps/computers` (создание команды) + шелл.

## 3. Шелл — пер-ПК аутентификация (закрывает отложенные бэкенд-IDOR)
Эндпоинты, которые зовёт шелл гостевым токеном, нельзя закрыть membership-проверкой
(гость не член клуба). Нужен **секрет устройства**:
1. `register/` возвращает `device_secret` (генерится при создании Computer).
2. Шелл хранит его в `pc_config.json`, шлёт в заголовке `X-Device-Secret`.
3. Бэкенд проверяет секрет на: `computers/<id>/specs/`, `metrics/`, `commands/pending/`,
   `commands/<id>/status/`, guest-status. Тогда снять с них AllowAny-by-id / гостевой доступ.
Это закрывает: ComputerUpdateSpecs/metrics IDOR, AllowAny команды, токен по hardware_id,
утечку high-access пароля в payload. **Требует синхронной правки backend+шелл и стенда.**

## 4. Шелл — киоск (требует инсталлятора / политик)
- **Захардкоженный пароль выхода** `pchub_admin_2024` + конфиг в `C:\ProgramData` без ACL:
  инсталлятор должен спрашивать пароль клуба и писать хеш под admin-only ACL (или HKLM).
- **Ctrl+Alt+Del / Task Manager / sticky-keys** обходят low-level хук:
  применить HKLM-политики `DisableTaskMgr`, `DisableLockWorkstation`, отключить залипание —
  через инсталлятор или GPO.
- **Watchdog в session-0** не перезапускает UI в пользовательскую сессию:
  использовать `WTSGetActiveConsoleSessionId` + `CreateProcessAsUser`.
- **Per-user shell replacement (HKCU)**: второй Windows-аккаунт обходит киоск —
  применять машинно (HKLM) или блокировать создание аккаунтов.

---

## 5. Проверки перед продом (то, что НЕ покрыл sqlite-харнесс)
1. `python manage.py migrate` на **Postgres** — тесты шли на sqlite `--no-migrations`.
2. **Конкурентный тест гонок** на Postgres: двойное закрытие смены/postpaid, склад,
   открытие смены в две вкладки — фиксы (`select_for_update`) проверены только логикой.
3. **Визуальный прогон фронта** в браузере (сборка проходит, но UX-проверка нужна).
4. **Шелл на реальном киоск-стенде**: офлайн-поведение (теперь fail-closed), выход из
   киоска, удалённые команды.
5. Создать клуб + владельца (см. ранее) и ввести `club_token` в Setup шелла.
6. **Realtime/ЧАТ (важно — на сервере чат не работал):** ответ оператора доставляется
   клиенту ТОЛЬКО по WebSocket (`push_chat_to_user`), REST-фолбэка у шелла нет. При
   `uvicorn --workers 2` + InMemory channel layer `group_send` не пересекает воркеры →
   ответы оператора не доходят. **Фикс в коде:** channel layer теперь авто-использует
   `REDIS_URL`, если `REDIS_CHANNELS_URL` не задан. На сервере `REDIS_URL` уже задан →
   после `git pull` + `systemctl restart pchub` чат (и баланс/команды) заработают.
   Проверь: `redis-cli ping` → PONG; в логах uvicorn нет ошибок подключения к Redis.

---

## 6. Функциональный аудит (breadth-first) — матрица покрытия

22 функциональных кластера прогнаны по чек-листу (бизнес-логика, CRUD, границы,
пагинация, переходы статусов, дата/TZ, деньги, пусто/первый-запуск, ошибки, i18n,
фронт-состояния). **100% кластеров отревьюировано**, 143 находки. Полный список —
в журнале воркфлоу (`tasks/wm2y73v16.output`).

### Исправлено в этот проход (с тестами, 36 регрессов зелёных)
- 🔴 **Возврат комбо-топапа не дебетовал депозит** (free money) → маркер `[TOPUP]` (red→green).
- 🟠 **TIME_ZONE=Asia/Tashkent** (был America/Chicago — ломал тарифы день/ночь и аналитику).
- 🟠 **Закрытие postpaid обнуляло предоплаченные минуты** → сохраняем (red→green).
- 🟠 **PENDING→COMPLETED заказа без оплаты** (бесплатные товары) → запрещено.
- 🟠 **500 на мусоре**: даты броней `?from/?to`, `?hours` метрик; пустые hosts брони;
  review/admin-call без клуба → 400.
- 🟠 **bonus_writeoff_pct без клампа** (отрицательная цена) → 0..100.
- 🟠 **high-access `bool("false")=True`** → корректный парсинг.
- Фронт: метки колонок Dashboard; гард дабл-клика и `limit` cash-orders; `limit=500`
  POS-каталог/скидки/отзывы/вызовы-админа.
- 🟠 кириллица в имени игры → валидный slug (была недоступна по detail/update).
- 🟠 metrics-ingest больше не сбрасывает MAINTENANCE/DISABLED → ONLINE.
- 🟠 `?all=1` показывает inactive тарифы/игры в админке (реактивация) — бэк+фронт.
- next-booking индикатор ПК учитывает REDEEMED; применены игнорировавшиеся фильтры
  списков (Task `?is_finished/?assigned_to/?search`, Review `?is_read`, AdminCall
  `?is_answered`); guard 500 на нечисловом `order` категории игр.

- batch E: 500 на `?year=abc` (my-visits) и коллизия длинных имён client-group;
  `ceil` для trial/days-to-pay.
- batch F: News title min-2; ClientSession PATCH ставит finished_at/cancelled_at.
- **deep-money** (новый раунд, 3 новых бага): (1) `total_revenue` смены теперь включает
  genuine банк-перевод (исключая внутренние `[DEPOSIT]`); (2) `start_guest_postpaid`
  отклоняет повторный старт на занятом ПК (был сброс накопленных неоплаченных минут →
  потеря выручки); (3) минутный штраф на postpaid отклоняется (был no-op + ошибочно
  выкидывал клиента). Все с red→green/регрессами.

### Доп. раунд HIGH-функционал (по запросу «продолжай», все с тестами)
- Список клиентов: per-club остаток времени/активность (был глобальный UserBalance).
- No-show брони освобождает залоченный ПК (отмена reserve-LOCK + UNLOCK) — был навсегда залочен.
- High-access создаёт ShellSecurity → применяется дефолтный пароль (был пустой).

(Всего по проекту на этот момент: **51 регресс-тест зелёный**.)

### Ценовая модель seat/zone — needs-stand (продуктовое решение, не угадываю)
- `computers/.../session.py:79-86`: ночь/праздник-цена применяется ТОЛЬКО для ПК с
  зоной (`pc.group_id`); ПК без зоны всегда base. Нулевая зона-цена → base.
- Operator-seat-path не применяет персональную скидку клиента (self-buy применяет) —
  одна цена тарифа разная в зависимости от инициатора. Выровнять — после решения, какая
  цена «правильная» для оператор-продажи.

(Итого функционального прохода: ~26 фиксов, 43 регресс-теста зелёных, red→green на
money/state. Остаток — LOW-косметика фронта/шелла под фан-аут агентов + needs-stand +
точечные backend LOW: telegram-escape динамики, per-club уникальность promocode,
orphan `/loyalty/topup/`, ClientSession state-machine.)

### Остаточный бэклог (fixable здесь, не критично — следующие проходы)
Сгруппировано; детали и `файл:строка` — в журнале воркфлоу.
- **HIGH:** депозит-топап учтён как TARIFF revenue (dashboard/analytics); Transfer
  исключён из shift total_revenue/Z-report; оплата promised-payment роняет клуб во Free;
  кириллица в имени игры → пустой slug (detail/update 404); category CASCADE-удаление
  товаров (нужен soft-delete); DISCOUNT-промокоды/loyalty.Discount не применяются;
  no-show оставляет ПК залоченным; redeem убирает бронь из «next booking»; ShellTheme/
  ShellSecurity строки не создаются (themes/security 404, дефолтный пароль пустой);
  inactive тариф/игра исчезают и не реактивируются; add-existing-user-as-employee 403;
  Clients-список показывает ГЛОБАЛЬНОЕ время вместо per-club.
- **MEDIUM (~45):** широкие списки без пагинации (>500 строк), фильтры/сортировки
  игнорятся (Task/News/Review/AdminCall), Booking heartbeat-гонка, metrics
  перезатирает MAINTENANCE→ONLINE, post_save помечает весь каталог installed,
  Cabinet/Tariffs/News/Combos фронт-капы и форматирование, Gantt полуночь и др.
- **LOW (~45):** косметика, форматирование денег/дат, валидации границ, CSV-заголовки,
  unsaved-changes guard, и т.п.

### Требует живого стенда (не воспроизводимо в sqlite/без шелла)
- Game-session double-count часов (реальный трекинг сессии).
- Dashboard «Занятые аккаунты» (хардкод in_use=False — нужен интент account-pool).
- Remote command double-exec при сбое in_progress-репорта (шелл).
- Game auto-detect зависание при полном скане дисков (шелл).
- Числовые Settings как строки в JSON blob (ломает ли C#-потребителя — на стенде).
- Точная числовая корректность выручки accrual-vs-cash + поведение списков >500 на Postgres.
- **Модель выручки дашборда (`dashboard.py:108` total_revenue)** — суммирует ВСЕ платежи,
  включая deposit-spends (`[DEPOSIT]`/`method=deposit`), уже посчитанные при топапе →
  **двойной счёт** (топ-ап 100 + трата 100 с депозита = «выручка» 200 при 100 реальных).
  Смена (`shift.close_shift`) уже переведена на cash-basis (genuine-money-in,
  исключая `[DEPOSIT]`) — дашборд НЕ выровнен намеренно: cash-basis vs accrual и
  «total = сумма категорий» — продуктовое решение. Выбрать модель на стенде и выровнять
  `total_revenue` + категории дашборда под неё (сейчас не трогаю, чтобы не гадать).

### Фронт/шелл — фан-аут агентов заблокирован
Часть фронт/шелл-фиксов (Combos-форма, Orders-форматирование, Gantt-полночь, шелл
RealtimeService UTF-8, ProfileViewModel-гонка и др.) подготовлена к фан-ауту агентов,
но **лимит аккаунта на саб-агентов** (сброс 9:00 Ташкент) прервал их. Возобновить после сброса.
