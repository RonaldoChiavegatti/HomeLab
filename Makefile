COMPOSE_INFRA = docker compose -f infra/docker-compose.yml
COMPOSE_CORE = docker compose -f core/docker-compose.yml
COMPOSE_APPS = docker compose -f apps/docker-compose.git.yml -f apps/docker-compose.vaultwarden.yml -f apps/docker-compose.media.yml -f apps/docker-compose.homeassistant.yml -f apps/docker-compose.mail.yml

HOMELAB_USER ?= homelab

## Comandos básicos (usar `make <alvo>`)

provision-host:
	cd infra/provision && sudo HOMELAB_USER=$(HOMELAB_USER) ./host_provision.sh

validate-host:
	cd infra/provision && python3 validate_host.py

docker-setup:
	cd infra/provision && sudo HOMELAB_USER=$(HOMELAB_USER) ./docker_setup.sh

validate-docker:
	cd infra/provision && python3 validate_docker.py --user $(HOMELAB_USER)

up-infra:
	$(COMPOSE_INFRA) up -d

down-infra:
	$(COMPOSE_INFRA) down

logs-infra:
	$(COMPOSE_INFRA) logs -f

up-core:
	$(COMPOSE_CORE) up -d

down-core:
	$(COMPOSE_CORE) down

logs-core:
	$(COMPOSE_CORE) logs -f

up-apps:
	$(COMPOSE_APPS) up -d

down-apps:
	$(COMPOSE_APPS) down

logs-apps:
	$(COMPOSE_APPS) logs -f

# Testes básicos de fumaça (usa pytest)
test:
	python -m venv .venv && . .venv/bin/activate && pip install -r tests/requirements.txt && pytest -q tests

# Backup dummy para demonstrar gancho futuro
backup-dummy:
	@echo "TODO: implementar rotina de backup incremental em /srv/homelab" && exit 0

.PHONY: up-infra down-infra logs-infra up-core down-core logs-core up-apps down-apps logs-apps test backup-dummy provision-host validate-host docker-setup validate-docker
