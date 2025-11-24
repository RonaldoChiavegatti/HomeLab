# homelab-infra

Infraestrutura mínima em contêineres para um homelab baseado em Raspberry Pi (Debian/Ubuntu). Este repositório entrega apenas o
**esqueleto inicial**: diretórios, composes separados por domínio e automações básicas para permitir iterações futuras.

## Filosofia
- Somente serviços open source, empacotados via Docker.
- Convenções de diretórios voltadas para SSD dedicado em `/srv/homelab`.
- Separação de stacks: `infra/`, `core/`, `apps/` para facilitar ciclos de vida independentes.
- Comentários e TODOs em português para orientar as próximas histórias.

## Visão geral de diretórios
```
./
├── README.md
├── .env.example
├── .gitignore
├── Makefile
├── infra/
│   └── docker-compose.yml
├── core/
│   └── docker-compose.yml
├── apps/
│   ├── docker-compose.git.yml
│   ├── docker-compose.vaultwarden.yml
│   ├── docker-compose.media.yml
│   ├── docker-compose.homeassistant.yml
│   └── docker-compose.mail.yml
└── tests/
    ├── requirements.txt
    └── test_smoke.py
```

Estrutura esperada no host (`/srv/homelab`):
```
/srv/homelab
├── traefik/
├── wireguard/
├── nextcloud/
│   ├── db/
│   ├── redis/
│   └── data/
├── git/
├── vaultwarden/
├── media/
│   ├── jellyfin/
│   ├── library/
│   └── transcodes/
├── homeassistant/
└── mail/
```

## Pré-requisitos
- Docker e Docker Compose v2 instalados (veja automação em `infra/provision/docker_setup.sh`).
- Usuário local `homelab` com permissões para `/srv/homelab`.
- Arquivo `.env` preenchido a partir de `.env.example` (sem segredos aqui).
- SSD dedicado montado em `/srv` com filesystem `ext4` (ou definido via flag). Use `make prepare-data-dirs` para criar a
  árvore inicial em `/srv/homelab`.

## Provisionamento do host (US-001) e Docker (US-002)
- Para preparar o Raspberry Pi (Debian/Ubuntu) com usuário `homelab`, SSH por chave e atualizações automáticas, use os scripts em
  `infra/provision/`.
- Automação de Docker/Compose e validação de hello-world também ficam em `infra/provision/`.
- Execução típica:
  ```bash
  make provision-host HOMELAB_USER=homelab  # requer sudo e variável SSH_PUBLIC_KEY_PATH apontando para sua chave
  make validate-host  # roda verificação do SO, pacotes e hardening de SSH

  make docker-setup HOMELAB_USER=homelab  # instala Docker Engine + Compose v2 e coloca o usuário no grupo docker
  make validate-docker HOMELAB_USER=homelab  # verifica docker/compose sem sudo e roda hello-world

  # Criar e/ou validar estrutura de dados em /srv/homelab (US-003)
  make prepare-data-dirs  # cria diretórios ausentes em /srv/homelab e valida filesystem do SSD
  make validate-data-dirs  # apenas valida filesystem + diretórios

  # Configurar firewall/NAT com UFW (US-012)
  make configure-firewall UFW_WAN_INTERFACE=eth0  # aplica política deny incoming, libera portas necessárias e NAT do WireGuard
  make validate-firewall  # varre portas TCP/UDP abertas para garantir exposição mínima
  ```

## Backup do Nextcloud (US-022)
- Script `core/nextcloud/backup_nextcloud.py` faz snapshot incremental com `rsync` + hardlinks.
- Variáveis de ambiente configuráveis no `.env`: `NEXTCLOUD_BACKUP_SOURCE`, `NEXTCLOUD_BACKUP_TARGET`, `NEXTCLOUD_BACKUP_LOG`
  e `NEXTCLOUD_BACKUP_RETENTION`.
- Execução manual:
  ```bash
  make backup-nextcloud  # usa defaults do .env
  python core/nextcloud/backup_nextcloud.py --dry-run  # apenas imprime comando rsync
  ```
- Agendamento via systemd:
  ```bash
  sudo cp core/nextcloud/nextcloud-backup.service /etc/systemd/system/
  sudo cp core/nextcloud/nextcloud-backup.timer /etc/systemd/system/
  sudo systemctl daemon-reload
  sudo systemctl enable --now nextcloud-backup.timer
  ```
- Logs: append em `${NEXTCLOUD_BACKUP_LOG}` e status em `${NEXTCLOUD_BACKUP_TARGET}/last_run.json`.
- Restore manual (teste recomendado após primeiro backup):
  ```bash
  sudo systemctl stop docker  # ou ao menos containers do Nextcloud
  rsync -a <PATH_DO_SNAPSHOT>/ /srv/homelab/nextcloud/data/
  sudo systemctl start docker
  ```

## Uso rápido
```
# Subir apenas a stack de infraestrutura (Traefik + whoami de teste)
make up-infra

# Ver logs da stack de infra
make logs-infra

# Executar testes de fumaça (usa docker compose da pasta infra)
make test
```

## TLS automático via Traefik (US-010)
- Traefik já está configurado com redirecionamento HTTP→HTTPS e resolver ACME usando Let's Encrypt (staging por padrão via
  `ACME_CA_SERVER`).
- Ajuste `HOMELAB_DOMAIN` e `ACME_EMAIL` no `.env`; para produção, troque `ACME_CA_SERVER` para o endpoint público do
  Let's Encrypt.
- O arquivo `acme.json` é persistido em `/srv/homelab/traefik` dentro do host; garanta permissões restritas (0600) após
  primeira emissão.

## Próximos passos (backlog sugerido)
- Configurar TLS completo via ACME (Let's Encrypt) no Traefik.
- Adicionar WireGuard (VPN) à stack infra.
- Completar setup do Nextcloud (com PostgreSQL + Redis) na stack core.
- Integrar Gitea/Forgejo, Vaultwarden, Jellyfin, Home Assistant e Mail na stack apps.
- Automatizar backups e monitoramento.
```
