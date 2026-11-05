# blocklist2

Automatiza a criação de uma blocklist compatível com AdGuard a partir de fontes configuráveis, com deduplicação, otimização de subdomínios e whitelist manual. O GitHub Actions pode gerar e publicar o ficheiro diariamente.

## Ficheiros

- `blocklist.py` — descarrega e processa as fontes, aplica a whitelist e gera o resultado.
- `sources.txt` — URLs das listas de origem, uma por linha.
- `whitelist.txt` — domínios que não devem ser bloqueados, um por linha. Cada entrada também protege os respetivos subdomínios.
- `blocklist_optimized.txt` — ficheiro gerado e versionado automaticamente pelo workflow.
- `.github/workflows/update-blocklist.yml` — workflow diário do GitHub Actions.
- `systemd/` — alternativa para execução diária num servidor Linux.

## Utilização manual

Requer Python 3.8 ou superior e não necessita de dependências externas.

```bash
python3 blocklist.py
