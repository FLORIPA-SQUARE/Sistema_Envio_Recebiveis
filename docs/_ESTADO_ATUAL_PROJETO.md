# ESTADO ATUAL DO PROJETO — Sistema Automação Envio de Boletos

> **Ultima atualizacao:** 2026-02-09
> **Sessao:** Implementacao M1 + M2 + M3 + M4 + M5 + M6 + M7
> **Fonte de verdade:** `docs/prd/PRD-001-Especificacao.md`

---

## 1. REGRAS ARQUITETURAIS CRÍTICAS (LEMBRETE)

### Arquitetura Híbrida — OBRIGATÓRIA

```
┌─ HOST WINDOWS ──────────────────────────────────────┐
│                                                      │
│  ┌─────────────────┐    ┌──────────────────────┐    │
│  │ Next.js :3000   │    │ FastAPI :8000         │    │
│  │ (npm run dev)   │───►│ (venv + uvicorn)      │──COM──► Outlook Desktop
│  └─────────────────┘    └──────────┬───────────┘    │
│                                    │ TCP:5432        │
│         ┌─ DOCKER ──────────┐      │                │
│         │ PostgreSQL 16     │◄─────┘                │
│         │ (ÚNICO container) │                       │
│         └───────────────────┘                       │
└──────────────────────────────────────────────────────┘
```

**REGRAS INVIOLÁVEIS:**
- **NUNCA** criar Dockerfile para backend ou frontend
- `docker-compose.yml` contém **APENAS** PostgreSQL
- Backend FastAPI roda no **HOST Windows** via `venv` (necessário para `pywin32`)
- Frontend Next.js roda no **HOST Windows** via Node.js
- `pywin32` é dependência **obrigatória** do Host — necessário para automação COM do Microsoft Outlook Desktop
- Motivo: COM do Outlook **NÃO funciona** dentro de containers Linux/Windows

---

## 2. STATUS DO ROTEIRO (Checklist)

### FASE 1: Fundação Híbrida (Setup) — ✅ CONCLUÍDA
- [x] Criar estrutura de pastas (backend/ e frontend/)
- [x] Criar `docker-compose.yml` APENAS para o PostgreSQL
- [x] Configurar `venv` Python e instalar `fastapi`, `uvicorn`, `pywin32`
- [x] Configurar Next.js com Tailwind e shadcn/ui
- [x] Criar script `start_system.bat` e `stop_system.bat`
- [x] Implementar autenticação JWT (login, bcrypt, 8h expiry)
- [x] Implementar CRUD de FIDCs (GET lista, PUT editar)
- [x] Seed de 4 FIDCs + 1 usuário admin
- [x] Alembic migration com 7 tabelas + índices

### FASE 2: Core Engine (Backend) — ✅ CONCLUÍDA
- [x] Implementar Factory Pattern para os Extratores de PDF (Capital, Novax, Credvale, Squid)
- [x] Implementar Parser de XML (NFe) com namespace handling
- [x] Implementar Lógica de Validação em 5 Camadas (XML vs PDF)
- [x] Implementar Renomeação de Arquivos conforme padrão `{PAGADOR} - NF {NUMERO}...`
- [x] Implementar detecção de juros/multa (RF-014)

### FASE 3: Interface & Upload (Frontend + API) — ✅ CONCLUÍDA
- [x] Criar endpoints de Upload (Multi-part) para boletos e XMLs
- [x] Implementar Split automático de PDF no backend (PyPDF2)
- [x] Criar tela de "Nova Operação" com Drag-and-Drop (wizard 3 etapas)
- [x] Criar endpoint de processamento (extração + validação + renomeação)
- [x] Preview/tabela de XMLs parseados
- [x] Tabela de resultado com boletos aprovados/rejeitados

### FASE 4: Ciclo de Vida de Operacoes — ✅ CONCLUIDA
- [x] CRUD completo de operacoes (listar, detalhar, cancelar)
- [x] Fluxo de processamento integrado (reprocessar rejeitados)
- [x] Reprocessar boletos rejeitados (POST /reprocessar)
- [x] Finalizar operacao (POST /finalizar — gera relatorios TXT/JSON)
- [x] Dashboard com KPIs reais (GET /dashboard/stats)
- [x] Tela de Historico com filtros e paginacao
- [x] Tela de Detalhes da Operacao com validacao 5 camadas expandivel
- [x] Audit logging integrado em todas as acoes
- [x] Download de relatorios (GET /relatorio?formato=json|txt_aprovados|txt_erros)

