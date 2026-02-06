# PRD: Mini-App Web — Automacao de Envio de Boletos para FIDCs

## Metadata
- **ID**: PRD-2026-001
- **Versao**: 1.1
- **Status**: Aprovado (G1)
- **Data**: 2026-02-06
- **Autor**: Planner AI
- **Aprovador**: [Stakeholder JJ]

---

## 1. Contexto & Problema

### 1.1 Background

A JJ opera com antecipacao de recebiveis atraves de 4 FIDCs parceiras (Capital RS, Novax, Credvale e Squid). Embora os boletos sejam gerados pelas FIDCs, o envio final ao cliente e realizado pela JJ para manter o relacionamento comercial e o controle operacional.

Atualmente, esse processo e executado por um **sistema desktop** (Python/Tkinter empacotado em .exe ~36MB) que:
- Recebe boletos PDF em pasta local
- Extrai dados via regex especifico por FIDC
- Valida em 5 camadas cruzando com XMLs de Nota Fiscal Eletronica (NFe)
- Agrupa boletos por cliente e envia via Microsoft Outlook (COM/pywin32)
- Gera relatorios de auditoria em TXT e JSON

O sistema legado esta documentado em 7 arquivos na pasta `docs/legacy_mintlify/`.

### 1.2 Problema

O sistema atual apresenta dividas tecnicas criticas que limitam a operacao:

1. **Caixa preta operacional**: operadora depende de .exe sem visibilidade interna, qualquer ajuste requer desenvolvedor
2. **Etapas manuais excessivas**: split de PDF via site publico (iLovePDF — risco LGPD), criacao manual de pastas no servidor, limpeza manual de XMLs residuais
3. **MODO_PREVIEW travado em True** desde a fase de testes — envio semi-manual sem opcao de alternancia na interface
4. **Zero visibilidade em tempo real**: sem dashboard, metricas ou historico consultavel via interface
5. **Fragilidade de manutencao**: regex inline, duplicacao de codigo entre ambiente dev e build_server, dois virtual environments

### 1.3 Hipotese de Valor

Migrar para uma aplicacao Web interna que replique 100% das regras de negocio do sistema legado, adicionando:
- **Transparencia operacional**: dashboard com status em tempo real e historico consultavel
- **Eliminacao de etapas manuais**: split de PDF automatico, gestao de operacoes integrada
- **Flexibilidade**: toggle preview/automatico na interface, configuracao de FIDCs editavel
- **Acessibilidade**: qualquer maquina com navegador na rede local pode operar

**Metrica de sucesso**: Taxa de sucesso de envio >= 98% com reducao de 50% no tempo operacional por lote de boletos.

---

## 2. Objetivos & Escopo

### 2.1 Objetivos

- [ ] Replicar integralmente as regras de negocio, validacoes de seguranca (5 camadas) e particularidades de cada FIDC do sistema legado
- [ ] Substituir todas as etapas manuais eliminaveis (split de PDF, limpeza de pastas) por automacao na interface Web
- [ ] Prover dashboard operacional com status em tempo real e historico de operacoes
- [ ] Manter envio de e-mails via Microsoft Outlook (pywin32) conforme fluxo atual
- [ ] Permitir alternancia interativa entre modo preview e envio automatico
- [ ] Suportar 1-3 operadores simultaneos sem hierarquia de permissao

### 2.2 Nao-Escopo (Out of Scope)

- Integracao com APIs dos portais das FIDCs (download automatico de boletos)
- Integracao com ERP Viasoft (extracao automatica de XMLs)
- Dashboard de metricas avancadas (Grafana/Prometheus)
- Gestao financeira (controle de antecipacoes, taxas, saldos)
- Notificacoes push/WhatsApp ao cliente
- Reenvio automatico de boletos nao confirmados
- Niveis de permissao (admin vs operador)
- Deploy em nuvem (sera servidor local)

### 2.3 Premissas

- O backend rodara em maquina **Windows** com Microsoft Outlook instalado e configurado com a conta `cobranca@jotajota.net.br` (ou `cobranca@jj.net.br` — a confirmar)
- Os XMLs de NFe continuarao sendo exportados manualmente do Viasoft e carregados via interface Web
- Os boletos PDF continuarao sendo baixados manualmente dos portais das FIDCs e carregados via interface Web
- Os regex e logica de extracao documentados nos arquivos Mintlify sao a **fonte de verdade absoluta**
- O operador tera acesso a navegador moderno (Chrome/Edge) na rede local
- A imagem de assinatura de e-mail (`assinatura.jpg`) sera mantida no formato atual

### 2.4 Restricoes

- **Design System**: Seguir estritamente o padrao Megatela v3.0:
  - Tipografia UI: `DM Sans` (400, 500, 700)
  - Tipografia Dados: `Halenoir Compact` (500, 600, 700) | Fallback: `Barlow Condensed`
  - Numeracao: Formato pt-BR (`R$ #.###,##`, `+##,#%`)
  - Brand Accent: `#F37021` (Laranja Megatela)
  - Semantica: Positive `#059669` | Negative `#DC2626` | Warning `#D97706`
  - Charts: 1. Accent, 2. Verde, 3. Azul (`#3B82F6`), 4. Roxo (`#8B5CF6`)
  - Radius: Buttons/Inputs `8-10px`; Cards `14-16px`; Modais `20px`
  - Grid: Base 8px (Tailwind spacing)
  - Componentes: shadcn/ui (base) + Lucide React (icones)
  - Graficos: Recharts
- **Stack obrigatoria**: React/Next.js (Front), Python/FastAPI (Back), PostgreSQL (DB)
- **Outlook obrigatorio**: Envio de e-mails via pywin32 COM automation (Microsoft Outlook desktop)
- **Backend Windows**: Obrigatorio por dependencia de pywin32/Outlook — roda diretamente no HOST Windows via venv (NAO containerizado)
- **Arquitetura Hibrida (Host + Docker)**: Backend FastAPI roda no Host Windows (acesso COM ao Outlook). PostgreSQL roda em container Docker. Frontend pode rodar no Host ou Docker.
- **Desenvolvimento local**: Fase inicial no computador do desenvolvedor (Windows), deploy futuro em servidor local da empresa

---

## 3. Requisitos Funcionais

### RF-001: Upload e Split Automatico de Boletos PDF
**Descricao**: O sistema deve permitir upload de um ou mais arquivos PDF (boletos). Se um PDF contiver multiplas paginas, o sistema deve separa-lo automaticamente em arquivos individuais (1 pagina = 1 boleto), eliminando a dependencia do site iLovePDF.
**Prioridade**: Must
**Criterios de Aceitacao**:
```gherkin
Feature: Upload e Split de Boletos PDF
  Scenario: Upload de PDF unico com multiplas paginas
    Given o operador esta na tela de nova operacao
    When ele faz upload de um PDF com 15 paginas
    Then o sistema separa automaticamente em 15 PDFs individuais
    And exibe preview visual de cada boleto separado
    And mostra contador "15 boletos detectados"

  Scenario: Upload de multiplos PDFs individuais
    Given o operador esta na tela de nova operacao
    When ele faz upload de 10 arquivos PDF via drag-and-drop
    Then o sistema aceita todos os arquivos
    And exibe preview de cada boleto
    And mostra contador "10 boletos detectados"

  Scenario: Upload de arquivo invalido
    Given o operador esta na tela de nova operacao
    When ele tenta fazer upload de um arquivo .docx
    Then o sistema rejeita o arquivo
    And exibe mensagem "Formato invalido. Apenas arquivos PDF sao aceitos."
```

---

### RF-002: Upload e Parsing de XMLs de NFe
**Descricao**: O sistema deve permitir upload batch de XMLs de Nota Fiscal Eletronica, realizar parsing automatico (replicando `xml_nfe_reader.py`) e exibir resumo dos dados extraidos.
**Prioridade**: Must
**Criterios de Aceitacao**:
```gherkin
Feature: Upload e Parsing de XMLs NFe
  Scenario: Upload batch de XMLs validos
    Given o operador esta na tela de nova operacao
    When ele faz upload de 15 arquivos XML
    Then o sistema faz parsing de cada XML
    And extrai: numero_nota, cnpj, nome, valor_total, emails, duplicatas
    And exibe tabela resumo com dados extraidos
    And mostra contador "15 XMLs carregados"

  Scenario: XML com email invalido
    Given o operador fez upload de XML com email "compras@empresa."
    When o sistema faz parsing
    Then o email e marcado como invalido
    And o sistema exibe aviso "1 email invalido filtrado: compras@empresa."

  Scenario: XML corrompido
    Given o operador fez upload de XML com estrutura invalida
    When o sistema tenta fazer parsing
    Then o XML e rejeitado
    And exibe mensagem "XML invalido: [nome_arquivo] - estrutura nao reconhecida"
```

---

