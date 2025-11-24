"""Valida configurações de transcodificação (US-031).

O objetivo aqui é garantir que o compose de mídia já declare os devices de
aceleração de hardware e limites de recursos obrigatórios para evitar que o
Jellyfin consuma o Raspberry Pi inteiro em sessões de transcode.
"""
from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MEDIA_COMPOSE = ROOT / "apps" / "docker-compose.media.yml"


def test_jellyfin_has_hwaccel_devices_and_limits():
    compose_text = MEDIA_COMPOSE.read_text()

    assert "JELLYFIN_DRI_DEVICE" in compose_text or "/dev/dri" in compose_text
    assert "JELLYFIN_V4L2" in compose_text or "/dev/video" in compose_text

    assert "JELLYFIN_MEMORY_LIMIT" in compose_text
    assert "JELLYFIN_CPU_LIMIT" in compose_text
    assert "${VIDEO_GID:-44}" in compose_text
