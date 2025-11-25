"""Teste E2E do Gitea integrado ao Traefik (US-040).

Sobe infra + stack git, cria usuário via API, repositório e valida
fluxo de clone/push usando container com git CLI.
"""
from __future__ import annotations

import os
import subprocess
import time
from typing import Dict

import pytest
import requests
import urllib3

ROOT = os.path.dirname(os.path.dirname(__file__))
INFRA_COMPOSE = os.path.join(ROOT, "infra", "docker-compose.yml")
GIT_COMPOSE = os.path.join(ROOT, "apps", "docker-compose.git.yml")

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)


def _run(cmd: list[str]) -> None:
    """Executa comando docker compose na raiz do repositório."""

    subprocess.check_call(cmd, cwd=ROOT)


def setup_module(module):
    _run(["docker", "compose", "-f", INFRA_COMPOSE, "up", "-d"])
    _run(["docker", "compose", "-f", GIT_COMPOSE, "up", "-d"])
    _wait_for_gitea()


def teardown_module(module):
    _run(["docker", "compose", "-f", GIT_COMPOSE, "down"])
    _run(["docker", "compose", "-f", INFRA_COMPOSE, "down"])


def _host_header() -> Dict[str, str]:
    domain = os.getenv("HOMELAB_DOMAIN", "example.local")
    return {"Host": f"git.{domain}"}


def _https_port() -> str:
    return os.getenv("TRAEFIK_HTTPS_PORT", "443")


def _wait_for_gitea(timeout: int = 120) -> str:
    """Espera endpoint de versão do Gitea responder 200 com JSON válido."""

    deadline = time.time() + timeout
    last_error = ""
    while time.time() < deadline:
        try:
            resp = requests.get(
                f"https://localhost:{_https_port()}/api/v1/version",
                headers=_host_header(),
                verify=False,
                timeout=10,
            )
            if resp.status_code == 200 and resp.json().get("version"):
                return resp.json()["version"]
            last_error = f"status {resp.status_code}"
        except Exception as exc:  # pragma: no cover - ajuda em CI
            last_error = str(exc)
        time.sleep(4)
    raise AssertionError(f"Gitea não ficou saudável: {last_error}")


def _create_token(username: str, password: str, token_name: str) -> str:
    resp = requests.post(
        f"https://localhost:{_https_port()}/api/v1/users/{username}/tokens",
        headers=_host_header(),
        auth=(username, password),
        json={"name": token_name},
        verify=False,
        timeout=15,
    )
    assert resp.status_code in (200, 201), resp.text
    return resp.json()["sha1"]


def _create_user(admin_token: str, username: str, password: str, email: str) -> None:
    resp = requests.post(
        f"https://localhost:{_https_port()}/api/v1/admin/users",
        headers={**_host_header(), "Authorization": f"token {admin_token}"},
        json={
            "login_name": username,
            "username": username,
            "email": email,
            "password": password,
            "must_change_password": False,
        },
        verify=False,
        timeout=15,
    )
    assert resp.status_code == 201, resp.text


def _create_repo(user_token: str, repo_name: str) -> None:
    resp = requests.post(
        f"https://localhost:{_https_port()}/api/v1/user/repos",
        headers={**_host_header(), "Authorization": f"token {user_token}"},
        json={"name": repo_name, "auto_init": True, "default_branch": "main"},
        verify=False,
        timeout=15,
    )
    assert resp.status_code == 201, resp.text


@pytest.mark.integration
def test_gitea_clone_and_push(tmp_path):
    """Cria usuário, repo e valida clone/push via git dentro de container."""

    domain = os.getenv("HOMELAB_DOMAIN", "example.local")
    https_port = _https_port()
    _wait_for_gitea()

    suffix = str(int(time.time()))
    admin_user = os.getenv("GITEA_ADMIN_USER", "gitea_admin")
    admin_password = os.getenv("GITEA_ADMIN_PASSWORD", "changeme")
    admin_token = _create_token(admin_user, admin_password, f"admin-token-{suffix}")

    new_user = f"ci-user-{suffix}"
    new_password = f"pass-{suffix}"
    new_email = f"{new_user}@example.local"
    _create_user(admin_token, new_user, new_password, new_email)

    user_token = _create_token(new_user, new_password, f"user-token-{suffix}")
    repo_name = f"demo-repo-{suffix}"
    _create_repo(user_token, repo_name)

    clone_url = (
        f"https://{new_user}:{new_password}@git.{domain}:{https_port}/{new_user}/{repo_name}.git"
    )

    script = (
        "git config --global user.email 'ci@example.local' && "
        "git config --global user.name 'CI Runner' && "
        f"git clone {clone_url} repo && "
        "cd repo && echo 'hello from ci' >> README.md && "
        "git add README.md && git commit -m 'ci push' && git push origin main"
    )

    cmd = [
        "docker",
        "run",
        "--rm",
        "--network",
        "host",
        "--add-host",
        f"git.{domain}:127.0.0.1",
        "-e",
        "GIT_SSL_NO_VERIFY=true",
        "-v",
        f"{tmp_path}:/work",
        "-w",
        "/work",
        "alpine/git",
        "sh",
        "-c",
        script,
    ]

    subprocess.check_call(cmd, cwd=ROOT)

    # Confirma que commit ficou no repo (HEAD avançou)
    head_check = subprocess.check_output(
        [
            "docker",
            "run",
            "--rm",
            "--network",
            "host",
            "--add-host",
            f"git.{domain}:127.0.0.1",
            "-e",
            "GIT_SSL_NO_VERIFY=true",
            "-w",
            "/repo",
            "-v",
            f"{tmp_path}/repo:/repo",
            "alpine/git",
            "sh",
            "-c",
            "git log --oneline -1",
        ],
        cwd=ROOT,
        text=True,
    )

    assert "ci push" in head_check
