#!/usr/bin/env bash
set -euo pipefail

# Provisionador mínimo para hosts Debian/Ubuntu arm64 (Raspberry Pi).
# Prepara o host para receber os containers do homelab com foco em segurança.

HOMELAB_USER=${HOMELAB_USER:-homelab}
SSH_PUBLIC_KEY_PATH=${SSH_PUBLIC_KEY_PATH:-${HOME}/.ssh/id_rsa.pub}
PACKAGES=("openssh-server" "sudo" "unattended-upgrades" "ca-certificates" "curl" "ufw")
UFW_WAN_INTERFACE=${UFW_WAN_INTERFACE:-eth0}
UFW_DASHBOARD_CIDR=${UFW_DASHBOARD_CIDR:-192.168.0.0/16}
WIREGUARD_SUBNET=${WIREGUARD_SUBNET:-10.13.13.0/24}

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
            echo "[OK] SO suportado: ${PRETTY_NAME}" ;;
        *)
            echo "[ERRO] SO não suportado (${PRETTY_NAME:-${ID}}). Use Debian ou Ubuntu." >&2
            exit 1 ;;
    esac
}

install_packages() {
    echo "[INFO] Atualizando pacotes e instalando dependências básicas..."
    apt-get update -y
    DEBIAN_FRONTEND=noninteractive apt-get install -y --no-install-recommends "${PACKAGES[@]}"
}

create_user() {
    if id "${HOMELAB_USER}" >/dev/null 2>&1; then
        echo "[OK] Usuário ${HOMELAB_USER} já existe."
    else
        echo "[INFO] Criando usuário ${HOMELAB_USER} com sudo sem senha."
        useradd -m -s /bin/bash "${HOMELAB_USER}"
        usermod -aG sudo "${HOMELAB_USER}"
        echo "%${HOMELAB_USER} ALL=(ALL) NOPASSWD:ALL" > \
            "/etc/sudoers.d/010-${HOMELAB_USER}-nopasswd"
        chmod 440 "/etc/sudoers.d/010-${HOMELAB_USER}-nopasswd"
    fi
}

configure_ssh_keys() {
    local key_path
    key_path=$(readlink -f "${SSH_PUBLIC_KEY_PATH}")
    if [[ ! -f "${key_path}" ]]; then
        echo "[ERRO] Chave pública não encontrada em ${key_path}. Configure SSH_PUBLIC_KEY_PATH." >&2
        exit 1
    fi
    local ssh_dir="/home/${HOMELAB_USER}/.ssh"
    mkdir -p "${ssh_dir}"
    cat "${key_path}" >> "${ssh_dir}/authorized_keys"
    chown -R "${HOMELAB_USER}:${HOMELAB_USER}" "${ssh_dir}"
    chmod 700 "${ssh_dir}"
    chmod 600 "${ssh_dir}/authorized_keys"
    echo "[OK] Chave pública adicionada para ${HOMELAB_USER}."
}

harden_sshd() {
    echo "[INFO] Aplicando hardening mínimo do SSH (sem senha, root bloqueado)."
    mkdir -p /etc/ssh/sshd_config.d
    cat > /etc/ssh/sshd_config.d/010-homelab.conf <<'CFG'
# Gerado por host_provision.sh - não editar manualmente sem entender o impacto.
PasswordAuthentication no
PermitRootLogin prohibit-password
PubkeyAuthentication yes
ChallengeResponseAuthentication no
UsePAM yes
CFG
    if command -v systemctl >/dev/null 2>&1; then
        systemctl reload ssh || systemctl reload sshd || true
    else
        service ssh reload || true
    fi
}

configure_unattended_upgrades() {
    echo "[INFO] Habilitando atualizações automáticas de segurança."
    cat > /etc/apt/apt.conf.d/20auto-upgrades <<'AUTO'
APT::Periodic::Update-Package-Lists "1";
APT::Periodic::Unattended-Upgrade "1";
AUTO
    dpkg-reconfigure --priority=low unattended-upgrades
    systemctl enable unattended-upgrades || true
    systemctl start unattended-upgrades || true
}

ensure_nat_rules() {
    local rules_file="/etc/ufw/before.rules"
    local marker="# HOMELAB-WIREGUARD-NAT"
    if grep -q "${marker}" "${rules_file}"; then
        return
    fi

    echo "[INFO] Adicionando NAT para WireGuard em ${rules_file} (interface ${UFW_WAN_INTERFACE}, subnet ${WIREGUARD_SUBNET})."
    cat >> "${rules_file}" <<RULES
${marker}
*nat
:POSTROUTING ACCEPT [0:0]
-A POSTROUTING -s ${WIREGUARD_SUBNET} -o ${UFW_WAN_INTERFACE} -j MASQUERADE
COMMIT
RULES
}

configure_ufw_sysctl() {
    local sysctl_file="/etc/ufw/sysctl.conf"
    echo "[INFO] Habilitando forwarding IPv4/IPv6 no UFW para permitir NAT da VPN."
    sed -i 's/^#\?net.ipv4.ip_forward=.*/net.ipv4.ip_forward=1/' "${sysctl_file}"
    sed -i 's/^#\?net.ipv6.conf.default.forwarding=.*/net.ipv6.conf.default.forwarding=1/' "${sysctl_file}"
    sed -i 's/^#\?net.ipv6.conf.all.forwarding=.*/net.ipv6.conf.all.forwarding=1/' "${sysctl_file}"
}

configure_firewall() {
    echo "[INFO] Configurando firewall UFW (política padrão deny incoming)."
    ufw --force reset
    ufw default deny incoming
    ufw default allow outgoing

    ufw allow 22/tcp comment 'SSH de gestão'
    ufw allow ${TRAEFIK_HTTP_PORT:-80}/tcp comment 'HTTP Traefik'
    ufw allow ${TRAEFIK_HTTPS_PORT:-443}/tcp comment 'HTTPS Traefik'
    ufw allow from ${UFW_DASHBOARD_CIDR} to any port ${TRAEFIK_DASHBOARD_PORT:-8080} proto tcp comment 'Dashboard Traefik (LAN)'
    ufw allow ${WIREGUARD_PORT:-51820}/udp comment 'WireGuard VPN'

    ensure_nat_rules
    configure_ufw_sysctl
    ufw --force enable
    ufw status verbose
}

main() {
    require_root
    check_os
    install_packages
    create_user
    configure_ssh_keys
    harden_sshd
    configure_unattended_upgrades
    configure_firewall
    echo "[SUCESSO] Host pronto para receber os containers do homelab."
}

main "$@"
