#!/usr/bin/env bash
set -e

INSTALL_DIR="/root/marzban-shop"
REPO_URL="https://github.com/indie-master/marzban-shop.git" # replace USER with your fork
DOMAIN_BOT="bot.example.com"
EMAIL_LETSENCRYPT="admin@example.com"
SKIP_NGINX_SETUP=false

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

copy_or_link_prompt() {
    local src=$1
    local dst=$2
    local label=$3

    if [[ -f "$dst" ]]; then
        echo "$dst already exists; leaving it untouched."
        return
    fi

    if [[ -f "$src" ]]; then
        read -r -p "$label Create it from $(basename "$src")? [Y/n]: " ans
        if [[ "$ans" =~ ^[Nn]$ ]]; then
            echo "Skipping creation of $dst. Please create it manually."
            return
        fi
        cp "$src" "$dst"
        echo "Created $dst from $(basename "$src")"
    else
        echo "$src not found. Creating minimal $dst; please fill it manually."
        touch "$dst"
    fi
}

ensure_files() {
    cd "$INSTALL_DIR"

    copy_or_link_prompt "$INSTALL_DIR/.env.example" "$INSTALL_DIR/.env" ".env not found." || true

    if [[ ! -f "$INSTALL_DIR/goods.example.json" ]]; then
        cat <<'JSON' > "$INSTALL_DIR/goods.example.json"
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

    copy_or_link_prompt "$INSTALL_DIR/goods.example.json" "$INSTALL_DIR/goods.json" "goods.json not found." || true
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

prompt_nginx_mode() {
    echo "Do you want to configure nginx and obtain a Let's Encrypt certificate now?"
    echo "1) Yes, configure nginx and request certificate"
    echo "2) No, skip nginx setup (I'll configure nginx manually later)"
    read -r -p "[1/2]: " choice
    if [[ "$choice" != "1" ]]; then
        SKIP_NGINX_SETUP=true
        return
    fi

    read -r -p "Enter bot domain (e.g. bot.example.com). Leave empty to skip nginx setup: " domain
    if [[ -z "$domain" ]]; then
        SKIP_NGINX_SETUP=true
        echo "No domain provided. Skipping nginx configuration."
    else
        DOMAIN_BOT="$domain"
    fi
}

configure_nginx() {
    echo "Configuring nginx for $DOMAIN_BOT ..."
    mkdir -p /etc/nginx/sites-available /etc/nginx/sites-enabled /var/www/letsencrypt
    if [[ -f "$INSTALL_DIR/nginx/bot.conf.example" ]]; then
        sed "s/bot.example.com/$DOMAIN_BOT/g" "$INSTALL_DIR/nginx/bot.conf.example" > /etc/nginx/sites-available/bot.conf
    fi
    if [[ ! -L /etc/nginx/sites-enabled/bot.conf ]]; then
        ln -s /etc/nginx/sites-available/bot.conf /etc/nginx/sites-enabled/bot.conf
    fi
    if nginx -t; then
        systemctl reload nginx
    else
        echo "nginx configuration test failed. You may need certificates before it succeeds."
    fi
}

obtain_certificate() {
    echo "Requesting Let's Encrypt certificate (domain must point to this server)..."
    certbot --nginx -d "$DOMAIN_BOT" --email "$EMAIL_LETSENCRYPT" --agree-tos --redirect || true
    if nginx -t; then
        systemctl reload nginx
    else
        echo "nginx configuration still failing; please review /etc/nginx configs and certificates."
    fi
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
    prompt_nginx_mode

    if [[ "$SKIP_NGINX_SETUP" == false ]]; then
        configure_nginx
        obtain_certificate
    else
        echo "Skipping nginx setup. Configure it manually later using nginx/*.example or mnginx."
    fi

    run_compose
    install_cli /usr/local/bin/mshop "$INSTALL_DIR/scripts/mshop"
    install_cli /usr/local/bin/mnginx "$INSTALL_DIR/scripts/mnginx"

    echo "Installation finished. Update .env and goods.json if needed, then run docker compose up -d."
}

main "$@"
