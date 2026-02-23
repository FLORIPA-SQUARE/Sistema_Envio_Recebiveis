"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import { apiFetch } from "@/lib/api";
import { useOperationTabs } from "@/contexts/operation-tabs";
import { ValoresExplorer } from "@/components/valores-explorer";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { toast } from "sonner";
import {
  FileText,
  CheckCircle2,
  XCircle,
  TrendingUp,
  ArrowRight,
  Eye,
} from "lucide-react";

interface Operacao {
  id: string;
  numero: string;
  fidc_id: string;
  fidc_nome: string | null;
  status: string;
  total_boletos: number;
  total_aprovados: number;
  total_rejeitados: number;
  taxa_sucesso: number;
  valor_bruto: number | null;
  valor_liquido: number | null;
  created_at: string;
}

interface DashboardStats {
  total_operacoes: number;
  total_boletos: number;
  total_aprovados: number;
  total_rejeitados: number;
  taxa_sucesso_global: number;
  operacoes_recentes: Operacao[];
}

function StatusBadge({ status }: { status: string }) {
  if (status === "concluida") {
    return (
      <Badge className="bg-success text-success-foreground hover:bg-success/90">
        Concluida
      </Badge>
    );
  }
  if (status === "em_processamento") {
    return (
      <Badge className="bg-warning text-warning-foreground hover:bg-warning/90">
        Em Processamento
      </Badge>
    );
  }
  if (status === "aguardando_envio") {
    return (
      <Badge className="bg-blue-500 text-white hover:bg-blue-500/90">
        Aguardando Envio
      </Badge>
    );
  }
  if (status === "enviada") {
    return (
      <Badge className="bg-indigo-600 text-white hover:bg-indigo-600/90">
        Enviada
      </Badge>
    );
  }
  if (status === "cancelada") {
    return <Badge variant="destructive">Cancelada</Badge>;
  }
  return <Badge variant="outline">{status}</Badge>;
}

function formatCurrency(value: number | null): string {
  if (value == null) return "—";
  return value.toLocaleString("pt-BR", {
    style: "currency",
    currency: "BRL",
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
  });
}

export default function DashboardPage() {
  const router = useRouter();
  const { openOperation } = useOperationTabs();
  const [stats, setStats] = useState<DashboardStats | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    apiFetch<DashboardStats>("/operacoes/dashboard/stats")
      .then(setStats)
      .catch(() => toast.error("Erro ao carregar dashboard"))
      .finally(() => setLoading(false));
  }, []);

  function handleOpenOperation(op: Operacao) {
    openOperation({
      operacaoId: op.id,
      operacaoNumero: op.numero,
      fidcId: op.fidc_id,
      fidcNome: op.fidc_nome || "",
    });
    router.push("/nova-operacao");
  }

  function formatDate(dateStr: string) {
    return new Date(dateStr).toLocaleDateString("pt-BR", {
      day: "2-digit",
      month: "2-digit",
      year: "numeric",
      hour: "2-digit",
      minute: "2-digit",
    });
  }

  const kpis = [
    {
      label: "Total Boletos",
      value: stats ? String(stats.total_boletos) : "—",
      icon: FileText,
      color: "text-primary",
    },
    {
      label: "Aprovados",
      value: stats ? String(stats.total_aprovados) : "—",
      icon: CheckCircle2,
      color: "text-success",
    },
    {
      label: "Rejeitados",
      value: stats ? String(stats.total_rejeitados) : "—",
      icon: XCircle,
      color: "text-destructive",
    },
    {
      label: "Taxa de Sucesso",
      value: stats ? `${stats.taxa_sucesso_global.toFixed(1)}%` : "—",
      icon: TrendingUp,
      color: "text-primary",
    },
  ];

  return (
    <div className="space-y-8">
      <div>
        <h1 className="text-3xl font-bold">Dashboard</h1>
        <p className="text-muted-foreground">
          Visao geral das operacoes de envio de boletos
        </p>
      </div>

      {/* KPI Cards */}
      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
        {kpis.map((stat) => (
          <Card key={stat.label}>
            <CardHeader className="flex flex-row items-center justify-between pb-2">
              <CardTitle className="text-sm font-medium">
                {stat.label}
              </CardTitle>
              <stat.icon className={`h-4 w-4 ${stat.color}`} />
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-bold font-[family-name:var(--font-barlow-condensed)]">
                {loading ? "..." : stat.value}
              </div>
            </CardContent>
          </Card>
        ))}
      </div>

      {/* Explorador Financeiro */}
      <ValoresExplorer />

      {/* Operacoes Recentes */}
      <Card>
        <CardHeader className="flex flex-row items-center justify-between">
          <div>
            <CardTitle>Operacoes Recentes</CardTitle>
            <CardDescription>
              {stats && stats.total_operacoes > 0
                ? `${stats.total_operacoes} operacoes no total`
                : "Nenhuma operacao encontrada"}
            </CardDescription>
          </div>
          {stats && stats.total_operacoes > 0 && (
            <Link href="/historico">
              <Button variant="outline" size="sm" className="gap-2">
                Ver todas
                <ArrowRight className="h-4 w-4" />
              </Button>
            </Link>
          )}
        </CardHeader>

        {stats && stats.operacoes_recentes.length > 0 && (
          <CardContent>
            <div className="overflow-x-auto">
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead>Numero</TableHead>
                    <TableHead>FIDC</TableHead>
                    <TableHead>Data</TableHead>
                    <TableHead>Status</TableHead>
                    <TableHead className="text-right">Boletos</TableHead>
                    <TableHead className="text-right">Taxa (%)</TableHead>
                    <TableHead className="text-right">Vl. Bruto</TableHead>
                    <TableHead className="text-center">Acoes</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {stats.operacoes_recentes.map((op) => (
                    <TableRow
                      key={op.id}
                      className="cursor-pointer hover:bg-muted/50"
                      onClick={() => handleOpenOperation(op)}
                    >
                      <TableCell className="font-medium font-[family-name:var(--font-barlow-condensed)]">
                        {op.numero}
                      </TableCell>
                      <TableCell>{op.fidc_nome || "—"}</TableCell>
                      <TableCell className="text-sm text-muted-foreground">
                        {formatDate(op.created_at)}
                      </TableCell>
                      <TableCell>
                        <StatusBadge status={op.status} />
                      </TableCell>
                      <TableCell className="text-right font-[family-name:var(--font-barlow-condensed)]">
                        {op.total_boletos}
                      </TableCell>
                      <TableCell className="text-right font-[family-name:var(--font-barlow-condensed)]">
                        {op.taxa_sucesso.toFixed(1)}%
                      </TableCell>
                      <TableCell className="text-right font-[family-name:var(--font-barlow-condensed)] whitespace-nowrap">
                        {formatCurrency(op.valor_bruto)}
                      </TableCell>
                      <TableCell className="text-center">
                        <Button
                          variant="ghost"
                          size="icon"
                          onClick={(e) => {
                            e.stopPropagation();
                            handleOpenOperation(op);
                          }}
                        >
                          <Eye className="h-4 w-4" />
                        </Button>
                      </TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            </div>
          </CardContent>
        )}

        {(!stats || stats.operacoes_recentes.length === 0) && !loading && (
          <CardContent>
            <p className="text-center text-muted-foreground py-4">
              Crie uma nova operacao para comecar.
            </p>
          </CardContent>
        )}
      </Card>
    </div>
  );
}
