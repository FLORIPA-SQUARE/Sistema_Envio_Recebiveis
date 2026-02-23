"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { apiFetch } from "@/lib/api";
import { useOperationTabs } from "@/contexts/operation-tabs";
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
import { Input } from "@/components/ui/input";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { toast } from "sonner";
import {
  Search,
  ChevronLeft,
  ChevronRight,
  X,
  AlertTriangle,
} from "lucide-react";

interface Fidc {
  id: string;
  nome: string;
  cor: string;
}

interface AuditoriaItem {
  boleto_id: string;
  operacao_id: string;
  operacao_numero: string;
  fidc_id: string;
  fidc_nome: string;
  pagador: string | null;
  cnpj: string | null;
  numero_nota: string | null;
  vencimento: string | null;
  valor: number | null;
  valor_formatado: string | null;
  status: string;
  motivo_rejeicao: string | null;
  juros_detectado: boolean;
  created_at: string;
}

interface AuditoriaBuscarResponse {
  items: AuditoriaItem[];
  total: number;
  page: number;
  per_page: number;
}

function useDebounce(value: string, delay: number): string {
  const [debouncedValue, setDebouncedValue] = useState(value);
  useEffect(() => {
    const handler = setTimeout(() => setDebouncedValue(value), delay);
    return () => clearTimeout(handler);
  }, [value, delay]);
  return debouncedValue;
}

function StatusBadge({ status }: { status: string }) {
  if (status === "aprovado") {
    return (
      <Badge className="bg-success text-success-foreground hover:bg-success/90">
        Aprovado
      </Badge>
    );
  }
  if (status === "parcialmente_aprovado") {
    return (
      <Badge className="bg-blue-600 text-white hover:bg-blue-600/90">
        Parcial
      </Badge>
    );
  }
  if (status === "rejeitado") {
    return <Badge variant="destructive">Rejeitado</Badge>;
  }
  if (status === "pendente") {
    return (
      <Badge className="bg-warning text-warning-foreground hover:bg-warning/90">
        Pendente
      </Badge>
    );
  }
  return <Badge variant="outline">{status}</Badge>;
}

