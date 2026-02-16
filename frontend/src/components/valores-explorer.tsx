"use client";

import { useCallback, useEffect, useState } from "react";
import { apiFetch } from "@/lib/api";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { Input } from "@/components/ui/input";
import { Button } from "@/components/ui/button";
import { toast } from "sonner";
import { BarChart3, X } from "lucide-react";
import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
  ResponsiveContainer,
} from "recharts";

interface Fidc {
  id: string;
  nome: string;
  cor: string;
}

interface ValoresItem {
  periodo: string;
  periodo_label: string;
  valor_bruto: number;
  valor_liquido: number;
  count: number;
}

interface ValoresResponse {
  items: ValoresItem[];
  total_bruto: number;
  total_liquido: number;
  total_operacoes: number;
}

function formatCurrency(value: number): string {
  return value.toLocaleString("pt-BR", {
    style: "currency",
    currency: "BRL",
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
  });
}

function defaultDataInicio(): string {
  const d = new Date();
  d.setMonth(d.getMonth() - 6);
  return d.toISOString().split("T")[0];
}

function defaultDataFim(): string {
  return new Date().toISOString().split("T")[0];
}

function CustomTooltip({
  active,
  payload,
  label,
}: {
  active?: boolean;
  payload?: Array<{ dataKey: string; color: string; name: string; value: number; payload: ValoresItem }>;
  label?: string;
}) {
  if (!active || !payload || payload.length === 0) return null;
  return (
    <div className="bg-card border rounded-lg p-3 shadow-lg text-sm">
      <p className="font-medium mb-1">{label}</p>
      {payload.map((entry) => (
        <p key={entry.dataKey} style={{ color: entry.color }}>
          {entry.name}: {formatCurrency(entry.value)}
        </p>
      ))}
      {payload[0]?.payload?.count != null && (
        <p className="text-muted-foreground mt-1">
          {payload[0].payload.count} operacao(es)
        </p>
      )}
    </div>
  );
}