### RF-003: Selecao de FIDC
**Descricao**: O sistema deve permitir selecao da FIDC para a operacao corrente. A selecao determina: extrator de dados, palavras-chave de deteccao, emails CC e informacoes do beneficiario no corpo do e-mail.
**Prioridade**: Must
**Criterios de Aceitacao**:
```gherkin
Feature: Selecao de FIDC
  Scenario: Selecionar FIDC Capital RS
    Given o operador esta na tela de nova operacao
    When ele seleciona "Capital RS"
    Then o sistema carrega configuracao da Capital RS
    And exibe cor identificadora #0e639c
    And configura CC para ["adm@jotajota.net.br"]
    And configura beneficiario "CAPITAL RS FIDC NP MULTISSETORIAL"

  Scenario: Selecionar FIDC Novax
    Given o operador esta na tela de nova operacao
    When ele seleciona "Novax"
    Then o sistema configura CC para ["adm@jotajota.net.br", "controladoria@novaxfidc.com.br"]
    And configura beneficiario "Novax Fundo de Investimento em Direitos Creditocios"

  Scenario: Selecionar FIDC Credvale
    Given o operador esta na tela de nova operacao
    When ele seleciona "Credvale"
    Then o sistema configura CC para ["adm@jotajota.net.br", "nichole@credvalefidc.com.br"]

  Scenario: Selecionar FIDC Squid
    Given o operador esta na tela de nova operacao
    When ele seleciona "Squid"
    Then o sistema configura CC para ["adm@jotajota.net.br"]
```

---

### RF-004: Extracao de Dados do Boleto PDF (Motor de Extratores)
**Descricao**: O sistema deve extrair dados de cada boleto PDF usando extratores especificos por FIDC, replicando integralmente a logica documentada em `extratores-por-fidc.mdx`. Dados extraidos: pagador, vencimento, valor, CNPJ/CPF, numero da nota fiscal.
**Prioridade**: Must
**Criterios de Aceitacao**:
```gherkin
Feature: Extracao de Dados por FIDC
  Scenario: Extrair dados de boleto Capital RS (formato DANFE)
    Given um boleto PDF da Capital RS com secao "DESTINATARIO/REMETENTE"
    When o sistema executa o extrator CAPITAL
    Then extrai pagador da linha apos "NOME/RAZAO SOCIAL"
    And extrai vencimento no formato DD-MM
    And extrai valor da secao FATURA (prioritario) ou Valor Documento (fallback)
    And extrai CNPJ do campo "CNPJ/CPF" apos DESTINATARIO
    And extrai numero da nota de "NUMERO DA NOTA" ou "Numero do Documento"

  Scenario: Extrair dados de boleto Novax (formato boleto tradicional)
    Given um boleto PDF da Novax com campo "Pagador:" em texto compacto
    When o sistema executa o extrator NOVAX
    Then extrai pagador do texto compacto entre "Pagador:" e "CNPJ"
    And extrai vencimento apos campo "VENCIMENTO"
    And extrai valor de "Valor Documento" ou fallback "data + valor"
    And extrai CNPJ apos "PAGADOR"
    And extrai numero da nota de "Numero do Documento" (sem sufixo /001)

  Scenario: Extrair dados de boleto Credvale (campo "Pagador" exato)
    Given um boleto PDF da Credvale com linha exata "Pagador"
    When o sistema executa o extrator CREDVALE
    Then extrai pagador da linha seguinte a "Pagador" (exato, sem dois pontos)
    And valida que a linha nao e codigo de barras
    And trata formato "- EPP -" antes do CNPJ

  Scenario: Extrair dados de boleto Squid (formato DANFE)
    Given um boleto PDF da Squid com secao FATURA
    When o sistema executa o extrator SQUID
    Then extrai valor da secao FATURA sem concatenar dia do vencimento (bug v2.0 corrigido)
    And suporta filename com prefixo "3-" para extracao de numero NF

  Scenario: FIDC nao detectada
    Given um boleto PDF sem palavras-chave de nenhuma FIDC
    When o sistema tenta detectar a FIDC
    Then retorna "DESCONHECIDO"
    And o boleto e marcado como "requer intervencao manual"
```

---

### RF-005: Renomeacao Automatica de Boletos
**Descricao**: Apos extracao de dados, o sistema deve renomear cada boleto no formato padrao: `{PAGADOR} - NF {NUMERO_NOTA} - {DD-MM} - R$ {VALOR}.pdf`. O numero da nota extraido do campo "Numero do Documento" do PDF tem prioridade sobre matching por CNPJ/valor no XML.
**Prioridade**: Must
**Criterios de Aceitacao**:
```gherkin
Feature: Renomeacao de Boletos
  Scenario: Renomeacao com dados completos
    Given um boleto com pagador "AREAIS DO LESTE SPE LTDA", NF 310227, vencimento 13/01, valor 2833.34
    When o sistema renomeia o boleto
    Then o novo nome e "AREAIS DO LESTE SPE LTDA - NF 310227 - 13-01 - R$ 2.833,34.pdf"

  Scenario: Renomeacao sem vencimento detectado
    Given um boleto cujo vencimento nao foi extraido
    When o sistema renomeia o boleto
    Then usa "A definir" no campo de vencimento

  Scenario: Divergencia entre Numero do Documento e matching XML
    Given um boleto com Numero do Documento "310227" mas matching XML retorna "310228"
    When o sistema renomeia
    Then prioriza "310227" (Numero do Documento)
    And registra alerta de divergencia no log
```

---

### RF-006: Validacao em 5 Camadas
**Descricao**: Cada boleto deve passar por validacao rigorosa em 5 camadas antes do envio. Replicar integralmente a logica do `EnvioBoleto.py` documentada em `estrutura-do-projeto.mdx` e `fluxo-operacional-completo.mdx`.
**Prioridade**: Must
**Criterios de Aceitacao**:
```gherkin
Feature: Validacao em 5 Camadas
  Scenario: Boleto aprovado em todas as camadas
    Given um boleto com NF 310227, CNPJ 54737141000110, valor 2833.34
    And um XML correspondente com mesmos dados e emails validos
    When o sistema executa validacao
    Then Camada 1 (XML): aprovado - "XML encontrado (310227)"
    And Camada 2 (CNPJ): aprovado - "Match perfeito: 54737141000110"
    And Camada 3 (Nome): aprovado - "Similaridade 100%"
    And Camada 4 (Valor): aprovado - "Diferenca R$ 0,00"
    And Camada 5 (Email): aprovado - "2 email(s) valido(s)"
    And status final: APROVADO

  Scenario: Boleto rejeitado por CNPJ divergente
    Given um boleto com CNPJ "12345678000190"
    And um XML com CNPJ "98765432000110"
    When o sistema executa validacao
    Then Camada 2 (CNPJ): REJEITADO - "CNPJ divergente!"
    And status final: REJEITADO
    And boleto e movido para lista de erros

  Scenario: Boleto com nome de similaridade baixa (aviso sem bloqueio)
    Given um boleto com pagador "EMPRESA ABC COMERCIO LTDA"
    And um XML com nome "EMPRESA ABC LTDA ME"
    And similaridade calculada = 72%
    When o sistema executa validacao da Camada 3
    Then registra aviso "Similaridade baixa: 72%"
    And NAO bloqueia o envio (continua validacao)

  Scenario: Boleto rejeitado por valor divergente
    Given um boleto com valor R$ 1.234,56
    And um XML com valor R$ 1.234,50
    When o sistema executa validacao da Camada 4
    Then Camada 4: REJEITADO - "Diferenca R$ 0,06 (tolerancia: R$ 0,00)"
    And status final: REJEITADO

  Scenario: Boleto rejeitado por ausencia de email valido
    Given um XML sem campo de email ou com emails truncados
    When o sistema executa validacao da Camada 5
    Then Camada 5: REJEITADO - "Nenhum email valido encontrado"
    And status final: REJEITADO

  Scenario: Validacao de valor com duplicata (parcela)
    Given um boleto com vencimento 13/01/2026 e valor 2833.34
    And um XML com duplicata que tem mesmo vencimento e valor
    When o sistema executa validacao da Camada 4
    Then prioriza valor da duplicata (nao valor total da NF)
    And Camada 4: aprovado
```

---

### RF-007: Agrupamento de Boletos por Cliente
**Descricao**: Boletos do mesmo cliente (mesmo email de destino) devem ser agrupados em um unico e-mail, com todos os boletos e XMLs correspondentes como anexos.
**Prioridade**: Must
**Criterios de Aceitacao**:
```gherkin
Feature: Agrupamento por Cliente
  Scenario: Multiplos boletos para mesmo cliente
    Given 3 boletos aprovados para "Tempoville" com email "financeiro@tempoville.com.br"
    When o sistema agrupa para envio
    Then cria 1 unico e-mail
    And anexa os 3 boletos PDF
    And anexa o(s) XML(s) correspondente(s)
    And o assunto lista todas as NFs: "Boleto e Nota Fiscal (318976, 318977, 318978)"

  Scenario: Boletos de clientes diferentes
    Given 2 boletos para "Cliente A" e 3 boletos para "Cliente B"
    When o sistema agrupa para envio
    Then cria 2 e-mails separados (1 por cliente)
```

---

