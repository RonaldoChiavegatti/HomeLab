"""Validações rápidas do compose do Nextcloud (US-021).

Garante que a stack core está pronta para criação de usuários/sync
com serviços e envs mínimos.
"""
from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
COMPOSE_FILE = ROOT / "core" / "docker-compose.yml"


def test_nextcloud_services_declared():
    content = COMPOSE_FILE.read_text()

    assert "nextcloud:" in content
    assert "nextcloud-web:" in content
    assert "nextcloud-cron:" in content

    assert "nextcloud:28-fpm" in content
    assert "POSTGRES_HOST=postgres" in content
    assert "REDIS_HOST=redis" in content
    assert "NEXTCLOUD_ADMIN_USER" in content
    assert "NEXTCLOUD_ADMIN_PASSWORD" in content
    assert "/srv/homelab/nextcloud/data:/var/www/html" in content
    assert "traefik.http.routers.nextcloud.rule" in content
    assert "proxy_net" in content and "internal_net" in content
