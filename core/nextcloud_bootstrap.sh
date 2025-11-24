#!/usr/bin/env bash
set -euo pipefail

# Cria usuários iniciais do Nextcloud e valida o sync básico via CLI.
# Requer docker compose com stack core já disponível.

ROOT_DIR="$(cd "$(dirname "$0")" && pwd)"
COMPOSE="docker compose -f ${ROOT_DIR}/docker-compose.yml"

ADMIN_USER=${NEXTCLOUD_ADMIN_USER:-nc_admin}
ADMIN_PASS=${NEXTCLOUD_ADMIN_PASSWORD:-CHANGE_ME}
REGULAR_USER=${NEXTCLOUD_USER:-nc_user}
REGULAR_PASS=${NEXTCLOUD_USER_PASSWORD:-CHANGE_ME}
DOMAIN=${HOMELAB_DOMAIN:-example.local}
SYNC_DIR=${NEXTCLOUD_SYNC_DIR:-/tmp/nextcloud-sync}

function start_stack() {
    ${COMPOSE} up -d postgres redis nextcloud nextcloud-cron nextcloud-web
}

function wait_nextcloud() {
    echo "Aguardando Nextcloud inicializar..."
    for i in {1..12}; do
        if ${COMPOSE} exec -T nextcloud php occ status >/dev/null 2>&1; then
            return 0
        fi
        sleep 5
    done
    echo "Falha ao validar o Nextcloud após 60s" >&2
    exit 1
}

function ensure_user() {
    local user=$1
    local password=$2
    local display=$3

    if ${COMPOSE} exec -T nextcloud php occ user:list | grep -q " - $user"; then
        echo "Usuário $user já existe, pulando criação."
        return
    fi

    OC_PASS="$password" ${COMPOSE} exec -T nextcloud php occ user:add --password-from-env --display-name "$display" "$user"
}

function validate_sync_cli() {
    mkdir -p "$SYNC_DIR"
    echo "Arquivo de teste gerado em $(date --iso-8601=seconds)" >"${SYNC_DIR}/sync-check.txt"
    nextcloudcmd --version >/dev/null 2>&1 || {
        echo "nextcloudcmd não encontrado; instale o cliente desktop/CLI do Nextcloud." >&2
        return 1
    }

    nextcloudcmd --non-interactive "${SYNC_DIR}" "https://${DOMAIN}" --user "$REGULAR_USER" --password "$REGULAR_PASS"
}

start_stack
wait_nextcloud

ensure_user "$ADMIN_USER" "$ADMIN_PASS" "Administrador"
ensure_user "$REGULAR_USER" "$REGULAR_PASS" "Usuário para sync"

validate_sync_cli || true

echo "Bootstrap concluído. Verifique o cliente desktop apontando para https://${DOMAIN} com o usuário ${REGULAR_USER}."