### RF-008: Composicao e Envio de E-mail via Outlook
**Descricao**: O sistema deve criar e-mails no Microsoft Outlook via pywin32 COM automation, replicando exatamente o formato, corpo, anexos e regras de CC do sistema legado. Deve suportar modo preview (abre rascunho no Outlook) e modo envio automatico, com toggle interativo na interface.
**Prioridade**: Must
**Criterios de Aceitacao**:
```gherkin
Feature: Envio de E-mail via Outlook
  Scenario: Envio em modo preview
    Given o toggle esta em "Modo Preview"
    And existem 5 e-mails agrupados prontos para envio
    When o operador clica em "Enviar Boletos"
    Then o sistema abre 5 rascunhos no Outlook (Display)
    And o operador confere e envia manualmente cada um

  Scenario: Envio em modo automatico
    Given o toggle esta em "Envio Automatico"
    And existem 5 e-mails agrupados prontos para envio
    When o operador clica em "Enviar Boletos"
    Then o popup de confirmacao exibe "Deseja enviar 5 emails automaticamente?"
    And apos confirmacao, o sistema envia todos via Outlook (Send)
    And exibe progresso em tempo real

  Scenario: Estrutura do e-mail gerado
    Given um grupo de boletos aprovados para cliente "AREAIS DO LESTE SPE LTDA"
    And FIDC selecionada = Novax
    When o sistema compoe o e-mail
    Then remetente = "cobranca@jotajota.net.br"
    And destinatarios = emails do XML (maximo 2)
    And CC = ["adm@jotajota.net.br", "controladoria@novaxfidc.com.br"]
    And assunto = "Boleto e Nota Fiscal (310227, 310228)"
    And corpo contem saudacao, nome do cliente, lista de NFs com valor/vencimento, nome completo + CNPJ da FIDC beneficiaria
    And anexos = boletos PDF + XMLs das NFs
    And assinatura = imagem assinatura.jpg

  Scenario: Toggle de modo de envio
    Given o operador esta na tela principal
    When ele alterna o toggle de "Modo Preview" para "Envio Automatico"
    Then o sistema exibe alerta de confirmacao: "Atencao: o envio sera automatico. Confirma?"
    And apos confirmacao, o toggle muda visualmente para indicar modo automatico
    And a cor do botao "Enviar" muda para indicar modo ativo

  Scenario: Regra de maximo 2 emails por cliente
    Given um XML com 3 emails cadastrados
    When o sistema extrai emails
    Then usa apenas os 2 primeiros emails validos
    And registra no log que o 3o email foi descartado

  Scenario: Descarte silencioso do 2o email longo
    Given um XML com 2 emails, sendo o 2o com mais de 100 caracteres
    When o sistema valida os emails
    Then descarta o 2o email
    And registra aviso no log: "Email descartado (muito longo): [primeiros 50 chars]..."
    And envia apenas para o 1o email
```

---

### RF-009: Dashboard Operacional
**Descricao**: Tela principal com visao consolidada do status das operacoes, contadores em tempo real e acesso rapido as funcionalidades.
**Prioridade**: Must
**Criterios de Aceitacao**:
```gherkin
Feature: Dashboard Operacional
  Scenario: Visualizar resumo da operacao em andamento
    Given uma operacao com 15 boletos sendo processada
    When o operador visualiza o dashboard
    Then exibe KPIs: Total Boletos (15), Aprovados (12), Rejeitados (3), Taxa Sucesso (80%)
    And exibe barra de progresso do processamento
    And exibe lista de boletos com status individual (aprovado/rejeitado/pendente)

  Scenario: Visualizar historico de operacoes
    Given o operador acessa a secao "Historico"
    When visualiza a lista
    Then exibe operacoes anteriores com: data, FIDC, quantidade, taxa de sucesso
    And permite filtrar por FIDC, data, status
    And permite buscar por nome de cliente ou numero de NF
```

---

### RF-010: Gestao de Operacoes
**Descricao**: Cada lote de boletos processado constitui uma "Operacao" vinculada a uma FIDC. O sistema deve gerenciar o ciclo de vida completo da operacao.
**Prioridade**: Must
**Criterios de Aceitacao**:
```gherkin
Feature: Gestao de Operacoes
  Scenario: Criar nova operacao
    Given o operador clica em "Nova Operacao"
    When preenche: FIDC = "Novax", Numero = "1234"
    And faz upload de boletos e XMLs
    Then o sistema cria uma operacao com status "Em Processamento"
    And vincula todos os boletos e XMLs a esta operacao

  Scenario: Finalizar operacao
    Given uma operacao com todos os boletos enviados
    When o operador clica em "Finalizar Operacao"
    Then o sistema gera relatorio final de auditoria
    And arquiva todos os boletos e XMLs
    And marca operacao como "Concluida"
    And limpa automaticamente arquivos temporarios

  Scenario: Reprocessar boletos rejeitados
    Given uma operacao com 3 boletos rejeitados
    When o operador corrige os XMLs e clica em "Reprocessar Rejeitados"
    Then o sistema executa novamente a validacao em 5 camadas apenas nos rejeitados
    And atualiza status individual e contadores
```

---

### RF-011: Auditoria e Relatorios
**Descricao**: O sistema deve gerar relatorios de auditoria identicos ao formato do sistema legado (TXT para aprovados, TXT para rejeitados, JSON estruturado, log de erros criticos), com adicao de persistencia em banco de dados para consulta via interface.
**Prioridade**: Must
**Criterios de Aceitacao**:
```gherkin
Feature: Auditoria e Relatorios
  Scenario: Gerar relatorio de boletos aprovados
    Given uma operacao finalizada com 12 boletos aprovados
    When o sistema gera relatorio
    Then cria arquivo TXT com formato identico ao legado:
      | Campo | Exemplo |
      | Numeracao | [001/012] |
      | Nome arquivo | AREAIS DO LESTE SPE LTDA - NF 310227... |
      | Timestamp | 06/02/2026 14:30:22 |
      | Status | ENVIADO COM SUCESSO |
      | 5 camadas | Detalhamento de cada validacao |
      | Dados XML | numero_nota, nome, cnpj, valor, emails |
      | Email enviado | Para, CC, Anexos |

  Scenario: Gerar relatorio JSON estruturado
    Given uma operacao finalizada
    When o sistema gera relatorio JSON
    Then o formato segue o schema do legado:
      | Campo | Tipo |
      | execucao_id | string (YYYYMMDD_HHMMSS) |
      | resumo.total_boletos | integer |
      | resumo.aprovados | integer |
      | resumo.rejeitados | integer |
      | resumo.taxa_sucesso | float |
      | boletos[] | array de objetos com validacoes |

  Scenario: Consultar auditoria via interface
    Given o operador acessa "Auditoria" no menu
    When busca por NF "310227"
    Then exibe todos os registros com essa NF
    And mostra detalhes de validacao, destinatarios e timestamp
    And permite download do relatorio em TXT ou JSON
```

---

### RF-012: Configuracao de FIDCs
**Descricao**: Interface para visualizar e editar configuracoes das FIDCs (nome, nome completo, CNPJ, emails CC, palavras-chave de deteccao, cor). Extensivel para adicionar 5a FIDC futura.
**Prioridade**: Should
**Criterios de Aceitacao**:
```gherkin
Feature: Configuracao de FIDCs
  Scenario: Editar emails CC de uma FIDC
    Given o operador acessa configuracoes da Novax
    When altera o email CC de "controladoria@novaxfidc.com.br" para "novo@novaxfidc.com.br"
    And salva
    Then as proximas operacoes Novax usam o novo email CC
    And o historico de alteracoes e registrado

  Scenario: Adicionar nova FIDC
    Given o operador acessa "Adicionar FIDC"
    When preenche: nome = "NOVA_FIDC", CNPJ = "XX.XXX.XXX/XXXX-XX", palavras-chave = ["NOVA FIDC"]
    And salva
    Then a nova FIDC aparece como opcao na tela de operacoes
    And requer cadastro de extrator customizado pelo desenvolvedor
```

---

### RF-013: Autenticacao Basica
**Descricao**: Login simples para identificacao do operador (1-3 usuarios), sem hierarquia de permissoes. Todos os usuarios tem acesso total a todas as funcionalidades.
**Prioridade**: Must
**Criterios de Aceitacao**:
```gherkin
Feature: Autenticacao Basica
  Scenario: Login de operador
    Given o operador acessa o sistema via navegador
    When informa usuario e senha
    Then o sistema autentica e redireciona ao dashboard
    And registra o nome do operador nas auditorias subsequentes

  Scenario: Sessao expirada
    Given o operador esta inativo por 8 horas
    When tenta realizar uma acao
    Then o sistema redireciona ao login
    And exibe mensagem "Sessao expirada. Faca login novamente."
```

---

### RF-014: Deteccao de Juros/Multa
**Descricao**: Quando o valor do boleto for maior que o valor da NF, o sistema deve detectar e registrar como juros/multa, usando o valor original da NF para nomenclatura.
**Prioridade**: Should
**Criterios de Aceitacao**:
```gherkin
Feature: Deteccao de Juros/Multa
  Scenario: Boleto com juros detectado
    Given um boleto com valor R$ 1.050,00
    And um XML com valor NF R$ 1.000,00
    When o sistema compara valores
    Then detecta juros de R$ 50,00
    And registra alerta informativo no log
    And usa valor da NF (R$ 1.000,00) no nome do arquivo
    And NAO bloqueia o envio
```

