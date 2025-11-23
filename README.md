# Marzban Shop

> 🇷🇺 Russian version: [README_ru.md](README_ru.md)

Telegram bot shop for selling and renewing VPN subscriptions via Marzban. The bot uses aiogram v3 and supports multiple payment methods, localized UI, and webhook-based delivery.

## Features
- Manual card payments via short links (Sber / T-Bank)
- YooKassa, Cryptomus, and Telegram Stars payments
- Trial subscriptions controlled by environment settings
- English and Russian localization
- CLI utilities for bot and nginx management
- One-click installer script

## Requirements
- Linux server with root access
- Docker and Docker Compose plugin
- nginx with valid TLS certificates (Let’s Encrypt recommended)
- Telegram bot token and access to your Marzban panel

## Quick install (one-click)
1. Download and run the installer (update REPO_URL inside `install.sh` to your fork if needed):
   ```bash
   curl -O https://raw.githubusercontent.com/indie-master/marzban-shop/main/install.sh
   chmod +x install.sh
   sudo ./install.sh
   ```
2. The installer can configure nginx/Let’s Encrypt if you supply a domain, or you can skip nginx and set it up later manually using `nginx/*.example` and `mnginx`.
3. Follow the prompts to fill in key `.env` values (copied from `.env.example`) and optional goods.
4. After installation, you can manage the bot with `mshop` and nginx with `mnginx`.

## Configuration

### Environment file (`.env`)
The repository ships `.env.example` with placeholders; copy it to `.env` during installation (the installer will offer to do this). Real `.env` values are not tracked in git. Key settings (examples only, replace with your values):
- `BOT_TOKEN` – Telegram bot token
- `SHOP_NAME` – Shop display name
- `TEST_PERIOD` – Enable/disable trial button (`true`/`false`)
- `TEST_PERIOD_DAYS` – Trial duration in days
- `PANEL_HOST`, `PANEL_GLOBAL`, `PANEL_USER`, `PANEL_PASS` – Marzban panel access (panel URL vs. external subscription URL)
- `PROTOCOLS_CONFIG` – Path to protocol config (e.g., `protocols.json`)
- Payment gateways: `YOOKASSA_TOKEN`, `YOOKASSA_SHOPID`, `CRYPTO_TOKEN`, `MERCHANT_UUID`
- Manual payment links: `PAY_SBER_URL`, `PAY_TBANK_URL`
- Telegram Stars toggle: `STARS_PAYMENT_ENABLED=true` (any other value disables Stars)
- Admin and notifications: `TG_INFO_CHANEL`, `ADMIN_IDS` (comma-separated), `TG_BACKUP_BOT_TOKEN`, `TG_BACKUP_CHAT_ID`
- Database: `DB_NAME`, `DB_USER`, `DB_PASS`, `DB_ROOT_PASS`, `DB_ADDRESS`, `DB_PORT`
- Webhook: `WEBHOOK_URL` (without `/webhook`, e.g., `https://bot.example.com`), `WEBHOOK_PORT`
- Notifications: `RENEW_NOTIFICATION_TIME`, `EXPIRED_NOTIFICATION_TIME`
- FAQ links: `FAQ_PRIVACY_URL`/`FAQ_PRIVACY_ENABLED`, `FAQ_TERMS_URL`/`FAQ_TERMS_ENABLED`, `FAQ_RULES_URL`/`FAQ_RULES_ENABLED`, `FAQ_OFFER_URL`/`FAQ_OFFER_ENABLED`
- Happ download buttons: `HAPP_IOS_URL`, `HAPP_ANDROID_PLAY_URL`, `HAPP_ANDROID_APK_URL`, `HAPP_WINDOWS_URL`, `HAPP_LINUX_URL`
- Optional section images: `START_IMAGE_ENABLED`/`START_IMAGE_PATH`, `SUBSCRIPTION_IMAGE_ENABLED`/`SUBSCRIPTION_IMAGE_PATH`, `INSTRUCTIONS_IMAGE_ENABLED`/`INSTRUCTIONS_IMAGE_PATH`, `FAQ_IMAGE_ENABLED`/`FAQ_IMAGE_PATH`, `SUPPORT_IMAGE_ENABLED`/`SUPPORT_IMAGE_PATH`

Edit the file manually or with `mshop edit .env` after installation. Keep your real `.env` out of git.

### Webhook configuration
1. Set `WEBHOOK_URL` in `.env` **without** `/webhook` (e.g., `https://bot.example.com`).
2. Ensure nginx proxies `https://your-domain/webhook` to the bot (see `nginx/bot.conf.example`).
3. Start or reload the bot stack: `mshop restart`.
4. Manage the Telegram webhook via CLI:
   - `mshop webhook-info` – show current webhook info
   - `mshop webhook-set` – set webhook to `${WEBHOOK_URL}/webhook`
   - `mshop webhook-delete` – delete webhook
   - `mshop webhook-reset` – delete then set webhook
