# Provisionamento inicial do host (US-001)

Automação mínima para preparar um Raspberry Pi (Debian/Ubuntu) como host dos containers.

## Scripts
- `host_provision.sh`: aplica ajustes de sistema, cria o usuário `homelab`, habilita SSH por chave e ativa atualizações automáticas.
- `validate_host.py`: verifica se o host atende aos critérios de segurança/performance da história US-001.

## Uso
```bash
# Provisionar (necessita root e variável SSH_PUBLIC_KEY_PATH apontando para sua chave pública)
sudo HOMELAB_USER=homelab SSH_PUBLIC_KEY_PATH=~/.ssh/id_rsa.pub ./host_provision.sh

# Validar estado atual do host
python3 validate_host.py
```

### O que é configurado
- Garantia de SO Debian/Ubuntu.
- Instalação de pacotes mínimos: openssh-server, sudo, unattended-upgrades, ca-certificates, curl.
- Usuário `homelab` com sudo sem senha e chave pública fornecida.
- SSH com `PasswordAuthentication no`, `PermitRootLogin prohibit-password` e `PubkeyAuthentication yes`.
- Atualizações automáticas de segurança (`unattended-upgrades`).
