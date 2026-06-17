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