export default function AuditoriaPage() {
  const router = useRouter();
  const { openOperation } = useOperationTabs();
  const [searchTerm, setSearchTerm] = useState("");
  const debouncedSearch = useDebounce(searchTerm, 400);

  const [dataInicio, setDataInicio] = useState("");
  const [dataFim, setDataFim] = useState("");
  const [filterFidc, setFilterFidc] = useState<string>("all");
  const [filterStatus, setFilterStatus] = useState<string>("all");

  const [fidcs, setFidcs] = useState<Fidc[]>([]);
  const [results, setResults] = useState<AuditoriaItem[]>([]);
  const [total, setTotal] = useState(0);
  const [page, setPage] = useState(1);
  const [perPage] = useState(20);
  const [loading, setLoading] = useState(false);
  const [hasSearched, setHasSearched] = useState(false);

  const totalPages = Math.ceil(total / perPage);

  // Carregar lista de FIDCs
  useEffect(() => {
    apiFetch<Fidc[]>("/fidcs").then(setFidcs).catch(() => {});
  }, []);

  // Buscar quando filtros mudam
  useEffect(() => {
    const hasFilters =
      filterFidc !== "all" ||
      filterStatus !== "all" ||
      dataInicio !== "" ||
      dataFim !== "";
    const hasSearch = debouncedSearch.length >= 3;

    if (hasSearch || hasFilters) {
      fetchResults();
    } else if (debouncedSearch.length === 0 && !hasFilters) {
      setResults([]);
      setTotal(0);
      setHasSearched(false);
    }
  }, [debouncedSearch, dataInicio, dataFim, filterFidc, filterStatus, page]);

  async function fetchResults() {
    setLoading(true);
    setHasSearched(true);
    try {
      const params = new URLSearchParams();
      if (debouncedSearch.length >= 3) params.set("q", debouncedSearch);
      if (dataInicio) params.set("data_inicio", dataInicio);
      if (dataFim) params.set("data_fim", dataFim);
      if (filterFidc && filterFidc !== "all") params.set("fidc_id", filterFidc);
      if (filterStatus && filterStatus !== "all") params.set("status", filterStatus);
      params.set("page", String(page));
      params.set("per_page", String(perPage));

      const data = await apiFetch<AuditoriaBuscarResponse>(
        `/auditoria/buscar?${params.toString()}`
      );
      setResults(data.items);
      setTotal(data.total);
    } catch {
      toast.error("Erro ao buscar");
    } finally {
      setLoading(false);
    }
  }

  function clearFilters() {
    setSearchTerm("");
    setDataInicio("");
    setDataFim("");
    setFilterFidc("all");
    setFilterStatus("all");
    setPage(1);
    setResults([]);
    setTotal(0);
    setHasSearched(false);
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

  function formatCurrency(value: number | null) {
    if (value === null) return "\u2014";
    return `R$ ${value.toLocaleString("pt-BR", {
      minimumFractionDigits: 2,
      maximumFractionDigits: 2,
    })}`;
  }

  const hasActiveFilters =
    searchTerm !== "" ||
    dataInicio !== "" ||
    dataFim !== "" ||
    filterFidc !== "all" ||
    filterStatus !== "all";

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-3xl font-bold">Auditoria</h1>
        <p className="text-muted-foreground">
          Busca global de boletos por cliente, NF ou CNPJ
        </p>
      </div>

      {/* Search + Filters Card */}
      <Card>
        <CardHeader>
          <CardTitle className="text-base flex items-center gap-2">
            <Search className="h-4 w-4" />
            Filtros de Busca
          </CardTitle>
        </CardHeader>
        <CardContent className="space-y-4">
          {/* Search input */}
          <div className="relative">
            <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
            <Input
              placeholder="Buscar por nome do cliente, numero NF ou CNPJ..."
              value={searchTerm}
              onChange={(e) => {
                setSearchTerm(e.target.value);
                setPage(1);
              }}
              className="pl-10"
            />
          </div>

          {/* Filter row */}
          <div className="flex flex-col sm:flex-row flex-wrap items-stretch sm:items-end gap-4">
            {/* Date range */}
            <div className="space-y-1">
              <label className="text-sm font-medium">Data Inicio</label>
              <Input
                type="date"
                value={dataInicio}
                onChange={(e) => {
                  setDataInicio(e.target.value);
                  setPage(1);
                }}
                className="w-full sm:w-40"
              />
            </div>
            <div className="space-y-1">
              <label className="text-sm font-medium">Data Fim</label>
              <Input
                type="date"
                value={dataFim}
                onChange={(e) => {
                  setDataFim(e.target.value);
                  setPage(1);
                }}
                className="w-full sm:w-40"
              />
            </div>

            {/* FIDC filter */}
            <div className="space-y-1">
              <label className="text-sm font-medium">FIDC</label>
              <Select
                value={filterFidc}
                onValueChange={(v) => {
                  setFilterFidc(v);
                  setPage(1);
                }}
              >
                <SelectTrigger className="w-full sm:w-44">
                  <SelectValue placeholder="Todos" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="all">Todos</SelectItem>
                  {fidcs.map((f) => (
                    <SelectItem key={f.id} value={f.id}>
                      <div className="flex items-center gap-2">
                        <div
                          className="h-2.5 w-2.5 rounded-full"
                          style={{ backgroundColor: f.cor }}
                        />
                        {f.nome}
                      </div>
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>

            {/* Status filter */}
            <div className="space-y-1">
              <label className="text-sm font-medium">Status</label>
              <Select
                value={filterStatus}
                onValueChange={(v) => {
                  setFilterStatus(v);
                  setPage(1);
                }}
              >
                <SelectTrigger className="w-full sm:w-40">
                  <SelectValue placeholder="Todos" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="all">Todos</SelectItem>
                  <SelectItem value="pendente">Pendente</SelectItem>
                  <SelectItem value="aprovado">Aprovado</SelectItem>
                  <SelectItem value="rejeitado">Rejeitado</SelectItem>
                </SelectContent>
              </Select>
            </div>

            {/* Clear button */}
            {hasActiveFilters && (
              <Button
                variant="ghost"
                size="sm"
                onClick={clearFilters}
                className="gap-1"
              >
                <X className="h-4 w-4" />
                Limpar
              </Button>
            )}
          </div>

          {/* Hint */}
          {searchTerm.length > 0 && searchTerm.length < 3 && (
            <p className="text-sm text-muted-foreground">
              Digite ao menos 3 caracteres para buscar
            </p>
          )}
        </CardContent>
      </Card>

      {/* Results */}
      <Card>
        <CardContent className="pt-6">
          {loading ? (
            <p className="text-center text-muted-foreground py-8">
              Buscando...
            </p>
          ) : !hasSearched ? (
            <div className="text-center py-12 space-y-2">
              <Search className="h-10 w-10 text-muted-foreground/50 mx-auto" />
              <p className="text-muted-foreground">
                Use os filtros acima para buscar boletos
              </p>
              <p className="text-sm text-muted-foreground">
                Busque por nome do cliente, numero da NF, CNPJ ou filtre por
                data, FIDC e status
              </p>
            </div>
          ) : results.length === 0 ? (
            <p className="text-center text-muted-foreground py-8">
              Nenhum boleto encontrado com os filtros informados
            </p>
          ) : (
            <>
              <div className="flex items-center justify-between mb-4">
                <p className="text-sm text-muted-foreground">
                  {total} resultado(s) encontrado(s)
                </p>
              </div>

              <div className="overflow-x-auto">
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead>Operacao</TableHead>
                    <TableHead>NF</TableHead>
                    <TableHead>Cliente (Pagador)</TableHead>
                    <TableHead>CNPJ</TableHead>
                    <TableHead className="text-right">Valor</TableHead>
                    <TableHead>Vencimento</TableHead>
                    <TableHead>Status</TableHead>
                    <TableHead>FIDC</TableHead>
                    <TableHead>Data</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {results.map((item) => (
                    <TableRow
                      key={item.boleto_id}
                      className="cursor-pointer hover:bg-muted/50"
                      onClick={() => {
                        const fidc = fidcs.find((f) => f.id === item.fidc_id);
                        openOperation({
                          operacaoId: item.operacao_id,
                          operacaoNumero: item.operacao_numero,
                          fidcId: item.fidc_id,
                          fidcNome: item.fidc_nome || fidc?.nome || "",
                          fidcCor: fidc?.cor || "",
                        });
                        router.push("/nova-operacao");
                      }}
                    >
                      <TableCell className="font-medium whitespace-nowrap">
                        {item.operacao_numero}
                      </TableCell>
                      <TableCell className="font-[family-name:var(--font-barlow-condensed)]">
                        {item.numero_nota || "\u2014"}
                      </TableCell>
                      <TableCell className="max-w-[200px] truncate">
                        {item.pagador || "\u2014"}
                      </TableCell>
                      <TableCell className="text-sm whitespace-nowrap">
                        {item.cnpj || "\u2014"}
                      </TableCell>
                      <TableCell className="text-right font-[family-name:var(--font-barlow-condensed)] whitespace-nowrap">
                        {item.valor_formatado || formatCurrency(item.valor)}
                      </TableCell>
                      <TableCell className="whitespace-nowrap">
                        {item.vencimento || "\u2014"}
                      </TableCell>
                      <TableCell>
                        <div className="flex items-center gap-1.5">
                          <StatusBadge status={item.status} />
                          {item.juros_detectado && (
                            <AlertTriangle className="h-3.5 w-3.5 text-warning" />
                          )}
                        </div>
                      </TableCell>
                      <TableCell className="whitespace-nowrap">
                        {item.fidc_nome}
                      </TableCell>
                      <TableCell className="text-sm whitespace-nowrap">
                        {formatDate(item.created_at)}
                      </TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
              </div>

              {/* Pagination */}
              {totalPages > 1 && (
                <div className="flex items-center justify-between mt-4 pt-4 border-t">
                  <p className="text-sm text-muted-foreground">
                    Pagina {page} de {totalPages}
                  </p>
                  <div className="flex gap-2">
                    <Button
                      variant="outline"
                      size="sm"
                      onClick={() => setPage(page - 1)}
                      disabled={page <= 1}
                    >
                      <ChevronLeft className="h-4 w-4" />
                      Anterior
                    </Button>
                    <Button
                      variant="outline"
                      size="sm"
                      onClick={() => setPage(page + 1)}
                      disabled={page >= totalPages}
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
