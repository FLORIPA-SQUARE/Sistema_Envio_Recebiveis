"use client";

import { useState, useEffect } from "react";
import { Info } from "lucide-react";
import { Badge } from "@/components/ui/badge";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogDescription,
} from "@/components/ui/dialog";
import { ScrollArea } from "@/components/ui/scroll-area";
import { Separator } from "@/components/ui/separator";

interface VersionInfo {
  version: string;
  name: string;
}

const CHANGELOG_ENTRIES = [
  {
    version: "1.6.1",
    date: "2026-02-16",
    summary: "Correcao: upload de boletos para FIDCs novas",
    items: [
      "Extrator generico como fallback para FIDCs sem extrator especializado",
      "Corrigido erro 500 no upload, processamento e reprocessamento de boletos",
    ],
  },
  {
    version: "1.6.0",
    date: "2026-02-16",
    summary: "CRUD de FIDCs e textos de email personalizados (#A04, #A05)",
    items: [
      "CRUD completo: criar, editar, ativar/desativar FIDCs",
      "Textos de email personalizados por FIDC (introducao, fechamento, assinatura)",
      "Fallback per-FIDC: textos do FIDC sobrepoem o layout global",
      "Interface com tabs (Dados Gerais + Texto de Email) e color picker",
      "FIDCs inativos filtrados automaticamente em nova operacao e historico",
    ],
  },
  {
    version: "1.5.0",
    date: "2026-02-16",
    summary: "Explorador financeiro (#A02)",
    items: [
      "Grafico de barras interativo no Dashboard (recharts)",
      "Valores bruto e liquido agregados por dia, semana ou mes",
      "Filtros por data, FIDC e status com totais do periodo",
      "Endpoint GET /operacoes/dashboard/valores para agregacao",
    ],
  },
  {
    version: "1.4.0",
    date: "2026-02-16",
    summary: "Auditoria do banco de dados (#A05)",
    items: [
      "Registro de login no audit_log para rastreamento de acessos",
      "Coluna 'Criado por' na tabela de historico de operacoes",
      "Nome do criador visivel no dashboard de operacoes recentes",
      "Endpoint GET /operacoes/{id}/atividade para historico de acoes",
      "Tab Atividade com timeline visual mostrando quem executou cada acao",
    ],
  },
  {
    version: "1.3.0",
    date: "2026-02-16",
    summary: "Exibir valores por operacao (#A06)",
    items: [
      "Valor Total Bruto (soma dos boletos aprovados) visivel no historico e dashboard",
      "Valor Liquido editavel por operacao na tabela de historico",
      "Calculo automatico de valor bruto durante processamento de boletos",
      "Endpoint PATCH para atualizar valor liquido com registro de auditoria",
    ],
  },
  {
    version: "1.2.0",
    date: "2026-02-16",
    summary: "Saudacao automatica por horario (#A01)",
    items: [
      "Saudacao do email ajustada automaticamente: Bom dia, Boa tarde ou Boa noite",
      "Campo saudacao na configuracao de email agora e read-only",
      "Horarios: Bom dia (0h-12h), Boa tarde (13h-18h), Boa noite (19h-23h)",
    ],
  },
  {
    version: "1.1.0",
    date: "2026-02-16",
    summary: "Indicador de historico de versoes (#A06)",
    items: [
      "Indicador de versao visivel na sidebar com dialog de historico",
      "Endpoint GET /api/v1/version retornando versao atual",
      "Arquivo VERSION como fonte unica de verdade",
      "CHANGELOG.md com historico completo de alteracoes",
      "Regra obrigatoria de atualizacao de versao no CLAUDE.md",
    ],
  },
  {
    version: "1.0.0",
    date: "2026-02-13",
    summary: "Primeira versao completa (M1-M7)",
    items: [
      "Fundacao hibrida: FastAPI + Next.js + PostgreSQL (Docker)",
      "Extratores PDF (Capital, Novax, Credvale, Squid) + Validacao 5 camadas",
      "Upload drag-and-drop com split automatico de PDF",
      "Ciclo de vida de operacoes (CRUD, processamento, envio)",
      "Email SMTP: envio direto e modo preview com anexos",
      "Dashboard KPIs, Historico, Auditoria com busca global",
      "Sistema de abas multi-operacao (max 10)",
      "Layouts de email configuraveis (ate 3 templates)",
      "Responsividade completa + deploy LAN",
    ],
  },
];

export function VersionBadge() {
  const [open, setOpen] = useState(false);
  const [versionInfo, setVersionInfo] = useState<VersionInfo | null>(null);

  const displayVersion = process.env.NEXT_PUBLIC_APP_VERSION || "—";

  useEffect(() => {
    fetch("/api/v1/version")
      .then((r) => r.json())
      .then((data: VersionInfo) => setVersionInfo(data))
      .catch(() => {});
  }, []);

  const version = versionInfo?.version || displayVersion;

  return (
    <>
      <button
        type="button"
        onClick={() => setOpen(true)}
        className="flex items-center gap-1.5 text-xs text-muted-foreground hover:text-foreground transition-colors cursor-pointer"
        title="Historico de versoes"
      >
        <Info className="h-3 w-3" />
        <span className="font-[family-name:var(--font-barlow-condensed)] font-medium">
          v{version}
        </span>
      </button>

      <Dialog open={open} onOpenChange={setOpen}>
        <DialogContent className="sm:max-w-md">
          <DialogHeader>
            <DialogTitle className="flex items-center gap-2">
              <span className="text-primary">Jota</span>Jota
              <Badge variant="outline" className="text-xs font-normal">
                v{version}
              </Badge>
            </DialogTitle>
            <DialogDescription>
              Historico de versoes do sistema
            </DialogDescription>
          </DialogHeader>

          <ScrollArea className="max-h-[400px] pr-4">
            <div className="space-y-4">
              {CHANGELOG_ENTRIES.map((entry, idx) => (
                <div key={entry.version}>
                  <div className="flex items-center justify-between mb-2">
                    <h3 className="font-semibold text-sm">v{entry.version}</h3>
                    <span className="text-xs text-muted-foreground font-[family-name:var(--font-barlow-condensed)] font-medium">
                      {entry.date}
                    </span>
                  </div>
                  <p className="text-xs text-muted-foreground mb-2">
                    {entry.summary}
                  </p>
                  <ul className="space-y-1">
                    {entry.items.map((item, i) => (
                      <li
                        key={i}
                        className="text-xs text-muted-foreground flex gap-2"
                      >
                        <span className="text-primary mt-0.5 shrink-0">•</span>
                        <span>{item}</span>
                      </li>
                    ))}
                  </ul>
                  {idx < CHANGELOG_ENTRIES.length - 1 && (
                    <Separator className="mt-4" />
                  )}
                </div>
              ))}
            </div>
          </ScrollArea>
        </DialogContent>
      </Dialog>
    </>
  );
}