### FASE 5: Integração Outlook — ✅ CONCLUÍDA
- [x] Criar classe de serviço `OutlookMailer` usando `win32com.client`
- [x] Implementar método `create_draft()` (Modo Preview) com retry 3x + exponential backoff
- [x] Implementar método `send_email()` (Modo Automático) com retry 3x + exponential backoff
- [x] Garantir que o loop de envio suporte anexos múltiplos e ordenação por data (vencimento ASC)
- [x] Grouping de boletos por cliente (mesmo email = 1 email) via `email_grouper.py`
- [x] Template de email com corpo HTML completo (nome cliente, NFs, valores, vencimentos, FIDC)
- [x] CC por FIDC (Capital: adm@, Novax: adm@ + controladoria@, etc.)
- [x] Schemas de envio (EnvioRequest, EnvioDetalhe, EnvioResultado, EnvioResponse)
- [x] Endpoint POST /operacoes/{id}/enviar (preview ou automatico)
- [x] Endpoint GET /operacoes/{id}/envios (listar envios)
- [x] Frontend tab "Envio" na pagina de detalhes (toggle modo, preview, historico)

### FASE 6: Dashboard + Auditoria — ✅ CONCLUÍDA
- [x] Dashboard com KPIs reais (Total, Aprovados, Rejeitados, Taxa) — feito em M4
- [x] Historico de operacoes com filtros (FIDC, data, status) — feito em M4
- [x] Geracao de relatorio TXT (formato legado identico) — feito em M4
- [x] Geracao de relatorio JSON estruturado — feito em M4
- [x] Download de relatorios — feito em M4
- [x] Busca global por cliente/NF/CNPJ (GET /auditoria/buscar + pagina frontend)
- [x] Filtros de data, FIDC e status na busca de auditoria

### FASE 7: Polish + Deploy — ✅ CONCLUÍDA
- [x] Responsividade: sidebar hamburger menu (Sheet) em mobile < md
- [x] Responsividade: overflow-x-auto em todas as tabelas (10 tabelas, 5 paginas)
- [x] Responsividade: KPI grids sm:grid-cols-2 (3 paginas)
- [x] Responsividade: filtros empilham vertical em mobile (historico + auditoria)
- [x] Responsividade: header/actions wrap em mobile (detail page)
- [x] .env.example com documentacao STORAGE_DIR
- [x] start_system.bat com health check do backend (PowerShell Invoke-WebRequest)

---

## 3. ESTRUTURA DE DIRETÓRIOS ATUAL

