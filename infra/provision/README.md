# Provisionamento inicial do host (US-001) e Docker (US-002)

Automação mínima para preparar um Raspberry Pi (Debian/Ubuntu) como host dos containers.

## Scripts
- `host_provision.sh`: aplica ajustes de sistema, cria o usuário `homelab`, habilita SSH por chave e ativa atualizações automáticas.
- `validate_host.py`: verifica se o host atende aos critérios de segurança/performance da história US-001.
- `docker_setup.sh`: instala Docker Engine + Docker Compose v2 a partir do repositório oficial e garante que `docker ps` funciona sem sudo.
- `validate_docker.py`: valida a instalação do Docker/Compose, confere grupo `docker` e roda `hello-world`.

## Uso
```
# Provisionar (necessita root e variável SSH_PUBLIC_KEY_PATH apontando para sua chave pública)
sudo HOMELAB_USER=homelab SSH_PUBLIC_KEY_PATH=~/.ssh/id_rsa.pub ./host_provision.sh

# Validar estado atual do host
python3 validate_host.py

# Instalar Docker + Compose para o usuário informado (requer root)
sudo HOMELAB_USER=homelab ./docker_setup.sh

# Validar acesso ao Docker/Compose e rodar hello-world
python3 validate_docker.py --user homelab
```

### O que é configurado
- Garantia de SO Debian/Ubuntu.
- Instalação de pacotes mínimos: openssh-server, sudo, unattended-upgrades, ca-certificates, curl.
- Usuário `homelab` com sudo sem senha e chave pública fornecida.
- SSH com `PasswordAuthentication no`, `PermitRootLogin prohibit-password` e `PubkeyAuthentication yes`.
- Atualizações automáticas de segurança (`unattended-upgrades`).
- Docker Engine e Docker Compose v2 instalados do repositório oficial, com daemon habilitado.
- Usuário `homelab` adicionado ao grupo `docker` e teste `hello-world` confirmando execução de contêineres.