---

### RF-015: Ordenacao Cronologica de Anexos
**Descricao**: Quando multiplos boletos forem anexados ao mesmo e-mail, devem ser ordenados por data de vencimento (mais proximo primeiro).
**Prioridade**: Should
**Criterios de Aceitacao**:
```gherkin
Feature: Ordenacao de Anexos
  Scenario: 3 boletos com vencimentos diferentes
    Given boletos com vencimentos 27/01, 13/01 e 20/01
    When o sistema prepara os anexos do e-mail
    Then ordena: 13/01, 20/01, 27/01
    And XMLs seguem apos os boletos ordenados
```

---

## 4. Requisitos Nao-Funcionais

| ID | Categoria | Requisito | Metrica |
|----|-----------|-----------|---------|
| RNF-001 | Performance | Extracao de dados de 1 boleto PDF | < 3s por boleto |
| RNF-002 | Performance | Split de PDF com 50 paginas | < 10s |
| RNF-003 | Performance | Validacao completa (5 camadas) de 1 boleto | < 1s |
| RNF-004 | Performance | Carregamento do dashboard | < 2s (first contentful paint) |
| RNF-005 | Disponibilidade | Uptime do sistema na rede local | 99% durante horario comercial |
| RNF-006 | Seguranca | Dados de boletos e XMLs | Nunca trafegam para servicos externos (tudo local) |
| RNF-007 | Seguranca | Senhas de usuarios | Armazenadas com hash bcrypt |
| RNF-008 | Seguranca | Sessoes | JWT com expiracao de 8h |
| RNF-009 | Seguranca | Input validation | Todos os uploads validados (tipo, tamanho, conteudo) |
| RNF-010 | Compatibilidade | Navegadores | Chrome 90+, Edge 90+ |
| RNF-011 | Dados | Formato numerico | pt-BR em toda a interface (R$ #.###,##) |
| RNF-012 | Rastreabilidade | Todas as acoes de envio | Registradas com timestamp, operador, detalhes de validacao |
| RNF-013 | Armazenamento | Retencao de auditorias | Minimo 2 anos no banco de dados |
| RNF-014 | Usabilidade | Responsividade | Desktop-first (1280px+), funcional em 1024px |

---

## 5. Arquitetura Tecnica

### 5.1 Visao Geral — Arquitetura Hibrida (Host + Docker)

> **DECISAO ARQUITETURAL CRITICA**: O Backend FastAPI **NAO pode rodar em container Docker**
> porque depende de `pywin32` para automacao COM do Microsoft Outlook instalado no Host Windows.
> Containers Linux nao suportam COM automation, e containers Windows nao tem acesso a instancia
> do Outlook do Host. Portanto, adota-se uma **Arquitetura Hibrida**:
> - **HOST Windows (venv)**: Backend FastAPI + Frontend Next.js
> - **Docker (container)**: Apenas PostgreSQL

```
┌──────────────────────────────────────────────────────────────────────────┐
│                     MAQUINA WINDOWS (Host)                               │
│                                                                          │
│  ┌─────────────┐       ┌──────────────────┐                              │
│  │  Browser     │──────▶│  Next.js (SSR)   │    ◀── Processo Host        │
│  │  (Operador)  │◀──────│  :3000           │        (npm run start)      │
│  └─────────────┘       └────────┬─────────┘                              │
│                                 │ HTTP/REST                              │
│                        ┌────────▼─────────┐        ┌──────────────────┐  │
│                        │  FastAPI (Python) │        │ Microsoft Outlook│  │
│                        │  :8000            │──COM──▶│ (Desktop App)    │  │
│                        │                   │pywin32 │ cobranca@jj...   │  │
│                        │  ◀── Processo Host│        └──────────────────┘  │
│                        │  (venv + uvicorn) │                              │
│                        │                   │        ┌──────────────────┐  │
│                        │  ┌─────────────┐  │        │ Filesystem Host  │  │
│                        │  │ Extractors  │  │───────▶│ (uploads, audits,│  │
│                        │  │ (por FIDC)  │  │        │  assinatura.jpg) │  │
│                        │  ├─────────────┤  │        └──────────────────┘  │
│                        │  │ Validators  │  │                              │
│                        │  ├─────────────┤  │   ┌─────────────────────┐    │
│                        │  │ PDF Engine  │  │   │  DOCKER CONTAINER   │    │
│                        │  │ (pdfplumber │  │   │  ┌───────────────┐  │    │
│                        │  │  + PyPDF2)  │  │   │  │  PostgreSQL   │  │    │
│                        │  ├─────────────┤  │──▶│  │  :5432        │  │    │
│                        │  │ XML Parser  │  │   │  └───────────────┘  │    │
│                        │  └─────────────┘  │   │  (docker-compose)   │    │
│                        └──────────────────┘   └─────────────────────┘    │
└──────────────────────────────────────────────────────────────────────────┘
```

### 5.1.1 Justificativa da Arquitetura Hibrida

| Componente | Onde roda | Por que |
|------------|-----------|---------|
| **FastAPI (Backend)** | HOST Windows (Python venv) | Requer `pywin32` para automacao COM do Outlook. COM nao funciona em containers (nem Linux nem Windows isolado). |
| **Next.js (Frontend)** | HOST Windows (Node.js) | Simplicidade operacional — roda junto com o backend no mesmo host. Poderia rodar em Docker, mas nao ha ganho. |
| **PostgreSQL (Database)** | Docker container | Isolamento limpo, facil setup/teardown, backup via volume, nao interfere com o Host. Gerenciado por `docker-compose.yml`. |
| **Microsoft Outlook** | HOST Windows (aplicativo desktop) | Ja instalado e configurado com conta `cobranca@jotajota.net.br`. Backend acessa via `win32com.client`. |

### 5.1.2 Comunicacao entre Componentes

```
Browser ──HTTP:3000──▶ Next.js ──HTTP:8000──▶ FastAPI ──COM──▶ Outlook
                                                │
                                                ├──TCP:5432──▶ PostgreSQL (Docker)
                                                │
                                                └──I/O──▶ Filesystem (uploads/)
```

- **Next.js → FastAPI**: HTTP REST (localhost:8000/api/v1)
- **FastAPI → PostgreSQL**: TCP via driver asyncpg (localhost:5432, porta exposta pelo Docker)
- **FastAPI → Outlook**: COM automation via pywin32 (processo local, mesmo usuario Windows)
- **FastAPI → Filesystem**: I/O direto para uploads, auditorias, assinatura

### 5.2 Modelo de Dados

```sql
-- Usuarios (autenticacao basica)
CREATE TABLE usuarios (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    nome VARCHAR(100) NOT NULL,
    email VARCHAR(255) UNIQUE NOT NULL,
    senha_hash VARCHAR(255) NOT NULL,
    ativo BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

-- Configuracao das FIDCs
CREATE TABLE fidcs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    nome VARCHAR(50) UNIQUE NOT NULL,           -- "CAPITAL", "NOVAX", etc.
    nome_completo VARCHAR(255) NOT NULL,
    cnpj VARCHAR(18),
    cc_emails TEXT[] NOT NULL DEFAULT '{}',      -- Array de emails CC
    palavras_chave TEXT[] NOT NULL DEFAULT '{}', -- Para deteccao automatica
    cor VARCHAR(7) DEFAULT '#000000',            -- Hex color
    ativo BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

-- Operacoes (lotes de boletos)
CREATE TABLE operacoes (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    numero VARCHAR(50),                          -- "Operacao 1234"
    fidc_id UUID NOT NULL REFERENCES fidcs(id),
    usuario_id UUID NOT NULL REFERENCES usuarios(id),
    status VARCHAR(20) DEFAULT 'em_processamento',  -- em_processamento, enviando, concluida, cancelada
    modo_envio VARCHAR(20) DEFAULT 'preview',        -- preview, automatico
    total_boletos INTEGER DEFAULT 0,
    total_aprovados INTEGER DEFAULT 0,
    total_rejeitados INTEGER DEFAULT 0,
    taxa_sucesso DECIMAL(5,2) DEFAULT 0,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

-- XMLs de NFe carregados
CREATE TABLE xmls_nfe (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    operacao_id UUID NOT NULL REFERENCES operacoes(id) ON DELETE CASCADE,
    nome_arquivo VARCHAR(500) NOT NULL,
    numero_nota VARCHAR(20) NOT NULL,
    cnpj VARCHAR(14),
    nome_destinatario VARCHAR(255),
    valor_total DECIMAL(12,2),
    emails TEXT[] DEFAULT '{}',
    emails_invalidos TEXT[] DEFAULT '{}',
    duplicatas JSONB DEFAULT '[]',               -- [{numero, vencimento, valor}]
    xml_valido BOOLEAN DEFAULT TRUE,
    dados_raw JSONB,                             -- Dados completos parseados
    created_at TIMESTAMP DEFAULT NOW()
);

-- Boletos processados
CREATE TABLE boletos (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    operacao_id UUID NOT NULL REFERENCES operacoes(id) ON DELETE CASCADE,
    xml_nfe_id UUID REFERENCES xmls_nfe(id),
    arquivo_original VARCHAR(500) NOT NULL,
    arquivo_renomeado VARCHAR(500),
    pagador VARCHAR(255),
    cnpj VARCHAR(14),
    numero_nota VARCHAR(20),
    vencimento VARCHAR(10),                      -- DD-MM ou "A definir"
    vencimento_date DATE,
    valor DECIMAL(12,2),
    valor_formatado VARCHAR(20),                 -- "R$ 2.833,34"
    fidc_detectada VARCHAR(50),
    status VARCHAR(20) DEFAULT 'pendente',       -- pendente, aprovado, rejeitado, enviado, erro
    motivo_rejeicao TEXT,
    validacao_camada1 JSONB,                     -- {resultado, detalhes}
    validacao_camada2 JSONB,
    validacao_camada3 JSONB,
    validacao_camada4 JSONB,
    validacao_camada5 JSONB,
    juros_detectado DECIMAL(12,2),               -- Null se nao detectado
    arquivo_path VARCHAR(1000),                  -- Caminho no filesystem
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

-- Registros de envio (auditoria)
CREATE TABLE envios (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    operacao_id UUID NOT NULL REFERENCES operacoes(id),
    usuario_id UUID NOT NULL REFERENCES usuarios(id),
    email_para TEXT[] NOT NULL,
    email_cc TEXT[] NOT NULL,
    assunto VARCHAR(500) NOT NULL,
    corpo_html TEXT,
    modo VARCHAR(20) NOT NULL,                   -- "preview" ou "automatico"
    status VARCHAR(20) DEFAULT 'criado',         -- criado, enviado, erro
    erro_detalhes TEXT,
    boletos_ids UUID[] NOT NULL,                 -- IDs dos boletos incluidos
    xmls_anexados TEXT[],                        -- Nomes dos XMLs anexados
    timestamp_envio TIMESTAMP,
    created_at TIMESTAMP DEFAULT NOW()
);

-- Log de auditoria geral (append-only)
CREATE TABLE audit_log (
    id BIGSERIAL PRIMARY KEY,
    operacao_id UUID REFERENCES operacoes(id),
    usuario_id UUID REFERENCES usuarios(id),
    acao VARCHAR(100) NOT NULL,                  -- "upload_boleto", "validacao", "envio", etc.
    entidade VARCHAR(50),                        -- "boleto", "xml", "operacao", etc.
    entidade_id UUID,
    detalhes JSONB,
    ip_address VARCHAR(45),
    created_at TIMESTAMP DEFAULT NOW()
);

-- Indices
CREATE INDEX idx_boletos_operacao ON boletos(operacao_id);
CREATE INDEX idx_boletos_status ON boletos(status);
CREATE INDEX idx_boletos_numero_nota ON boletos(numero_nota);
CREATE INDEX idx_xmls_operacao ON xmls_nfe(operacao_id);
CREATE INDEX idx_xmls_numero_nota ON xmls_nfe(numero_nota);
CREATE INDEX idx_envios_operacao ON envios(operacao_id);
CREATE INDEX idx_audit_log_operacao ON audit_log(operacao_id);
CREATE INDEX idx_audit_log_created ON audit_log(created_at);
CREATE INDEX idx_operacoes_status ON operacoes(status);
CREATE INDEX idx_operacoes_fidc ON operacoes(fidc_id);
```

### 5.3 Contratos de API

```yaml
openapi: 3.1.0
info:
  title: Automacao Boletos JJ - API
  version: 1.0.0
  description: API para o Mini-App Web de automacao de envio de boletos para FIDCs

servers:
  - url: http://localhost:8000/api/v1
    description: Desenvolvimento local

paths:
  # === AUTENTICACAO ===
  /auth/login:
    post:
      summary: Login do operador
      tags: [Auth]
      requestBody:
        content:
          application/json:
            schema:
              type: object
              required: [email, senha]
              properties:
                email:
                  type: string
                  format: email
                senha:
                  type: string
      responses:
        '200':
          description: Login bem-sucedido
          content:
            application/json:
              schema:
                type: object
                properties:
                  access_token:
                    type: string
                  token_type:
                    type: string
                    example: bearer
                  usuario:
                    $ref: '#/components/schemas/Usuario'
        '401':
          description: Credenciais invalidas

  # === FIDCS ===
  /fidcs:
    get:
      summary: Listar FIDCs configuradas
      tags: [FIDCs]
      responses:
        '200':
          description: Lista de FIDCs
          content:
            application/json:
              schema:
                type: array
                items:
                  $ref: '#/components/schemas/FIDC'

  /fidcs/{id}:
    put:
      summary: Atualizar configuracao de FIDC
      tags: [FIDCs]
      parameters:
        - name: id
          in: path
          required: true
          schema:
            type: string
            format: uuid
      requestBody:
        content:
          application/json:
            schema:
              $ref: '#/components/schemas/FIDCUpdate'
      responses:
        '200':
          description: FIDC atualizada
          content:
            application/json:
              schema:
                $ref: '#/components/schemas/FIDC'

  # === OPERACOES ===
  /operacoes:
    get:
      summary: Listar operacoes (historico)
      tags: [Operacoes]
      parameters:
        - name: fidc_id
          in: query
          schema:
            type: string
            format: uuid
        - name: status
          in: query
          schema:
            type: string
            enum: [em_processamento, enviando, concluida, cancelada]
        - name: page
          in: query
          schema:
            type: integer
            default: 1
        - name: per_page
          in: query
          schema:
            type: integer
            default: 20
      responses:
        '200':
          description: Lista paginada de operacoes
          content:
            application/json:
              schema:
                $ref: '#/components/schemas/OperacoesPaginadas'

    post:
      summary: Criar nova operacao
      tags: [Operacoes]
      requestBody:
        content:
          application/json:
            schema:
              type: object
              required: [fidc_id]
              properties:
                fidc_id:
                  type: string
                  format: uuid
                numero:
                  type: string
                  example: "Operacao 1234"
      responses:
        '201':
          description: Operacao criada
          content:
            application/json:
              schema:
                $ref: '#/components/schemas/Operacao'

  /operacoes/{id}:
    get:
      summary: Detalhe da operacao com boletos e status
      tags: [Operacoes]
      parameters:
        - name: id
          in: path
          required: true
          schema:
            type: string
            format: uuid
      responses:
        '200':
          description: Detalhes completos da operacao
          content:
            application/json:
              schema:
                $ref: '#/components/schemas/OperacaoDetalhada'

  /operacoes/{id}/finalizar:
    post:
      summary: Finalizar operacao (gera relatorios e arquiva)
      tags: [Operacoes]
      parameters:
        - name: id
          in: path
          required: true
          schema:
            type: string
            format: uuid
      responses:
        '200':
          description: Operacao finalizada
          content:
            application/json:
              schema:
                $ref: '#/components/schemas/Operacao'

  # === UPLOAD ===
  /operacoes/{id}/boletos/upload:
    post:
      summary: Upload de boletos PDF (com split automatico)
      tags: [Upload]
      parameters:
        - name: id
          in: path
          required: true
          schema:
            type: string
            format: uuid
      requestBody:
        content:
          multipart/form-data:
            schema:
              type: object
              properties:
                files:
                  type: array
                  items:
                    type: string
                    format: binary
      responses:
        '200':
          description: Boletos processados
          content:
            application/json:
              schema:
                type: object
                properties:
                  total_paginas:
                    type: integer
                  boletos_criados:
                    type: integer
                  boletos:
                    type: array
                    items:
                      $ref: '#/components/schemas/BoletoResumo'

  /operacoes/{id}/xmls/upload:
    post:
      summary: Upload batch de XMLs de NFe
      tags: [Upload]
      parameters:
        - name: id
          in: path
          required: true
          schema:
            type: string
            format: uuid
      requestBody:
        content:
          multipart/form-data:
            schema:
              type: object
              properties:
                files:
                  type: array
                  items:
                    type: string
                    format: binary
      responses:
        '200':
          description: XMLs processados
          content:
            application/json:
              schema:
                type: object
                properties:
                  total_xmls:
                    type: integer
                  validos:
                    type: integer
                  invalidos:
                    type: integer
                  xmls:
                    type: array
                    items:
                      $ref: '#/components/schemas/XMLResumo'

  # === PROCESSAMENTO ===
  /operacoes/{id}/processar:
    post:
      summary: Executar extracao + renomeacao + validacao 5 camadas
      tags: [Processamento]
      parameters:
        - name: id
          in: path
          required: true
          schema:
            type: string
            format: uuid
      responses:
        '200':
          description: Resultado do processamento
          content:
            application/json:
              schema:
                $ref: '#/components/schemas/ResultadoProcessamento'

  /operacoes/{id}/reprocessar:
    post:
      summary: Reprocessar apenas boletos rejeitados
      tags: [Processamento]
      parameters:
        - name: id
          in: path
          required: true
          schema:
            type: string
            format: uuid
      responses:
        '200':
          description: Resultado do reprocessamento
          content:
            application/json:
              schema:
                $ref: '#/components/schemas/ResultadoProcessamento'

  # === ENVIO ===
  /operacoes/{id}/enviar:
    post:
      summary: Enviar boletos aprovados via Outlook
      tags: [Envio]
      parameters:
        - name: id
          in: path
          required: true
          schema:
            type: string
            format: uuid
      requestBody:
        content:
          application/json:
            schema:
              type: object
              properties:
                modo:
                  type: string
                  enum: [preview, automatico]
                  default: preview
      responses:
        '200':
          description: Resultado do envio
          content:
            application/json:
              schema:
                type: object
                properties:
                  emails_criados:
                    type: integer
                  emails_enviados:
                    type: integer
                  modo:
                    type: string
                  detalhes:
                    type: array
                    items:
                      $ref: '#/components/schemas/EnvioDetalhe'

  # === AUDITORIA ===
  /operacoes/{id}/relatorio:
    get:
      summary: Gerar/download relatorio de auditoria
      tags: [Auditoria]
      parameters:
        - name: id
          in: path
          required: true
          schema:
            type: string
            format: uuid
        - name: formato
          in: query
          schema:
            type: string
            enum: [json, txt]
            default: json
      responses:
        '200':
          description: Relatorio gerado
          content:
            application/json:
              schema:
                $ref: '#/components/schemas/RelatorioAuditoria'
            text/plain:
              schema:
                type: string

  /auditoria/buscar:
    get:
      summary: Buscar em auditorias (por NF, cliente, data)
      tags: [Auditoria]
      parameters:
        - name: q
          in: query
          required: true
          schema:
            type: string
          description: Termo de busca (numero NF, nome cliente, CNPJ)
        - name: data_inicio
          in: query
          schema:
            type: string
            format: date
        - name: data_fim
          in: query
          schema:
            type: string
            format: date
      responses:
        '200':
          description: Resultados da busca
          content:
            application/json:
              schema:
                type: array
                items:
                  $ref: '#/components/schemas/AuditoriaItem'

components:
  schemas:
    Usuario:
      type: object
      properties:
        id:
          type: string
          format: uuid
        nome:
          type: string
        email:
          type: string

    FIDC:
      type: object
      properties:
        id:
          type: string
          format: uuid
        nome:
          type: string
        nome_completo:
          type: string
        cnpj:
          type: string
        cc_emails:
          type: array
          items:
            type: string
        palavras_chave:
          type: array
          items:
            type: string
        cor:
          type: string

    FIDCUpdate:
      type: object
      properties:
        nome_completo:
          type: string
        cnpj:
          type: string
        cc_emails:
          type: array
          items:
            type: string
        palavras_chave:
          type: array
          items:
            type: string
        cor:
          type: string

    Operacao:
      type: object
      properties:
        id:
          type: string
          format: uuid
        numero:
          type: string
        fidc:
          $ref: '#/components/schemas/FIDC'
        status:
          type: string
        modo_envio:
          type: string
        total_boletos:
          type: integer
        total_aprovados:
          type: integer
        total_rejeitados:
          type: integer
        taxa_sucesso:
          type: number
        created_at:
          type: string
          format: date-time

    OperacaoDetalhada:
      allOf:
        - $ref: '#/components/schemas/Operacao'
        - type: object
          properties:
            boletos:
              type: array
              items:
                $ref: '#/components/schemas/BoletoCompleto'
            xmls:
              type: array
              items:
                $ref: '#/components/schemas/XMLResumo'

    OperacoesPaginadas:
      type: object
      properties:
        items:
          type: array
          items:
            $ref: '#/components/schemas/Operacao'
        total:
          type: integer
        page:
          type: integer
        per_page:
          type: integer

    BoletoResumo:
      type: object
      properties:
        id:
          type: string
          format: uuid
        arquivo_original:
          type: string
        paginas:
          type: integer

    BoletoCompleto:
      type: object
      properties:
        id:
          type: string
          format: uuid
        arquivo_original:
          type: string
        arquivo_renomeado:
          type: string
        pagador:
          type: string
        cnpj:
          type: string
        numero_nota:
          type: string
        vencimento:
          type: string
        valor:
          type: number
        valor_formatado:
          type: string
        fidc_detectada:
          type: string
        status:
          type: string
        motivo_rejeicao:
          type: string
        validacoes:
          type: object
          properties:
            camada1:
              type: object
            camada2:
              type: object
            camada3:
              type: object
            camada4:
              type: object
            camada5:
              type: object

    XMLResumo:
      type: object
      properties:
        id:
          type: string
          format: uuid
        nome_arquivo:
          type: string
        numero_nota:
          type: string
        cnpj:
          type: string
        nome_destinatario:
          type: string
        valor_total:
          type: number
        emails:
          type: array
          items:
            type: string
        xml_valido:
          type: boolean

    ResultadoProcessamento:
      type: object
      properties:
        total:
          type: integer
        aprovados:
          type: integer
        rejeitados:
          type: integer
        taxa_sucesso:
          type: number
        boletos:
          type: array
          items:
            $ref: '#/components/schemas/BoletoCompleto'

    EnvioDetalhe:
      type: object
      properties:
        email_para:
          type: array
          items:
            type: string
        email_cc:
          type: array
          items:
            type: string
        assunto:
          type: string
        boletos_count:
          type: integer
        status:
          type: string

    RelatorioAuditoria:
      type: object
      properties:
        execucao_id:
          type: string
        timestamp_inicio:
          type: string
          format: date-time
        timestamp_fim:
          type: string
          format: date-time
        duracao_segundos:
          type: number
        modo:
          type: string
        resumo:
          type: object
          properties:
            total_boletos:
              type: integer
            aprovados:
              type: integer
            rejeitados:
              type: integer
            taxa_sucesso:
              type: number
        boletos:
          type: array
          items:
            type: object

    AuditoriaItem:
      type: object
      properties:
        operacao_id:
          type: string
          format: uuid
        numero_nota:
          type: string
        cliente:
          type: string
        status:
          type: string
        timestamp:
          type: string
          format: date-time
        detalhes:
          type: object

  securitySchemes:
    bearerAuth:
      type: http
      scheme: bearer
      bearerFormat: JWT

security:
  - bearerAuth: []
```

### 5.4 Dependencias & Integracoes

| Dependencia | Tipo | Onde roda | Proposito | Risco |
|-------------|------|-----------|-----------|-------|
| Microsoft Outlook (pywin32) | Externa | **HOST Windows** | Envio de e-mails via COM automation | **Alto** — requer Windows + Outlook no mesmo Host que o Backend |
| Docker Desktop | Infraestrutura | HOST Windows | Gerencia container do PostgreSQL | Baixo — necessario apenas para o banco |
| pdfplumber | Biblioteca | HOST (venv) | Extracao de texto de PDFs de boletos | Baixo — biblioteca madura e estavel |
| PyPDF2 | Biblioteca | HOST (venv) | Split de PDFs multipagina em paginas individuais | Baixo |
| xml.etree.ElementTree | Stdlib | HOST (venv) | Parsing de XMLs de NFe | Baixo — stdlib Python |
| PostgreSQL 16 | Infraestrutura | **Docker container** | Persistencia de dados, auditorias, historico | Baixo — isolado em container |
| Next.js | Framework | HOST (Node.js) | Frontend SSR + rotas de pagina | Baixo |
| FastAPI | Framework | **HOST (venv)** | Backend API REST + processamento | Baixo |
| ERP Viasoft | Externa (indireta) | N/A | Fonte dos XMLs de NFe (upload manual) | Medio — mudanca de formato pode quebrar parsing |
| Portais FIDCs | Externa (indireta) | N/A | Fonte dos boletos PDF (download manual) | Medio — mudanca de layout pode quebrar extratores |

---

## 6. Riscos & Mitigacoes

| ID | Risco | Probabilidade | Impacto | Mitigacao |
|----|-------|---------------|---------|-----------|
| R-001 | FIDC altera layout de boleto PDF, quebrando regex de extracao | Media | Alto | Factory Pattern permite ajustar extrator isolado; testes automatizados por FIDC; alertas quando extracao falha |
| R-002 | pywin32/Outlook COM instavel no Host (travamentos, timeout) | Media | Alto | Implementar retry com backoff; monitorar saude do Outlook; fallback para modo preview se Outlook nao responder; Backend DEVE rodar no Host (nao em container) |
| R-002b | Desenvolvedor tenta containerizar o Backend (quebrando COM) | Media | **Critico** | Documentar decisao arquitetural no README; bloquear criacao de Dockerfile para backend; docker-compose.yml deve conter APENAS o PostgreSQL |
| R-003 | Operador envia boletos para cliente errado (erro de XML ou CNPJ) | Baixa | Alto | Validacao em 5 camadas mantida com tolerancia ZERO; modo preview como padrao; confirmacao explicita antes de envio automatico |
| R-004 | Performance degradada com muitos boletos simultaneos (>50) | Media | Medio | Processamento assincrono com fila; progress bar em tempo real; limitar lote a 50 boletos por operacao |
| R-005 | Perda de dados por falha do servidor local | Baixa | Alto | Backup automatico diario do PostgreSQL; logs de auditoria em filesystem redundante |
| R-006 | XML do Viasoft muda formato/campos | Baixa | Alto | Parser defensivo com fallbacks; validacao de schema; alertas claros quando campo esperado esta ausente |
| R-007 | Conflito de sessao entre 2-3 operadores na mesma operacao | Media | Medio | Lock otimista por operacao (apenas 1 operador por vez); fila de processamento |

---

## 7. Plano de Execucao

### 7.1 Milestones

| Milestone | Descricao | Criterio de Done | Estimativa |
|-----------|-----------|------------------|------------|
| M1 | Fundacao: Setup Hibrido + Auth + CRUD FIDCs | Projeto inicializado (venv + docker-compose + Next.js), login funcional, FIDCs configuradas no banco | 3d |
| M2 | Core Engine: Extratores + Validador + XML Parser | Motor de extracao e validacao 5 camadas portado e testado | 5d |
| M3 | Upload Pipeline: PDFs + XMLs + Split | Upload drag-and-drop, split automatico, parsing de XMLs | 3d |
| M4 | Operacoes: Fluxo Completo de Processamento | Criar operacao, processar boletos, ver resultados de validacao | 3d |
| M5 | Envio: Outlook Integration + Templates | Envio via pywin32, toggle preview/automatico, template de e-mail | 4d |
| M6 | Dashboard + Auditoria | Dashboard operacional, historico, busca, relatorios | 3d |
| M7 | Polish + Testes E2E + Deploy Local | Design System aplicado, testes ponta a ponta, start_system.bat funcional | 3d |

### 7.2 Decomposicao de Tarefas

```markdown
## Milestone 1: Fundacao — Arquitetura Hibrida (3d)
- [ ] TASK-001: Setup projeto Next.js + TypeScript + TailwindCSS + shadcn/ui (Host, Node.js) | Agente: Coder | Est: 3h
- [ ] TASK-002: Setup projeto FastAPI + estrutura de pastas + config (Host, Python venv) | Agente: Coder | Est: 2h
- [ ] TASK-003: Criar docker-compose.yml com PostgreSQL 16 (container) + volume persistente + .env | Agente: Coder | Est: 2h
- [ ] TASK-003b: Criar migrations do schema completo (Alembic ou SQL direto) rodando contra o PostgreSQL do container | Agente: Coder | Est: 2h
- [ ] TASK-004: Implementar autenticacao (JWT + bcrypt + login/logout) | Agente: Coder | Est: 4h
- [ ] TASK-005: CRUD de FIDCs (API + tela de configuracao) | Agente: Coder | Est: 4h
- [ ] TASK-006: Seed das 4 FIDCs com configuracoes do legado | Agente: Coder | Est: 1h
- [ ] TASK-007: Testes unitarios M1 | Agente: QA | Est: 3h
- [ ] TASK-008: Code review M1 | Agente: Reviewer | Est: 2h

## Milestone 2: Core Engine (5d)
- [ ] TASK-009: Portar BaseExtractor + Factory Pattern | Agente: Coder | Est: 3h
- [ ] TASK-010: Portar CapitalExtractor (todos os regex documentados) | Agente: Coder | Est: 4h
- [ ] TASK-011: Portar NovaxExtractor | Agente: Coder | Est: 3h
- [ ] TASK-012: Portar CredvaleExtractor | Agente: Coder | Est: 3h
- [ ] TASK-013: Portar SquidExtractor (incluindo fix do bug v2.0) | Agente: Coder | Est: 4h
- [ ] TASK-014: Portar xml_nfe_reader.py (parser de XMLs NFe) | Agente: Coder | Est: 4h
- [ ] TASK-015: Implementar validador 5 camadas (replicar EnvioBoleto.py) | Agente: Coder | Est: 6h
- [ ] TASK-016: Implementar logica de renomeacao (formato padrao) | Agente: Coder | Est: 2h
- [ ] TASK-017: Implementar deteccao de juros/multa | Agente: Coder | Est: 1h
- [ ] TASK-018: Testes unitarios por extrator (minimo 10 cenarios cada) | Agente: QA | Est: 6h
- [ ] TASK-019: Testes unitarios validador 5 camadas | Agente: QA | Est: 4h
- [ ] TASK-020: Code review M2 | Agente: Reviewer | Est: 3h

## Milestone 3: Upload Pipeline (3d)
- [ ] TASK-021: Endpoint upload de boletos PDF (multipart) | Agente: Coder | Est: 3h
- [ ] TASK-022: Implementar split automatico de PDF (PyPDF2) | Agente: Coder | Est: 3h
- [ ] TASK-023: Endpoint upload de XMLs NFe (batch) | Agente: Coder | Est: 2h
- [ ] TASK-024: Componente drag-and-drop de upload (frontend) | Agente: Coder | Est: 4h
- [ ] TASK-025: Preview visual de boletos apos upload | Agente: Coder | Est: 3h
- [ ] TASK-026: Tabela resumo de XMLs parseados | Agente: Coder | Est: 2h
- [ ] TASK-027: Validacao de arquivos (tipo, tamanho, integridade) | Agente: Coder | Est: 2h
- [ ] TASK-028: Testes unitarios M3 | Agente: QA | Est: 3h
- [ ] TASK-029: Code review M3 | Agente: Reviewer | Est: 2h

## Milestone 4: Operacoes (3d)
- [ ] TASK-030: API CRUD de operacoes + estado do ciclo de vida | Agente: Coder | Est: 4h
- [ ] TASK-031: Tela "Nova Operacao" (selecao FIDC + upload + processar) | Agente: Coder | Est: 6h
- [ ] TASK-032: Endpoint /processar (extracao + validacao + renomeacao) | Agente: Coder | Est: 4h
- [ ] TASK-033: Tela de resultado (lista de boletos com status por camada) | Agente: Coder | Est: 4h
- [ ] TASK-034: Endpoint /reprocessar (apenas rejeitados) | Agente: Coder | Est: 2h
- [ ] TASK-035: Endpoint /finalizar (arquivar + limpar) | Agente: Coder | Est: 2h
- [ ] TASK-036: Testes unitarios M4 | Agente: QA | Est: 3h
- [ ] TASK-037: Code review M4 | Agente: Reviewer | Est: 2h

## Milestone 5: Envio via Outlook (4d)
- [ ] TASK-038: Modulo de integracao pywin32/Outlook (criar email, anexar, send/display) | Agente: Coder | Est: 6h
- [ ] TASK-039: Implementar agrupamento de boletos por cliente (mesmo email) | Agente: Coder | Est: 3h
- [ ] TASK-040: Implementar ordenacao cronologica de anexos | Agente: Coder | Est: 2h
- [ ] TASK-041: Implementar template HTML do corpo do e-mail (identico ao legado) | Agente: Coder | Est: 3h
- [ ] TASK-042: Implementar logica de CC por FIDC | Agente: Coder | Est: 1h
- [ ] TASK-043: Implementar assinatura com imagem (assinatura.jpg) | Agente: Coder | Est: 2h
- [ ] TASK-044: Toggle preview/automatico na interface + confirmacao | Agente: Coder | Est: 3h
- [ ] TASK-045: Endpoint /enviar com suporte a ambos os modos | Agente: Coder | Est: 4h
- [ ] TASK-046: Barra de progresso em tempo real (WebSocket ou SSE) | Agente: Coder | Est: 3h
- [ ] TASK-047: Regra de max 2 emails + log de descarte | Agente: Coder | Est: 2h
- [ ] TASK-048: Testes unitarios M5 | Agente: QA | Est: 4h
- [ ] TASK-049: Code review M5 | Agente: Reviewer | Est: 3h

## Milestone 6: Dashboard + Auditoria (3d)
- [ ] TASK-050: Dashboard principal (KPIs, operacao ativa, ultimas operacoes) | Agente: Coder | Est: 4h
- [ ] TASK-051: Tela de historico de operacoes (filtros + paginacao) | Agente: Coder | Est: 3h
- [ ] TASK-052: Modulo de auditoria (gerar TXT + JSON identicos ao legado) | Agente: Coder | Est: 4h
- [ ] TASK-053: Tela de auditoria com busca (NF, cliente, data) | Agente: Coder | Est: 3h
- [ ] TASK-054: Download de relatorios (TXT e JSON) | Agente: Coder | Est: 2h
- [ ] TASK-055: Log de erros criticos (append-only, formato legado) | Agente: Coder | Est: 2h
- [ ] TASK-056: Testes unitarios M6 | Agente: QA | Est: 3h
- [ ] TASK-057: Code review M6 | Agente: Reviewer | Est: 2h

## Milestone 7: Polish + Testes E2E + Deploy Local (3d)
- [ ] TASK-058: Aplicar Design System Megatela v3.0 em todas as telas | Agente: Coder | Est: 4h
- [ ] TASK-059: Responsividade desktop (1280px+, funcional em 1024px) | Agente: Coder | Est: 2h
- [ ] TASK-060: Testes E2E do fluxo completo (upload -> processar -> enviar) | Agente: QA | Est: 6h
- [ ] TASK-061: Testes de integracao com Outlook real (no Host Windows) | Agente: QA | Est: 4h
- [ ] TASK-062: Criar start_system.bat (sobe docker-compose PostgreSQL + inicia uvicorn + inicia Next.js) | Agente: DevOps | Est: 3h
- [ ] TASK-062b: Criar stop_system.bat (para processos + docker-compose down) | Agente: DevOps | Est: 1h
- [ ] TASK-062c: Criar .env.example com todas as variaveis documentadas | Agente: DevOps | Est: 1h
- [ ] TASK-063: Documentacao de operacao (manual do usuario + guia de instalacao do ambiente hibrido) | Agente: Coder | Est: 3h
- [ ] TASK-064: Code review final + security review | Agente: Reviewer | Est: 3h
```

### 7.3 Sequencia de Execucao

```
M1 (Fundacao — Arquitetura Hibrida)
  TASK-001 (Next.js Host) ──┐
  TASK-002 (FastAPI venv) ──┼──▶ TASK-003 (docker-compose PG) ──▶ TASK-003b (migrations)
                            │         │
                            │         ▼
                            │    TASK-004 ──▶ TASK-005 ──▶ TASK-006
                            │                                  │
                            └──▶ TASK-007 (paralelo) ──▶ TASK-008
                                                              ▼
M2 (Core Engine) ◀───────────────────────────────────────────┘
  TASK-009 ──▶ TASK-010 ──┐
              TASK-011 ──┤
              TASK-012 ──┤──▶ TASK-015 ──▶ TASK-016 ──▶ TASK-017
              TASK-013 ──┤        ▲
  TASK-014 ──────────────┘        │
              TASK-018 (paralelo) ┤
              TASK-019 ──────────┘──▶ TASK-020
                                              │
M3 (Upload) ◀────────────────────────────────┘
  TASK-021 ──▶ TASK-022 ──┐
  TASK-023 ──────────────┤──▶ TASK-024 ──▶ TASK-025 ──▶ TASK-026 ──▶ TASK-027
              TASK-028 ──┤
                         └──▶ TASK-029
                                       │
M4 (Operacoes) ◀──────────────────────┘
  TASK-030 ──▶ TASK-031 ──▶ TASK-032 ──▶ TASK-033 ──▶ TASK-034 ──▶ TASK-035
              TASK-036 (paralelo) ──▶ TASK-037
                                               │
M5 (Envio) ◀─────────────────────────────────┘
  TASK-038 ──▶ TASK-039 ──▶ TASK-040 ──▶ TASK-041 ──▶ TASK-042 ──▶ TASK-043
                                                          │
  TASK-044 ──▶ TASK-045 ──▶ TASK-046 ──▶ TASK-047 ◀─────┘
              TASK-048 (paralelo) ──▶ TASK-049
                                               │
M6 (Dashboard) ◀─────────────────────────────┘
  TASK-050 ──▶ TASK-051 ──┐
  TASK-052 ──▶ TASK-053 ──┤──▶ TASK-054 ──▶ TASK-055
              TASK-056 ──┤
                         └──▶ TASK-057
                                       │
M7 (Polish + Deploy Hibrido) ◀──────┘
  TASK-058 ──▶ TASK-059 ──▶ TASK-060 ──▶ TASK-061 (Outlook no Host)
                                                │
  TASK-062 (start_system.bat) ──┐               │
  TASK-062b (stop_system.bat) ──┤──▶ TASK-062c (.env.example) ──▶ TASK-063 ──▶ TASK-064
                                │
                                ◀───────────────┘
```

---

## 8. Checklist de Qualidade (Gate G4)

### Codigo
- [ ] Testes unitarios com cobertura >= 80%
- [ ] Testes de integracao para fluxos criticos (upload -> processar -> enviar)
- [ ] Teste E2E do fluxo completo com dados reais
- [ ] Sem secrets hardcoded (usar variaveis de ambiente)
- [ ] Linting sem erros (ESLint + Ruff)
- [ ] Todos os 4 extratores testados com boletos reais de cada FIDC

### Seguranca
- [ ] Input validation em todos os endpoints (tipo, tamanho, formato)
- [ ] Autenticacao JWT implementada e funcional
- [ ] Rate limiting ativo nos endpoints de upload
- [ ] Logs sem dados sensiveis (sem passwords, sem conteudo de emails)
- [ ] Upload aceita apenas PDF e XML (validacao de MIME type + extensao)
- [ ] Nenhum dado financeiro trafega para servicos externos

### Integracao Outlook
- [ ] pywin32 testado com Outlook real na maquina de desenvolvimento
- [ ] Modo preview funcional (abre rascunho sem enviar)
- [ ] Modo automatico funcional (envia diretamente)
- [ ] Toggle de modo funcional com confirmacao
- [ ] Assinatura com imagem renderiza corretamente
- [ ] CC por FIDC configurado corretamente para todas as 4 FIDCs
- [ ] Retry implementado para falhas transientes do Outlook

### Paridade com Legado
- [ ] Validacao em 5 camadas produz resultados identicos ao sistema legado
- [ ] Formato de renomeacao identico: `{PAGADOR} - NF {NUMERO} - {DD-MM} - R$ {VALOR}.pdf`
- [ ] Corpo do e-mail identico ao template legado
- [ ] Relatorios TXT e JSON no mesmo formato do legado
- [ ] Regras de CC por FIDC identicas ao FIDC_CONFIG legado
- [ ] Tolerancia de valor = 0 centavos (ZERO)
- [ ] Fuzzy matching de nome >= 85% (SequenceMatcher)
- [ ] Maximo 2 emails por cliente

### Infraestrutura (Arquitetura Hibrida)
- [ ] docker-compose.yml funcional com PostgreSQL 16 + volume persistente
- [ ] PostgreSQL inicializado com schema e seed de FIDCs (via migrations)
- [ ] Backend FastAPI roda no Host Windows via venv + uvicorn (NAO em Docker)
- [ ] Frontend Next.js roda no Host Windows via Node.js (NAO em Docker)
- [ ] start_system.bat funcional: sobe Docker PostgreSQL + inicia Backend + inicia Frontend
- [ ] stop_system.bat funcional: para processos + docker-compose down
- [ ] Variaveis de ambiente configuradas (.env.example fornecido com documentacao)
- [ ] Backup de database configurado (script de backup via pg_dump no container)
- [ ] Logs de aplicacao persistidos em filesystem do Host
- [ ] Verificado que pywin32 acessa Outlook a partir do processo uvicorn no Host

---

## 9. Glossario

| Termo | Definicao |
|-------|-----------|
| FIDC | Fundo de Investimento em Direitos Creditorios — fundo regulado pela CVM que compra direitos de credito |
| Operacao | Lote de boletos antecipados em uma unica transacao com uma FIDC especifica |
| Termo de Duplicatas | Documento legal que formaliza a cessao de credito da JJ para a FIDC |
| XML NFe | Arquivo XML da Nota Fiscal Eletronica, gerado pelo ERP Viasoft, contendo dados completos da venda |
| Boleto | Documento de cobranca bancaria em PDF, gerado pela FIDC apos aprovacao da operacao |
| Viasoft | Sistema ERP usado pela JJ, responsavel por emissao de NFe e cadastro de clientes |
| Duplicata | Titulo de credito representando venda a prazo; cada parcela gera uma duplicata no XML |
| pywin32 | Biblioteca Python para automacao COM no Windows, usada para controlar o Microsoft Outlook |
| Factory Pattern | Padrao de projeto que permite criar objetos (extratores) sem especificar a classe exata |
| Fuzzy Matching | Comparacao aproximada de strings usando SequenceMatcher (similaridade percentual) |
| Modo Preview | E-mails sao abertos como rascunho no Outlook para revisao manual antes do envio |
| Modo Automatico | E-mails sao enviados diretamente pelo Outlook sem revisao manual |
| Arquitetura Hibrida | Modelo onde Backend roda no Host Windows (venv) para acesso COM ao Outlook, e PostgreSQL roda em container Docker para isolamento |
| COM Automation | Component Object Model — tecnologia Windows que permite controlar aplicativos (como Outlook) programaticamente. Requer que o processo controlador rode no mesmo Host que o aplicativo |
| docker-compose | Ferramenta para definir e executar containers Docker. Neste projeto, usado APENAS para o PostgreSQL |
| start_system.bat | Script Windows que inicializa todo o sistema: sobe container PostgreSQL, inicia Backend (uvicorn) e Frontend (Next.js) |

---

## Historico de Revisoes

| Versao | Data | Autor | Mudancas |
|--------|------|-------|----------|
| 1.0 | 2026-02-06 | Planner AI | Versao inicial — PRD completo baseado em analise de 7 documentos Mintlify do sistema legado |
| 1.1 | 2026-02-06 | Planner AI | **Correcao arquitetural critica**: Docker vs Outlook COM. Backend migrado de container para Host Windows (venv). PostgreSQL mantido em Docker. Criados scripts start/stop_system.bat. Adicionado risco R-002b. Atualizado M1 (TASK-003 split + docker-compose) e M7 (TASK-062 split em .bat/.env). Diagrama de arquitetura refeito para modelo hibrido. |
| 1.1 | 2026-02-06 | Stakeholder | **Gate G1 APROVADO**. PRD liberado para pipeline de desenvolvimento. |
