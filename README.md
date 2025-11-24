# homelab-infra

Infraestrutura mínima em contêineres para um homelab baseado em Raspberry Pi (Debian/Ubuntu). Este repositório entrega apenas o **esqueleto inicial**: diretórios, composes separados por domínio e automações básicas para permitir iterações futuras.

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
│   └── transcodes/
├── homeassistant/
└── mail/
```

## Pré-requisitos
- Docker e Docker Compose v2 instalados.
- Usuário local `homelab` com permissões para `/srv/homelab`.
- Arquivo `.env` preenchido a partir de `.env.example` (sem segredos aqui).

## Provisionamento do host (US-001)
- Para preparar o Raspberry Pi (Debian/Ubuntu) com usuário `homelab`, SSH por chave e atualizações automáticas, use os scripts em `infra/provision/`.
- Execução típica:
  ```bash
  make provision-host HOMELAB_USER=homelab  # requer sudo e variável SSH_PUBLIC_KEY_PATH apontando para sua chave
  make validate-host  # roda verificação do SO, pacotes e hardening de SSH
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

## Próximos passos (backlog sugerido)
- Configurar TLS completo via ACME (Let's Encrypt) no Traefik.
- Adicionar WireGuard (VPN) à stack infra.
- Completar setup do Nextcloud (com PostgreSQL + Redis) na stack core.
- Integrar Gitea/Forgejo, Vaultwarden, Jellyfin, Home Assistant e Mail na stack apps.
- Automatizar backups e monitoramento.
```

