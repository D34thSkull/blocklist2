# blocklist2

Automatiza a criação diária de uma blocklist compatível com AdGuard, a partir de fontes configuráveis, com deduplicação, otimização de subdomínios e whitelist manual.

## Ficheiros

- `blocklist.py` — descarrega e processa as fontes, aplica a whitelist e gera o resultado.
- `sources.txt` — URLs das listas de origem, uma por linha.
- `whitelist.txt` — domínios que não devem ser bloqueados, um por linha. Cada entrada também protege os respetivos subdomínios.
- `blocklist_optimized.txt` — ficheiro gerado; não é versionado.
- `systemd/` — serviço e temporizador para execução diária às 00:00.

## Utilização manual

Requer Python 3.8 ou superior e não necessita de dependências externas.

```bash
python3 blocklist.py
```

O script grava `blocklist_optimized.txt` junto aos ficheiros do projeto. Se todas as fontes falharem, termina sem substituir uma saída existente.

### Gerir a whitelist

Edita `whitelist.txt`, adicionando um domínio por linha. Linhas vazias e linhas que começam por `#` ou `!` são ignoradas. Por exemplo:

```text
exemplo.pt
servico-local.lan
```

Uma entrada como `exemplo.pt` exclui `exemplo.pt` e qualquer subdomínio (`www.exemplo.pt`, por exemplo). O script só aceita regras simples de domínio; filtros AdGuard mais complexos são ignorados.

### Gerir as fontes

Edita `sources.txt` e adiciona ou remove URLs HTTP/HTTPS, uma por linha. O script aceita entradas de ficheiros hosts, domínios simples e regras Adblock básicas no formato `||dominio.example^`.

## Instalação do temporizador systemd

Os ficheiros de serviço usam `/opt/blocklist-auto` como caminho de instalação. Copia o projeto para esse diretório e instala as unidades:

```bash
sudo mkdir -p /opt/blocklist-auto
sudo cp -r . /opt/blocklist-auto/
sudo cp /opt/blocklist-auto/systemd/blocklist-auto.service /etc/systemd/system/
sudo cp /opt/blocklist-auto/systemd/blocklist-auto.timer /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable --now blocklist-auto.timer
```

O serviço está configurado como `root`, seguindo o exemplo fornecido. Para um ambiente mais restrito, recomenda-se criar um utilizador dedicado, atribuir-lhe permissões de escrita em `/opt/blocklist-auto` e alterar `User=` na unidade.

Verifica o agendamento e executa uma atualização de teste:

```bash
systemctl list-timers --all | grep blocklist-auto
sudo systemctl start blocklist-auto.service
sudo journalctl -u blocklist-auto.service -n 50 --no-pager
```

A hora depende do fuso horário configurado no servidor. O temporizador é persistente: se o servidor estiver desligado à meia-noite, a execução em falta será iniciada quando voltar.
