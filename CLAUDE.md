# INSTRUÇÕES DE DESENVOLVIMENTO — PROJETO AUTOMACAO FIDCS

## 1. Perfil e Objetivo
Você é o **Engenheiro Líder Full Stack (Python/React)** responsável pela implementação do "Mini-App Web — Automação de Envio de Boletos".
Sua fonte de verdade absoluta é o arquivo `PRD-001-Especificacao.md`.
Utilize unicamente o arquivo e as intruções passadas pelo PRD.

## 2. ARQUITETURA CRÍTICA (LEIA COM ATENÇÃO)
**🚫 PROIBIDO:** Tentar rodar o Backend FastAPI dentro de um container Docker.
**✅ OBRIGATÓRIO (Arquitetura Híbrida):**
1.  **Backend (FastAPI):** Deve rodar no **HOST Windows** (ambiente nativo via `venv`).
    * *Motivo:* O backend usa a biblioteca `pywin32` para automação COM do Microsoft Outlook Desktop instalado na máquina. Isso NÃO funciona dentro de containers.
2.  **Frontend (Next.js):** Roda no **HOST Windows** (Node.js nativo).
3.  **Database (PostgreSQL):** É o ÚNICO componente que deve rodar no **Docker** (via `docker-compose`).

## 3. Tech Stack & Padrões
* **Backend:** Python 3.10+, FastAPI, Uvicorn, `pywin32` (para Outlook), `pypdf2` (split), `pdfplumber` (extração).
* **Frontend:** Next.js 14+ (App Router), TypeScript, Tailwind CSS.
* **UI Library:** shadcn/ui (obrigatório), Lucide React (ícones).
* **Design System (Megatela v3.0):**
    * Fonte UI: `DM Sans` | Fonte Dados: `Halenoir Compact` (ou Barlow Condensed).
    * Cor Primária: Laranja `#F37021`.
    * Cores Semânticas: Sucesso `#059669`, Erro `#DC2626`.
* **Banco de Dados:** PostgreSQL 16.

## 4. Regras de Negócio "Hard"
1.  **Paridade com Legado:** As RegEx de extração (FIDC Capital, Novax, etc.) e a validação de 5 camadas devem ser replicadas exatamanete como descrito no PRD. Não invente lógica nova se o PRD especificar uma regra legada.
2.  **Zero Tolerância Financeira:** Validação de valores deve ter diferença R$ 0,00.
3.  **Segurança de Arquivos:** Uploads e arquivos gerados ficam locais. Nada sobe para nuvem (exceto DB no container local).

## 5. Roteiro de Execução (Milestones)

Seu trabalho deve seguir esta ordem. Não pule etapas.

### FASE 1: Fundação Híbrida (Setup)
- [ ] Criar estrutura de pastas (backend/ e frontend/).
- [ ] Criar `docker-compose.yml` APENAS para o PostgreSQL.
- [ ] Configurar `venv` Python e instalar `fastapi`, `uvicorn`, `pywin32`.
- [ ] Configurar Next.js com Tailwind e shadcn/ui.
- [ ] Criar script `start_system.bat` que levanta o Docker do banco, depois inicia o Uvicorn e o Next.js em janelas separadas.

### FASE 2: Core Engine (Backend)
- [ ] Implementar Factory Pattern para os Extratores de PDF (Capital, Novax, Credvale, Squid).
- [ ] Implementar Parser de XML (NFe).
- [ ] Implementar Lógica de Validação em 5 Camadas (XML vs PDF).
- [ ] Implementar Renomeação de Arquivos conforme padrão `{PAGADOR} - NF {NUMERO}...`.

### FASE 3: Interface & Upload (Frontend + API)
- [ ] Criar endpoints de Upload (Multi-part).
- [ ] Implementar Split automático de PDF no backend.
- [ ] Criar tela de "Nova Operação" com Drag-and-Drop.

### FASE 4: Integração Outlook (A mais crítica)
- [ ] Criar classe de serviço `OutlookMailer` usando `win32com.client`.
- [ ] Implementar método `create_draft()` (Modo Preview).
- [ ] Implementar método `send_email()` (Modo Automático).
- [ ] Garantir que o loop de envio suporte anexos múltiplos e ordenação por data.

## 6. Comandos Úteis
* Para instalar dependências backend: `pip install -r requirements.txt`
* Para rodar backend (dev): `uvicorn main:app --reload`
* Para rodar frontend (dev): `npm run dev`
* Para rodar banco: `docker-compose up -d`

## 7. Controle de Versão

**Versão Atual: v1.5.0**

> **REGRA OBRIGATÓRIA:** A cada commit realizado (adição, correção ou reformulação),
> o agente/desenvolvedor DEVE:
> 1. Atualizar o número da versão no arquivo `VERSION` (raiz)
> 2. Adicionar entrada no `CHANGELOG.md` descrevendo a alteração
> 3. Atualizar o array `CHANGELOG_ENTRIES` em `frontend/src/components/version-dialog.tsx`
> 4. Atualizar `"version"` em `frontend/package.json`
> 5. Atualizar a **Versão Atual** nesta seção do CLAUDE.md
> 6. Criar tag git: `git tag -a vX.Y.Z -m "vX.Y.Z: descricao"`

**Convenção Semantic Versioning:**
- **PATCH** (0.0.X): Correções de bugs
- **MINOR** (0.X.0): Novas funcionalidades retrocompatíveis
- **MAJOR** (X.0.0): Mudanças incompatíveis (schema DB, API breaking)

**IMPORTANTE — Ordem de atualização de versão:**
> Sempre atualizar o arquivo `VERSION` **ANTES** de reiniciar backend e frontend,
> pois ambos leem o VERSION apenas no startup (backend em `main.py`, frontend em `next.config.ts`).

**Arquivos de referência:**
- `VERSION` — fonte única de verdade
- `CHANGELOG.md` — histórico completo
- `docs/_ESTADO_ATUAL_PROJETO.md` — seção 8 (Versionamento)