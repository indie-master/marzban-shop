#!/usr/bin/env bash
set -e

INSTALL_DIR="/opt/marzban-shop"
REPO_URL="https://github.com/USER/marzban-shop.git" # replace USER with your fork
DOMAIN_BOT="bot.example.com"
EMAIL_LETSENCRYPT="admin@example.com"

require_root() {
    if [[ $EUID -ne 0 ]]; then
        echo "This script must be run as root." >&2
        exit 1
    fi
}

ensure_dep() {
    local pkg=$1
    if ! command -v "$pkg" >/dev/null 2>&1; then
        apt-get update
        apt-get install -y "$pkg"
    fi
}

install_docker() {
    if ! command -v docker >/dev/null 2>&1; then
        echo "Installing Docker..."
        curl -fsSL https://get.docker.com | sh
    fi
}

install_compose() {
    if ! docker compose version >/dev/null 2>&1; then
        echo "Installing Docker Compose plugin..."
        local compose_url="https://github.com/docker/compose/releases/download/v2.24.6/docker-compose-$(uname -s)-$(uname -m)"
        mkdir -p /usr/local/lib/docker/cli-plugins
        curl -SL "$compose_url" -o /usr/local/lib/docker/cli-plugins/docker-compose
        chmod +x /usr/local/lib/docker/cli-plugins/docker-compose
    fi
}

clone_or_update_repo() {
    if [[ -d "$INSTALL_DIR/.git" ]]; then
        echo "Updating repository in $INSTALL_DIR"
        cd "$INSTALL_DIR"
        git pull
    else
        echo "Cloning repository to $INSTALL_DIR"
        git clone "$REPO_URL" "$INSTALL_DIR"
    fi
}

ensure_files() {
    cd "$INSTALL_DIR"
    if [[ ! -f .env ]]; then
        echo "Creating empty .env (fill it with your values)"
        touch .env
    fi
    if [[ ! -f goods.json ]]; then
        echo "Creating goods.json from template"
        cat <<'JSON' > goods.json
[
  {
    "title": "Basic VPN",
    "price": {"en": 1, "ru": 100, "stars": 50},
    "callback": "basic_vpn",
    "months": 1,
    "description": "Example tariff; replace with your real plans"
  }
]
JSON
    fi
}

update_env_value() {
    local key=$1
    local value=$2
    local file=$3
    if grep -q "^${key}=" "$file"; then
        sed -i "s|^${key}=.*|${key}=${value}|" "$file"
    else
        printf '\n%s=%s\n' "$key" "$value" >> "$file"
    fi
}

interactive_env_setup() {
    local env_file="$INSTALL_DIR/.env"
    echo "Configure basic .env values (press Enter to skip)"
    read -r -p "Enter BOT_TOKEN: " bot_token
    [[ -n "$bot_token" ]] && update_env_value "BOT_TOKEN" "$bot_token" "$env_file"

    read -r -p "Enter SHOP_NAME: " shop_name
    [[ -n "$shop_name" ]] && update_env_value "SHOP_NAME" "$shop_name" "$env_file"

    read -r -p "Enter PANEL_HOST (e.g. https://panel.example.com): " panel_host
    [[ -n "$panel_host" ]] && update_env_value "PANEL_HOST" "$panel_host" "$env_file"

    read -r -p "Enter PANEL_GLOBAL (e.g. https://panel.example.com): " panel_global
    [[ -n "$panel_global" ]] && update_env_value "PANEL_GLOBAL" "$panel_global" "$env_file"

    read -r -p "Enter PANEL_USER: " panel_user
    [[ -n "$panel_user" ]] && update_env_value "PANEL_USER" "$panel_user" "$env_file"

    read -r -p "Enter PANEL_PASS: " panel_pass
    [[ -n "$panel_pass" ]] && update_env_value "PANEL_PASS" "$panel_pass" "$env_file"

    read -r -p "Enter DB_NAME: " db_name
    [[ -n "$db_name" ]] && update_env_value "DB_NAME" "$db_name" "$env_file"

    read -r -p "Enter DB_USER: " db_user
    [[ -n "$db_user" ]] && update_env_value "DB_USER" "$db_user" "$env_file"

    read -r -p "Enter DB_PASS: " db_pass
    [[ -n "$db_pass" ]] && update_env_value "DB_PASS" "$db_pass" "$env_file"

    read -r -p "Enter TG_INFO_CHANEL (admin chat id): " tg_info
    [[ -n "$tg_info" ]] && update_env_value "TG_INFO_CHANEL" "$tg_info" "$env_file"
}

prepare_goods() {
    if [[ ! -f "$INSTALL_DIR/goods.json" ]]; then
        echo "goods.json not found; creating template"
        cat <<'JSON' > "$INSTALL_DIR/goods.json"
[
  {
    "title": "Basic VPN",
    "price": {"en": 1, "ru": 100, "stars": 50},
    "callback": "basic_vpn",
    "months": 1,
    "description": "Example tariff; replace with your real plans"
  }
]
JSON
    fi
    read -r -p "Keep example goods.json? [Y/n]: " keep_goods
    if [[ "$keep_goods" =~ ^[Nn]$ ]]; then
        echo "Please edit $INSTALL_DIR/goods.json manually later."
    fi
}

configure_nginx() {
    echo "Configuring nginx..."
    mkdir -p /etc/nginx/sites-available /etc/nginx/sites-enabled /var/www/letsencrypt
    if [[ -f "$INSTALL_DIR/nginx/bot.conf.example" ]]; then
        sed "s/bot.example.com/$DOMAIN_BOT/g" "$INSTALL_DIR/nginx/bot.conf.example" > /etc/nginx/sites-available/bot.conf
    fi
    if [[ ! -L /etc/nginx/sites-enabled/bot.conf ]]; then
        ln -s /etc/nginx/sites-available/bot.conf /etc/nginx/sites-enabled/bot.conf
    fi
    nginx -t && systemctl reload nginx
}

obtain_certificate() {
    echo "Requesting Let's Encrypt certificate (may require DNS pointing)..."
    certbot --nginx -d "$DOMAIN_BOT" --email "$EMAIL_LETSENCRYPT" --agree-tos --redirect || true
}

run_compose() {
    cd "$INSTALL_DIR"
    docker compose up -d
}

install_cli() {
    local target=$1
    local source=$2
    if [[ -f "$source" ]]; then
        if [[ -f "$target" ]]; then
            read -r -p "File $target exists. Overwrite? [Y/n]: " overwrite
            if [[ "$overwrite" =~ ^[Nn]$ ]]; then
                echo "Skipping $target"
                return
            fi
        fi
        cp "$source" "$target"
        chmod +x "$target"
        echo "Installed $(basename "$target")"
    fi
}

main() {
    require_root
    ensure_dep curl
    ensure_dep git
    ensure_dep nginx
    ensure_dep certbot
    ensure_dep python3-certbot-nginx
    install_docker
    install_compose
    clone_or_update_repo
    ensure_files
    interactive_env_setup
    prepare_goods
    configure_nginx
    obtain_certificate
    run_compose
    install_cli /usr/local/bin/mshop "$INSTALL_DIR/scripts/mshop"
    install_cli /usr/local/bin/mnginx "$INSTALL_DIR/scripts/mnginx"
    echo "Installation finished. Update .env and goods.json if needed, then run docker compose up -d."
}

main "$@"
