# Checklist manual: US-021 - Sincronizar notebook/celular com Nextcloud

Objetivo: confirmar criação de usuários e operação do cliente de sincronização desktop/mobile.

## Pré-requisitos
- `.env` preenchido com `NEXTCLOUD_*` (senhas fortes) e `HOMELAB_DOMAIN` resolvendo para o host.
- Stack `infra` ativa (`make up-infra`) e portas 80/443 disponíveis.
- Pacote `nextcloud-desktop` ou `nextcloudcmd` instalado no notebook usado para o teste.

## Passo a passo sugerido (E2E manual)
1. **Subir stack core + criar usuários**
   ```bash
   # a partir da raiz do repo
   ./core/nextcloud_bootstrap.sh
   ```
   - Confirma que containers `nextcloud`, `nextcloud-web`, `nextcloud-cron`, `postgres`, `redis` estão em `running`.
   - Garante criação do admin (`NEXTCLOUD_ADMIN_USER`) e de um usuário de uso (`NEXTCLOUD_USER`).

2. **Acessar web UI e confirmar login**
   - Abrir `https://nextcloud.<HOMELAB_DOMAIN>`.
   - Fazer login com o usuário de uso (`NEXTCLOUD_USER`).
   - Criar uma pasta de teste chamada `sync-e2e`.

3. **Configurar cliente desktop**
   - No notebook, abrir o cliente Nextcloud Desktop.
   - Inserir URL `https://nextcloud.<HOMELAB_DOMAIN>` e credenciais do usuário de uso.
   - Selecionar diretório local dedicado (ex: `~/Nextcloud-e2e`).
   - Verificar que a pasta `sync-e2e` apareceu localmente após sincronização inicial.

4. **Validar upload→download**
   - Criar um arquivo `from-desktop.txt` dentro de `sync-e2e` no notebook com algum conteúdo.
   - Aguardar sincronização (ícone verde no cliente).
   - Conferir via web UI que o arquivo existe e pode ser baixado/aberto.

5. **Validar download→upload (celular opcional)**
   - Pelo web UI, enviar arquivo `from-web.txt` para `sync-e2e`.
   - Verificar que o cliente desktop puxou o arquivo automaticamente.
   - Se houver app mobile configurado, abrir e conferir que ambos os arquivos aparecem e conseguem ser abertos.

6. **Checklist final**
   - [ ] Admin e usuário criados.
   - [ ] Login web funcionando via Traefik/HTTPS.
   - [ ] Cliente desktop sincroniza uploads e downloads sem conflitos.
   - [ ] (Opcional) App mobile vê os mesmos arquivos.

## Observações
- O script `core/nextcloud_bootstrap.sh` também tenta usar `nextcloudcmd` (CLI) para sincronização básica caso esteja instalado, gerando um arquivo `sync-check.txt` na pasta local informada em `NEXTCLOUD_SYNC_DIR`.
- Após os testes, use `docker compose -f core/docker-compose.yml down` se precisar liberar recursos.
