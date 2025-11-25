# Bootstrap do repositório homelab-infra (US-041)

Automação mínima para criar o repositório `homelab-infra` no Gitea interno e publicar o código já existente.

## Pré-requisitos
- Stack de infra + git rodando (`make up-infra` + `docker compose -f apps/docker-compose.git.yml up -d`).
- `.env` preenchido com `HOMELAB_DOMAIN`, `GITEA_ADMIN_USER`, `GITEA_ADMIN_PASSWORD` e `GITEA_SECRET_KEY`.
- Árvore git limpa (nenhum arquivo pendente de commit); o script aborta caso detecte sujeira.
- Git e curl disponíveis no host de gestão.

## Uso
```bash
./apps/git/bootstrap_repo.sh
```
O script:
1) Gera token de API temporário para o admin.
2) Cria o repositório privado `homelab-infra` (padrão) com branch principal `main`.
3) Configura o remote `gitea` (pode ser alterado via `GITEA_REMOTE_NAME`).
4) Faz push da HEAD atual para a branch default (`GITEA_DEFAULT_BRANCH`, padrão `main`).

URLs e credenciais são montadas com base em:
- `HOMELAB_DOMAIN`: define `git.<domínio>` para a chamada da API.
- `TRAEFIK_HTTPS_PORT`: porta pública exposta pelo Traefik (default 443).

## Validação manual
Após a execução:
```bash
git remote -v           # deve mostrar remote gitea apontando para git.<domínio>
git ls-remote gitea     # lista refs e confirma autenticação
```

## Notas
- Para branch principal diferente, exporte `GITEA_DEFAULT_BRANCH=my-branch` antes de rodar.
- O remote é atualizado se já existir; isso evita duplicar a configuração em rodadas subsequentes.
- O repositório permanece privado; para torná-lo público, ajuste posteriormente via UI do Gitea.
