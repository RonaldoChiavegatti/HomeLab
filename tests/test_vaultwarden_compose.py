"""Validações rápidas do compose do Vaultwarden (US-050).

Garante que o serviço está publicado via Traefik em HTTPS e persistindo
os dados no caminho esperado.
"""
from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
COMPOSE_FILE = ROOT / "apps" / "docker-compose.vaultwarden.yml"


def test_vaultwarden_compose_declares_https_route_and_data_dir():
    content = COMPOSE_FILE.read_text()

    assert "vaultwarden/server:alpine" in content
    assert "/srv/homelab/vaultwarden/data:/data" in content
    assert "DOMAIN=https://pw.${HOMELAB_DOMAIN:-example.local}" in content
    assert "ADMIN_TOKEN=${VAULTWARDEN_ADMIN_TOKEN:-changeme}" in content
    assert "SIGNUPS_ALLOWED=${VAULTWARDEN_SIGNUPS_ALLOWED:-true}" in content
    assert "traefik.http.routers.vaultwarden.rule=Host(`pw.${HOMELAB_DOMAIN}`)" in content
    assert "traefik.http.routers.vaultwarden.entrypoints=websecure" in content
    assert "traefik.http.routers.vaultwarden.tls=true" in content
    assert "traefik.http.routers.vaultwarden.tls.certresolver=letsencrypt" in content
    assert "proxy_net" in content and "internal_net" in content
