"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { apiFetch } from "@/lib/api";
import {
  Card,
  CardContent,
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
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { toast } from "sonner";
import { Eye, ChevronLeft, ChevronRight, Filter } from "lucide-react";

interface Fidc {
  id: string;
  nome: string;
  cor: string;
}

interface Operacao {
  id: string;
  numero: string;
  fidc_id: string;
  fidc_nome: string | null;
  status: string;
  modo_envio: string;
  total_boletos: number;
  total_aprovados: number;
  total_rejeitados: number;
  taxa_sucesso: number;
  created_at: string;
  updated_at: string;
}

interface OperacoesPaginadas {
  items: Operacao[];
  total: number;
  page: number;
  per_page: number;
}

const STATUS_LABELS: Record<string, { label: string; variant: string }> = {
  em_processamento: { label: "Em Processamento", variant: "outline" },
  enviando: { label: "Enviando", variant: "outline" },
  concluida: { label: "Concluida", variant: "default" },
  cancelada: { label: "Cancelada", variant: "destructive" },
};

function StatusBadge({ status }: { status: string }) {
  const config = STATUS_LABELS[status] || { label: status, variant: "outline" };

  if (status === "concluida") {
    return (
      <Badge className="bg-success text-success-foreground hover:bg-success/90">
        {config.label}
      </Badge>
    );
  }
  if (status === "em_processamento") {
    return (
      <Badge className="bg-warning text-warning-foreground hover:bg-warning/90">
        {config.label}
      </Badge>
    );
  }
  if (status === "cancelada") {
    return <Badge variant="destructive">{config.label}</Badge>;
  }
  return <Badge variant="outline">{config.label}</Badge>;
}

export default function HistoricoPage() {
  const router = useRouter();
  const [operacoes, setOperacoes] = useState<Operacao[]>([]);
  const [fidcs, setFidcs] = useState<Fidc[]>([]);
  const [total, setTotal] = useState(0);
  const [page, setPage] = useState(1);
  const [perPage] = useState(20);
  const [filterFidc, setFilterFidc] = useState<string>("all");
  const [filterStatus, setFilterStatus] = useState<string>("all");
  const [loading, setLoading] = useState(true);

  const totalPages = Math.ceil(total / perPage);

  useEffect(() => {
    apiFetch<Fidc[]>("/fidcs").then(setFidcs).catch(() => {});
  }, []);

  useEffect(() => {
    fetchOperacoes();
  }, [page, filterFidc, filterStatus]);

  async function fetchOperacoes() {
    setLoading(true);
    try {
      const params = new URLSearchParams();
      params.set("page", String(page));
      params.set("per_page", String(perPage));
      if (filterFidc && filterFidc !== "all") params.set("fidc_id", filterFidc);
      if (filterStatus && filterStatus !== "all") params.set("status_filter", filterStatus);

      const data = await apiFetch<OperacoesPaginadas>(`/operacoes?${params.toString()}`);
      setOperacoes(data.items);
      setTotal(data.total);
    } catch {
      toast.error("Erro ao carregar operacoes");
    } finally {
      setLoading(false);
    }
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

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-3xl font-bold">Historico de Operacoes</h1>
        <p className="text-muted-foreground">
          Consulte e gerencie todas as operacoes realizadas
        </p>
      </div>

      {/* Filtros */}
      <Card>
        <CardContent className="pt-6">
          <div className="flex flex-col sm:flex-row flex-wrap items-stretch sm:items-end gap-4">
            <div className="space-y-1.5">
              <label className="text-sm font-medium">FIDC</label>
              <Select value={filterFidc} onValueChange={(v) => { setFilterFidc(v); setPage(1); }}>
                <SelectTrigger className="w-full sm:w-48">
                  <SelectValue placeholder="Todos os FIDCs" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="all">Todos os FIDCs</SelectItem>
                  {fidcs.map((f) => (
                    <SelectItem key={f.id} value={f.id}>{f.nome}</SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>

            <div className="space-y-1.5">
              <label className="text-sm font-medium">Status</label>
              <Select value={filterStatus} onValueChange={(v) => { setFilterStatus(v); setPage(1); }}>
                <SelectTrigger className="w-full sm:w-48">
                  <SelectValue placeholder="Todos os status" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="all">Todos os status</SelectItem>
                  <SelectItem value="em_processamento">Em Processamento</SelectItem>
                  <SelectItem value="concluida">Concluida</SelectItem>
                  <SelectItem value="cancelada">Cancelada</SelectItem>
                </SelectContent>
              </Select>
            </div>

            <Button
              variant="outline"
              onClick={() => { setFilterFidc("all"); setFilterStatus("all"); setPage(1); }}
              className="gap-2"
            >
              <Filter className="h-4 w-4" />
              Limpar Filtros
            </Button>
          </div>
        </CardContent>
      </Card>

      {/* Tabela */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center justify-between">
            <span>Operacoes ({total})</span>
          </CardTitle>
        </CardHeader>
        <CardContent>
          {loading ? (
            <p className="text-center text-muted-foreground py-8">Carregando...</p>
          ) : operacoes.length === 0 ? (
            <p className="text-center text-muted-foreground py-8">
              Nenhuma operacao encontrada.
            </p>
          ) : (
            <>
              <div className="overflow-x-auto">
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead>Numero</TableHead>
                    <TableHead>FIDC</TableHead>
                    <TableHead>Data</TableHead>
                    <TableHead>Status</TableHead>
                    <TableHead className="text-right">Total</TableHead>
                    <TableHead className="text-right">Aprovados</TableHead>
                    <TableHead className="text-right">Rejeitados</TableHead>
                    <TableHead className="text-right">Taxa (%)</TableHead>
                    <TableHead className="text-center">Acoes</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {operacoes.map((op) => (
                    <TableRow
                      key={op.id}
                      className="cursor-pointer hover:bg-muted/50"
                      onClick={() => router.push(`/operacoes/${op.id}`)}
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
                      <TableCell className="text-right font-[family-name:var(--font-barlow-condensed)] text-success">
                        {op.total_aprovados}
                      </TableCell>
                      <TableCell className="text-right font-[family-name:var(--font-barlow-condensed)] text-destructive">
                        {op.total_rejeitados}
                      </TableCell>
                      <TableCell className="text-right font-[family-name:var(--font-barlow-condensed)]">
                        {op.taxa_sucesso.toFixed(1)}%
                      </TableCell>
                      <TableCell className="text-center">
                        <Button
                          variant="ghost"
                          size="icon"
                          onClick={(e) => {
                            e.stopPropagation();
                            router.push(`/operacoes/${op.id}`);
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

              {/* Paginacao */}
              {totalPages > 1 && (
                <div className="flex items-center justify-between pt-4">
                  <p className="text-sm text-muted-foreground">
                    Pagina {page} de {totalPages} ({total} operacoes)
                  </p>
                  <div className="flex gap-2">
                    <Button
                      variant="outline"
                      size="sm"
                      disabled={page <= 1}
                      onClick={() => setPage(page - 1)}
                    >
                      <ChevronLeft className="h-4 w-4" />
                      Anterior
                    </Button>
                    <Button
                      variant="outline"
                      size="sm"
                      disabled={page >= totalPages}
                      onClick={() => setPage(page + 1)}
                    >
                      Proximo
                      <ChevronRight className="h-4 w-4" />
                    </Button>
                  </div>
                </div>
              )}
            </>
          )}
        </CardContent>
      </Card>
    </div>
  );
}
