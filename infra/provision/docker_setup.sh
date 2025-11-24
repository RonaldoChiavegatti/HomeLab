#!/usr/bin/env bash
set -euo pipefail

# Instala Docker Engine + Docker Compose v2 em Debian/Ubuntu arm64 (Raspberry Pi).
# Garante que o usuário informado consegue rodar `docker ps` e `docker compose` sem sudo.

HOMELAB_USER=${HOMELAB_USER:-homelab}
APT_PREREQS=("ca-certificates" "curl" "gnupg")
DOCKER_PACKAGES=("docker-ce" "docker-ce-cli" "containerd.io" "docker-buildx-plugin" "docker-compose-plugin")

require_root() {
    if [[ "${EUID}" -ne 0 ]]; then
        echo "[ERRO] Execute como root (sudo)." >&2
        exit 1
    fi
}

check_os() {
    if [[ ! -f /etc/os-release ]]; then
        echo "[ERRO] /etc/os-release não encontrado; sistema não suportado." >&2
        exit 1
    fi
    . /etc/os-release
    case "${ID}" in
        debian|ubuntu)
            if [[ -z "${VERSION_CODENAME:-}" ]]; then
                echo "[ERRO] VERSION_CODENAME ausente em /etc/os-release." >&2
                exit 1
            fi
            echo "[OK] SO suportado: ${PRETTY_NAME}" ;;
        *)
            echo "[ERRO] SO não suportado (${PRETTY_NAME:-${ID}}). Use Debian ou Ubuntu." >&2
            exit 1 ;;
    esac
}

install_prereqs() {
    echo "[INFO] Instalando dependências para repositório do Docker..."
    apt-get update -y
    DEBIAN_FRONTEND=noninteractive apt-get install -y --no-install-recommends "${APT_PREREQS[@]}"
}

configure_repository() {
    . /etc/os-release
    install -m 0755 -d /etc/apt/keyrings
    if [[ ! -f /etc/apt/keyrings/docker.gpg ]]; then
        curl -fsSL "https://download.docker.com/linux/${ID}/gpg" -o /etc/apt/keyrings/docker.gpg
        chmod a+r /etc/apt/keyrings/docker.gpg
    fi
    local arch
    arch=$(dpkg --print-architecture)
    echo "deb [arch=${arch} signed-by=/etc/apt/keyrings/docker.gpg] https://download.docker.com/linux/${ID} ${VERSION_CODENAME} stable" \
        > /etc/apt/sources.list.d/docker.list
    echo "[OK] Repositório oficial do Docker configurado."
}

install_docker() {
    echo "[INFO] Instalando Docker Engine e plugins Compose/Buildx..."
    apt-get update -y
    DEBIAN_FRONTEND=noninteractive apt-get install -y --no-install-recommends "${DOCKER_PACKAGES[@]}"
    systemctl enable docker >/dev/null 2>&1 || true
    systemctl start docker >/dev/null 2>&1 || true
    echo "[OK] Docker Engine e Compose instalados."
}

ensure_user_in_docker_group() {
    if ! id "${HOMELAB_USER}" >/dev/null 2>&1; then
        echo "[ERRO] Usuário ${HOMELAB_USER} não encontrado. Rode host_provision.sh antes ou ajuste HOMELAB_USER." >&2
        exit 1
    fi
    groupadd -f docker
    if id -nG "${HOMELAB_USER}" | tr ' ' "\n" | grep -q "^docker$"; then
        echo "[OK] Usuário ${HOMELAB_USER} já está no grupo docker."
    else
        usermod -aG docker "${HOMELAB_USER}"
        echo "[OK] Usuário ${HOMELAB_USER} adicionado ao grupo docker (relogin necessário)."
    fi
}

validate_cli_access() {
    echo "[INFO] Verificando docker/compose executando sem sudo para ${HOMELAB_USER}..."
    if ! su - "${HOMELAB_USER}" -c "docker ps >/dev/null"; then
        echo "[ERRO] docker ps falhou para ${HOMELAB_USER}. Verifique se o daemon está ativo e se o usuário já relogou." >&2
        exit 1
    fi
    if ! su - "${HOMELAB_USER}" -c "docker compose version >/dev/null"; then
        echo "[ERRO] docker compose version falhou para ${HOMELAB_USER}." >&2
        exit 1
    fi
    echo "[OK] docker ps e docker compose funcionam sem sudo."
}

run_hello_world() {
    echo "[INFO] Rodando hello-world para validar execução de contêineres..."
    local output
    if ! output=$(su - "${HOMELAB_USER}" -c "docker run --rm hello-world" 2>&1); then
        echo "[ERRO] Falha ao executar hello-world: ${output}" >&2
        exit 1
    fi
    if echo "${output}" | grep -q "Hello from Docker!"; then
        echo "[OK] hello-world retornou mensagem esperada. Docker funcionando."
    else
        echo "[ERRO] hello-world executou mas saída não contém 'Hello from Docker!'." >&2
        exit 1
    fi
}

main() {
    require_root
    check_os
    install_prereqs
    configure_repository
    install_docker
    ensure_user_in_docker_group
    validate_cli_access
    run_hello_world
    echo "[SUCESSO] Docker pronto para orquestrar os contêineres do homelab."
}

main "$@"