```
Sistema_Envio_Recebiveis/
├── .env                                    # Variáveis de ambiente (dev)
├── .env.example                            # Template
├── .gitignore
├── docker-compose.yml                      # PostgreSQL 16 Alpine APENAS
├── start_system.bat                        # Inicia Docker + Backend + Frontend
├── stop_system.bat                         # Para tudo
├── CLAUDE.md                               # Instruções do projeto
│
├── docs/
│   ├── prd/
│   │   └── PRD-001-Especificacao.md        # FONTE DE VERDADE
│   ├── legacy_mintlify/                    # 7 arquivos de documentação legada
│   │   ├── contexto-de-negocio.mdx
│   │   ├── divida-tecnica-roadmap.mdx
│   │   ├── estrutura-do-projeto.mdx
│   │   ├── extratores-por-fidc.mdx         # REGEX E LÓGICA DOS EXTRATORES
│   │   ├── fluxo-operacional-completo.mdx
│   │   ├── guia-de-build-e-deploy.mdx
│   │   └── troubleshooting.mdx
│   └── _ESTADO_ATUAL_PROJETO.md            # ESTE ARQUIVO
│
├── backend/
│   ├── requirements.txt                    # FastAPI, SQLAlchemy, PyPDF2, pdfplumber, pywin32
│   ├── main.py                             # Entry point — registra routers auth, fidcs, operacoes
│   ├── alembic.ini
│   ├── alembic/
│   │   ├── env.py                          # Async migration config
│   │   └── versions/
│   │       └── 001_initial_schema.py       # 7 tabelas + índices + uuid-ossp
│   ├── app/
│   │   ├── __init__.py
│   │   ├── config.py                       # Settings (pydantic-settings, .env)
│   │   ├── database.py                     # AsyncEngine + AsyncSession (asyncpg)
│   │   ├── security.py                     # JWT + bcrypt + get_current_user
│   │   ├── seed.py                         # 4 FIDCs + 1 admin (admin@jotajota.net.br / admin123)
│   │   ├── models/
│   │   │   ├── __init__.py                 # Re-exporta todos os modelos
│   │   │   ├── usuario.py                  # UUID pk, nome, email, senha_hash, ativo
│   │   │   ├── fidc.py                     # nome, nome_completo, cnpj, cc_emails[], palavras_chave[], cor
│   │   │   ├── operacao.py                 # numero, fidc_id, status, modo_envio, totais
│   │   │   ├── xml_nfe.py                  # numero_nota, cnpj, valor_total, emails[], duplicatas JSONB
│   │   │   ├── boleto.py                   # pagador, valor, validacao_camada1-5 JSONB, status
│   │   │   ├── envio.py                    # email_para[], email_cc[], boletos_ids[], status
│   │   │   └── audit_log.py               # BIGSERIAL pk, acao, detalhes JSONB
│   │   ├── schemas/
│   │   │   ├── __init__.py
│   │   │   ├── auth.py                     # LoginRequest/Response, UsuarioResponse
│   │   │   ├── fidc.py                     # FidcResponse, FidcUpdate
│   │   │   ├── operacao.py                 # OperacaoCreate/Response/Detalhada, Upload/Process/Envio results
│   │   │   └── auditoria.py               # AuditoriaItem + AuditoriaBuscarResponse
│   │   ├── routers/
│   │   │   ├── __init__.py
│   │   │   ├── auth.py                     # POST /auth/login, GET /auth/me
│   │   │   ├── fidcs.py                    # GET /fidcs, PUT /fidcs/{id}
│   │   │   ├── operacoes.py               # 13 endpoints: CRUD, upload, processar, enviar, envios, relatorio
│   │   │   └── auditoria.py              # GET /auditoria/buscar — busca global ILIKE
│   │   ├── extractors/
│   │   │   ├── __init__.py                 # Re-exporta tudo
│   │   │   ├── base.py                     # BaseExtractor (ABC) + helpers compartilhados
│   │   │   ├── capital.py                  # CapitalExtractor — DANFE + boleto
│   │   │   ├── novax.py                    # NovaxExtractor — texto compacto
│   │   │   ├── credvale.py                 # CredvaleExtractor — "Pagador" exato (sem colon)
│   │   │   ├── squid.py                    # SquidExtractor — DANFE + NF do filename
│   │   │   ├── factory.py                  # get_extractor_by_name(), detect_fidc_from_text()
│   │   │   ├── xml_parser.py              # parse_xml_nfe() — namespace handling, email validation
│   │   │   ├── validator.py               # validar_5_camadas() — XML, CNPJ, Nome 85%, Valor 0, Email
│   │   │   └── renamer.py                 # gerar_nome_arquivo() — {PAGADOR} - NF {NUM} - {DD-MM} - R$ {VALOR}.pdf
│   │   └── services/
│   │       ├── __init__.py
│   │       ├── pdf_splitter.py            # split_pdf() via PyPDF2
│   │       ├── audit.py                   # registrar_audit() helper
│   │       ├── report_generator.py        # Geracao TXT/JSON de relatorios
│   │       ├── email_template.py          # gerar_email_html(), gerar_assunto()
│   │       ├── email_grouper.py           # agrupar_boletos_para_envio(), EmailGroup
│   │       └── outlook_mailer.py          # OutlookMailer — COM automation (create_draft, send_email)
│   └── storage/
│       ├── uploads/                        # Uploads por operação (subpastas por UUID)
│       ├── boletos/
│       ├── xmls/
│       ├── auditoria/
│       └── erros/
│
└── frontend/
    ├── package.json                        # Next.js 16, shadcn/ui, Lucide React
    ├── next.config.ts                      # Proxy rewrite /api → localhost:8000
    ├── components.json                     # shadcn/ui config (Tailwind v4)
    ├── tsconfig.json
    ├── src/
    │   ├── app/
    │   │   ├── layout.tsx                  # Root: DM Sans + Barlow Condensed + Toaster
    │   │   ├── globals.css                 # Megatela v3.0: #F37021, success, destructive, warning
    │   │   ├── login/
    │   │   │   └── page.tsx                # Tela login (JWT → localStorage)
    │   │   └── (dashboard)/
    │   │       ├── layout.tsx              # Sidebar autenticada (5 links)
    │   │       ├── page.tsx                # Dashboard (KPIs reais + operacoes recentes)
    │   │       ├── nova-operacao/
    │   │       │   └── page.tsx            # Wizard 3 etapas: Config → Upload → Resultado
    │   │       ├── historico/
    │   │       │   └── page.tsx            # Listagem paginada com filtros FIDC/status
    │   │       ├── auditoria/
    │   │       │   └── page.tsx            # Busca global: search + date range + FIDC/status
    │   │       ├── operacoes/
    │   │       │   └── [id]/
    │   │       │       └── page.tsx        # Detalhe: KPIs, tabs boletos/XMLs/Envio, 5 camadas
    │   │       └── configuracao/
    │   │           └── fidcs/
    │   │               └── page.tsx        # Cards FIDC com edicao de CC emails
    │   ├── components/
    │   │   ├── file-dropzone.tsx           # Drag-and-drop com preview
    │   │   └── ui/                         # shadcn/ui: button, input, label, card, badge, table,
    │   │                                   #            dialog, sonner, select, progress, separator,
    │   │                                   #            scroll-area, tabs, sheet
    │   └── lib/
    │       ├── api.ts                      # apiFetch() — JWT injection + 401 redirect
    │       └── utils.ts                    # cn() helper (shadcn)
    └── .env.local
```