5. Quick check:
   ```bash
   curl -I https://your-domain/webhook
   ```

### Bot screens and navigation
- **Greeting (`/start`)** shows the welcome text with motto, available locations, and the free-trial line when trials are enabled and unused (`TEST_PERIOD`/`TEST_PERIOD_DAYS`).
- **My subscription** displays status (active/inactive), days left, expiry date (`dd.mm.yyyy`), remaining traffic (or ♾️), and a copy-friendly subscription URL; the existing WebApp button still opens the subscription.
- **Instructions** menu offers OS options: 🍏 iOS / MacOS, 🤖 Android, 🖥️ Windows, 👨🏻‍💻 Linux. Each platform shows setup steps with download buttons sourced from `HAPP_*` variables and a back button to the OS list.
- **FAQ** presents inline links (privacy, terms, rules, offer) controlled by `FAQ_*_ENABLED` and `FAQ_*_URL` pairs.
- **Support** includes a “Write to support” button using `SUPPORT_LINK` plus a back button.
- Optional photos can precede key sections via `*_IMAGE_ENABLED` + `*_IMAGE_PATH` pairs for start, subscription, instructions, FAQ, and support (paths may be local files or HTTP/HTTPS URLs).

### Goods configuration (`goods.json`)
`goods.example.json` holds a sample tariff set; copy it to `goods.json` during installation or later. The real `goods.json` is not tracked in git. A minimal example:
```json
[
  {
    "title": "Basic VPN",
    "price": {"en": 1, "ru": 100, "stars": 50},
    "callback": "basic_vpn",
    "months": 1,
    "description": "Example tariff; replace with your real plans"
  }
]
```
Update titles, prices, months, and callbacks to match your offerings.

### Protocols configuration
`protocols.json` defines protocol options and inbound names for Marzban. Adjust the file to match your panel inbounds and set `PROTOCOLS_CONFIG=protocols.json` in `.env`.

## nginx configuration
Example configs are provided in `nginx/`:
- `nginx/nginx.conf.example` – base nginx config with optional `stream {}` block for TLS passthrough/SNI sharing of port 443.
- `nginx/bot.conf.example` – site config with HTTP→HTTPS redirect, Let’s Encrypt challenge location, webhook proxy (`/webhook` → `127.0.0.1:8080/webhook`), and payment link placeholders (`/pay/sber`, `/pay/tbank`).

Setup steps (also automated by `install.sh`):
1. Copy the example configs to `/etc/nginx/nginx.conf` and `/etc/nginx/sites-available/bot.conf`, adjusting the domain.
2. Create a symlink to `/etc/nginx/sites-enabled/bot.conf`.
3. Test config with `nginx -t` and reload.
4. Obtain certificates with Certbot, e.g. `certbot --nginx -d bot.example.com --email admin@example.com --agree-tos --redirect`.

## CLI for the bot (`mshop`)
`mshop` is installed to `/usr/local/bin/mshop` by the installer.

Commands:
- `mshop status` – Show container status
- `mshop start` / `mshop stop` / `mshop restart`
- `mshop reload` – Restart bot container
- `mshop logs` – Tail bot logs
- `mshop edit .env|docker-compose.yml|goods.json|protocols.json|db` – Edit configs or open DB shell (with warning)
- `mshop update` – Pull repo and images, restart
- `mshop backup-db` – Create DB backup (uploads to Telegram if `TG_BACKUP_BOT_TOKEN` and `TG_BACKUP_CHAT_ID` set)
- `mshop restore-db <backup.tar.gz>` – Restore DB from backup
- `mshop webhook-info|webhook-set|webhook-delete|webhook-reset` – Manage Telegram webhook using `WEBHOOK_URL` + `/webhook`
- `mshop help` – Show help

## CLI for nginx (`mnginx`)
`mnginx` is installed to `/usr/local/bin/mnginx` by the installer.

Commands:
- `mnginx status|start|stop|restart`
- `mnginx enable` – Enable nginx service and bot site symlink
- `mnginx reload` / `mnginx test`
- `mnginx logs` – Follow nginx logs
- `mnginx update` – Copy example configs to nginx and reload
- `mnginx version` – Show nginx version
- `mnginx help` – Show help

## Backup & restore
- Create backup: `mshop backup-db` (stores archive under `backups/` and optionally sends to Telegram).
- Restore: `mshop restore-db <path/to/archive.tar.gz>` (prompts before overwriting).

## Update
- Bot and services: `mshop update`
- nginx configs: `mnginx update`

## Troubleshooting
- Check bot logs: `mshop logs`
- Test nginx config: `mnginx test`
- Reload nginx: `mnginx reload`
- Verify webhook: `curl -I https://your-domain.com/webhook`

Ensure your domain points to the server and certificates are valid when using webhooks.
