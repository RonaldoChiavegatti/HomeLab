#!/usr/bin/env bash
# Bootstrap do repositório homelab-infra no Gitea (US-041).
set -euo pipefail

ROOT_DIR=$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)
cd "$ROOT_DIR"

# Carrega variáveis do .env se existir (sem exigir secrets no repo)
if [[ -f .env ]]; then
  set -a
  # shellcheck disable=SC1091
  source .env
  set +a
fi

GITEA_ADMIN_USER=${GITEA_ADMIN_USER:-gitea_admin}
GITEA_ADMIN_PASSWORD=${GITEA_ADMIN_PASSWORD:-changeme}
HOMELAB_DOMAIN=${HOMELAB_DOMAIN:-example.local}
TRAEFIK_HTTPS_PORT=${TRAEFIK_HTTPS_PORT:-443}
GITEA_REMOTE_NAME=${GITEA_REMOTE_NAME:-gitea}
GITEA_REPO_NAME=${GITEA_REPO_NAME:-homelab-infra}
DEFAULT_BRANCH=${GITEA_DEFAULT_BRANCH:-main}

API_BASE="https://git.${HOMELAB_DOMAIN}:${TRAEFIK_HTTPS_PORT}/api/v1"
REMOTE_HTTP="https://${GITEA_ADMIN_USER}:${GITEA_ADMIN_PASSWORD}@git.${HOMELAB_DOMAIN}:${TRAEFIK_HTTPS_PORT}/${GITEA_ADMIN_USER}/${GITEA_REPO_NAME}.git"

log() {
  echo "[bootstrap-gitea] $*"
}

require_clean_tree() {
  if ! git diff --quiet || ! git diff --cached --quiet; then
    log "Árvore de trabalho suja; faça commit antes de publicar."
    exit 1
  fi
}

ensure_token() {
  local token_name="bootstrap-$(date +%s)"
  local response
  response=$(curl -ksS -u "${GITEA_ADMIN_USER}:${GITEA_ADMIN_PASSWORD}" \
    -H "Content-Type: application/json" \
    -X POST \
    -d "{\"name\":\"${token_name}\"}" \
    "${API_BASE}/users/${GITEA_ADMIN_USER}/tokens")
  TOKEN=$(python - <<'PY'
import json, sys
resp = json.load(sys.stdin)
print(resp.get("sha1", ""))
PY
<<<"${response}")
  if [[ -z ${TOKEN} ]]; then
    log "Falha ao gerar token de API (verifique credenciais)."
    exit 1
  fi
}

repo_exists() {
  local status
  status=$(curl -ks -o /dev/null -w "%{http_code}" \
    -H "Authorization: token ${TOKEN}" \
    "${API_BASE}/repos/${GITEA_ADMIN_USER}/${GITEA_REPO_NAME}")
  [[ "${status}" == "200" ]]
}

create_repo() {
  local tmp
  tmp=$(mktemp)
  local status
  status=$(curl -ks -w "%{http_code}" -o "$tmp" \
    -H "Authorization: token ${TOKEN}" \
    -H "Content-Type: application/json" \
    -X POST \
    -d "{\"name\":\"${GITEA_REPO_NAME}\",\"private\":true,\"auto_init\":false,\"default_branch\":\"${DEFAULT_BRANCH}\"}" \
    "${API_BASE}/user/repos")
  if [[ "${status}" != "201" && "${status}" != "409" ]]; then
    log "Erro ao criar repositório (status ${status}):"
    cat "$tmp"
    rm -f "$tmp"
    exit 1
  fi
  rm -f "$tmp"
}

configure_remote() {
  if git remote get-url "${GITEA_REMOTE_NAME}" >/dev/null 2>&1; then
    log "Remote ${GITEA_REMOTE_NAME} já existe; atualizando URL."
    git remote set-url "${GITEA_REMOTE_NAME}" "${REMOTE_HTTP}"
  else
    git remote add "${GITEA_REMOTE_NAME}" "${REMOTE_HTTP}"
  fi
}

push_repo() {
  git push "${GITEA_REMOTE_NAME}" "HEAD:${DEFAULT_BRANCH}" --set-upstream
}

log "Garantindo diretório clean antes do push..."
require_clean_tree

log "Gerando token admin..."
ensure_token

if repo_exists; then
  log "Repositório ${GITEA_REPO_NAME} já existe; seguindo para push."
else
  log "Criando repositório ${GITEA_REPO_NAME} (privado) no Gitea..."
  create_repo
fi

log "Configurando remote ${GITEA_REMOTE_NAME} -> ${REMOTE_HTTP}"
configure_remote

log "Enviando branch atual para ${DEFAULT_BRANCH}..."
push_repo

log "Concluído. Valide clone/push via 'git ls-remote ${GITEA_REMOTE_NAME}'."