export function ValoresExplorer() {
  const [dataInicio, setDataInicio] = useState(defaultDataInicio);
  const [dataFim, setDataFim] = useState(defaultDataFim);
  const [agrupamento, setAgrupamento] = useState("mes");
  const [filterFidc, setFilterFidc] = useState("all");
  const [filterStatus, setFilterStatus] = useState("all");

  const [fidcs, setFidcs] = useState<Fidc[]>([]);
  const [data, setData] = useState<ValoresResponse | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    apiFetch<Fidc[]>("/fidcs").then(setFidcs).catch(() => {});
  }, []);

  const fetchData = useCallback(async () => {
    setLoading(true);
    try {
      const params = new URLSearchParams();
      if (dataInicio) params.set("data_inicio", dataInicio);
      if (dataFim) params.set("data_fim", dataFim);
      params.set("agrupamento", agrupamento);
      if (filterFidc && filterFidc !== "all") params.set("fidc_id", filterFidc);
      if (filterStatus && filterStatus !== "all")
        params.set("status_filter", filterStatus);

      const result = await apiFetch<ValoresResponse>(
        `/operacoes/dashboard/valores?${params.toString()}`
      );
      setData(result);
    } catch {
      toast.error("Erro ao carregar dados financeiros");
    } finally {
      setLoading(false);
    }
  }, [dataInicio, dataFim, agrupamento, filterFidc, filterStatus]);

  useEffect(() => {
    fetchData();
  }, [fetchData]);

  return (
    <Card>
      <CardHeader>
        <div className="flex flex-col lg:flex-row lg:items-center lg:justify-between gap-4">
          <div>
            <CardTitle className="flex items-center gap-2">
              <BarChart3 className="h-5 w-5 text-primary" />
              Explorador Financeiro
            </CardTitle>
            <CardDescription>
              Valores bruto e liquido por periodo
            </CardDescription>
          </div>
          {data && !loading && (
            <div className="flex gap-6 text-right">
              <div>
                <p className="text-xs text-muted-foreground">Total Bruto</p>
                <p className="text-lg font-bold font-[family-name:var(--font-barlow-condensed)] text-[var(--chart-1)]">
                  {formatCurrency(data.total_bruto)}
                </p>
              </div>
              <div>
                <p className="text-xs text-muted-foreground">Total Liquido</p>
                <p className="text-lg font-bold font-[family-name:var(--font-barlow-condensed)] text-[var(--chart-2)]">
                  {formatCurrency(data.total_liquido)}
                </p>
              </div>
              <div>
                <p className="text-xs text-muted-foreground">Operacoes</p>
                <p className="text-lg font-bold font-[family-name:var(--font-barlow-condensed)]">
                  {data.total_operacoes}
                </p>
              </div>
            </div>
          )}
        </div>
      </CardHeader>
      <CardContent className="space-y-4">
        {/* Filters row */}
        <div className="flex flex-col sm:flex-row flex-wrap items-stretch sm:items-end gap-3">
          <div className="space-y-1">
            <label className="text-sm font-medium">Data Inicio</label>
            <Input
              type="date"
              value={dataInicio}
              onChange={(e) => setDataInicio(e.target.value)}
              className="w-full sm:w-40"
            />
          </div>
          <div className="space-y-1">
            <label className="text-sm font-medium">Data Fim</label>
            <Input
              type="date"
              value={dataFim}
              onChange={(e) => setDataFim(e.target.value)}
              className="w-full sm:w-40"
            />
          </div>
          <div className="space-y-1">
            <label className="text-sm font-medium">Agrupamento</label>
            <Select value={agrupamento} onValueChange={setAgrupamento}>
              <SelectTrigger className="w-full sm:w-36">
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="dia">Dia</SelectItem>
                <SelectItem value="semana">Semana</SelectItem>
                <SelectItem value="mes">Mes</SelectItem>
              </SelectContent>
            </Select>
          </div>
          <div className="space-y-1">
            <label className="text-sm font-medium">FIDC</label>
            <Select value={filterFidc} onValueChange={setFilterFidc}>
              <SelectTrigger className="w-full sm:w-44">
                <SelectValue placeholder="Todos" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="all">Todos</SelectItem>
                {fidcs.map((f) => (
                  <SelectItem key={f.id} value={f.id}>
                    {f.nome}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>
          <div className="space-y-1">
            <label className="text-sm font-medium">Status</label>
            <Select value={filterStatus} onValueChange={setFilterStatus}>
              <SelectTrigger className="w-full sm:w-40">
                <SelectValue placeholder="Todos" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="all">Todos</SelectItem>
                <SelectItem value="em_processamento">Em Processamento</SelectItem>
                <SelectItem value="concluida">Concluida</SelectItem>
                <SelectItem value="cancelada">Cancelada</SelectItem>
              </SelectContent>
            </Select>
          </div>
          <Button
            variant="ghost"
            size="sm"
            onClick={() => {
              setDataInicio(defaultDataInicio());
              setDataFim(defaultDataFim());
              setAgrupamento("mes");
              setFilterFidc("all");
              setFilterStatus("all");
            }}
            className="gap-1"
          >
            <X className="h-4 w-4" />
            Limpar
          </Button>
        </div>

        {/* Chart */}
        {loading ? (
          <div className="h-72 flex items-center justify-center text-muted-foreground">
            Carregando...
          </div>
        ) : !data || data.items.length === 0 ? (
          <div className="h-72 flex items-center justify-center text-muted-foreground">
            Nenhum dado encontrado para o periodo selecionado
          </div>
        ) : (
          <ResponsiveContainer width="100%" height={320}>
            <BarChart
              data={data.items}
              margin={{ top: 5, right: 20, left: 20, bottom: 5 }}
            >
              <CartesianGrid strokeDasharray="3 3" className="stroke-border" />
              <XAxis
                dataKey="periodo_label"
                tick={{ fontSize: 12 }}
                className="fill-muted-foreground"
              />
              <YAxis
                tick={{ fontSize: 12 }}
                className="fill-muted-foreground"
                tickFormatter={(v: number) =>
                  v >= 1000
                    ? `${(v / 1000).toLocaleString("pt-BR", { maximumFractionDigits: 0 })}k`
                    : String(v)
                }
              />
              <Tooltip content={<CustomTooltip />} />
              <Legend />
              <Bar
                dataKey="valor_bruto"
                name="Valor Bruto"
                fill="var(--chart-1)"
                radius={[4, 4, 0, 0]}
              />
              <Bar
                dataKey="valor_liquido"
                name="Valor Liquido"
                fill="var(--chart-2)"
                radius={[4, 4, 0, 0]}
              />
            </BarChart>
          </ResponsiveContainer>
        )}
      </CardContent>
    </Card>
  );
}