---

## 4. COMANDOS DE EXECUÇÃO

### Opção 1: Script automático
```bat
start_system.bat    :: Inicia Docker + migrations + seed + backend + frontend
stop_system.bat     :: Para tudo
```

### Opção 2: Manual (passo a passo)
```bash
# 1. PostgreSQL (Docker)
docker-compose up -d

# 2. Backend (FastAPI)
cd backend
python -m venv venv                          # Apenas primeira vez
venv\Scripts\activate
pip install -r requirements.txt              # Apenas primeira vez
alembic upgrade head                         # Migrations
python -m app.seed                           # Seed (4 FIDCs + admin)
uvicorn main:app --reload --port 8000

# 3. Frontend (Next.js)
cd frontend
npm install                                  # Apenas primeira vez
npm run dev                                  # http://localhost:3000
```

### Credenciais de desenvolvimento
- **Login:** `admin@jotajota.net.br` / `admin123`
- **API Docs:** http://localhost:8000/api/docs
- **Frontend:** http://localhost:3000

---

## 5. STATUS GERAL

### Projeto COMPLETO (M1-M7)

Todas as fases de desenvolvimento foram concluidas com sucesso.
O sistema esta funcional e pronto para uso em producao.

**Melhorias opcionais futuras:**

1. **Testes E2E** — Cobertura automatizada de fluxo completo
2. **Documentacao de usuario** — Guia de uso com screenshots
3. **Monitoramento** — Logs centralizados, alertas

---

## 6. DECISÕES TÉCNICAS IMPORTANTES

| Decisão | Valor | Motivo |
|---------|-------|--------|
| Tailwind CSS | v4 (CSS-first) | `@theme inline` em `globals.css`, SEM `tailwind.config.ts` |
| shadcn/ui | v3.8+ | Auto-detecta Tailwind v4 |
| Next.js | 16 (App Router) | `next.config.ts` (TypeScript) |
| Fontes | DM Sans + Barlow Condensed | via `next/font/google` |
| API Proxy | Next.js rewrites | `/api/*` → `localhost:8000` |
| DB Driver | asyncpg | SQLAlchemy 2.x async |
| Encoding | Evitar ≥ em mensagens | Windows cp1252 não suporta Unicode math |
| Upload | FormData direto | Não usar `apiFetch` wrapper (não suporta multipart) |
| Valor tolerance | 0 centavos | Zero tolerância — regra de negócio inviolável |
| Fuzzy match | 85% (SequenceMatcher) | Camada 3 — warning only, nunca bloqueia |
| Max emails | 2 por cliente | 2º email descartado se > 100 chars |

---

## 7. SEED DATA (Referência Rápida)

| FIDC | CNPJ | Cor | CC Emails |
|------|------|-----|-----------|
| CAPITAL | 12.910.463/0001-70 | #0e639c | adm@jotajota.net.br |
| NOVAX | 28.879.551/0001-96 | #107c10 | adm@jotajota.net.br, controladoria@novaxfidc.com.br |
| CREDVALE | — | #d83b01 | adm@jotajota.net.br, nichole@credvalefidc.com.br |
| SQUID | — | #8764b8 | adm@jotajota.net.br |
