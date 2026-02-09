"use client";

import { useEffect, useState } from "react";
import { useRouter, useParams } from "next/navigation";
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
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Progress } from "@/components/ui/progress";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { Separator } from "@/components/ui/separator";
import { toast } from "sonner";
import {
  ArrowLeft,
  FileText,
  CheckCircle2,
  XCircle,
  TrendingUp,
  RefreshCw,
  CheckCheck,
  Ban,
  Download,
  ChevronDown,
  ChevronUp,
  AlertTriangle,
  Mail,
  Send,
  Eye,
  Loader2,
} from "lucide-react";

interface Boleto {
  id: string;
  arquivo_original: string;
  arquivo_renomeado: string | null;
  pagador: string | null;
  cnpj: string | null;
  numero_nota: string | null;
  vencimento: string | null;
  valor: number | null;
  valor_formatado: string | null;
  fidc_detectada: string | null;
  status: string;
  motivo_rejeicao: string | null;
  validacao_camada1: CamadaResult | null;
  validacao_camada2: CamadaResult | null;
  validacao_camada3: CamadaResult | null;
  validacao_camada4: CamadaResult | null;
  validacao_camada5: CamadaResult | null;
  juros_detectado: boolean;
}

interface CamadaResult {
  camada: number;
  nome: string;
  aprovado: boolean;
  mensagem: string;
  bloqueia: boolean;
  detalhes: Record<string, unknown> | null;
}

interface XmlResumo {
  id: string;
  nome_arquivo: string;
  numero_nota: string;
  cnpj: string | null;
  nome_destinatario: string | null;
  valor_total: number | null;
  emails: string[];
  emails_invalidos: string[];
  xml_valido: boolean;
}

interface FidcInfo {
  id: string;
  nome: string;
  cor: string;
}

interface EnvioDetalhe {
  email_para: string[];
  email_cc: string[];
  assunto: string;
  boletos_count: number;
  xmls_count: number;
  status: string;
}

interface EnvioResultado {
  emails_criados: number;
  emails_enviados: number;
  modo: string;
  detalhes: EnvioDetalhe[];
}

interface EnvioRecord {
  id: string;
  email_para: string[];
  email_cc: string[];
  assunto: string;
  modo: string;
  status: string;
  erro_detalhes: string | null;
  boletos_ids: string[];
  xmls_anexados: string[];
  timestamp_envio: string | null;
  created_at: string;
}

interface OperacaoDetalhada {
  id: string;
  numero: string;
  fidc: FidcInfo;
  status: string;
  modo_envio: string;
  total_boletos: number;
  total_aprovados: number;
  total_rejeitados: number;
  taxa_sucesso: number;
  created_at: string;
  boletos: Boleto[];
  xmls: XmlResumo[];
}

function StatusBadge({ status }: { status: string }) {
  if (status === "aprovado" || status === "concluida") {
    return (
      <Badge className="bg-success text-success-foreground hover:bg-success/90">
        {status === "aprovado" ? "Aprovado" : "Concluida"}
      </Badge>
    );
  }
  if (status === "rejeitado" || status === "cancelada") {
    return <Badge variant="destructive">{status === "rejeitado" ? "Rejeitado" : "Cancelada"}</Badge>;
  }
  if (status === "em_processamento") {
    return (
      <Badge className="bg-warning text-warning-foreground hover:bg-warning/90">
        Em Processamento
      </Badge>
    );
  }
  if (status === "pendente") {
    return <Badge variant="outline">Pendente</Badge>;
  }
  return <Badge variant="outline">{status}</Badge>;
}

function CamadaLine({ camada }: { camada: CamadaResult | null }) {
  if (!camada) return <span className="text-muted-foreground">N/A</span>;

  return (
    <div className="flex items-start gap-2 text-sm">
      {camada.aprovado ? (
        <CheckCircle2 className="h-4 w-4 shrink-0 text-success mt-0.5" />
      ) : camada.bloqueia ? (
        <XCircle className="h-4 w-4 shrink-0 text-destructive mt-0.5" />
      ) : (
        <AlertTriangle className="h-4 w-4 shrink-0 text-warning mt-0.5" />
      )}
      <div>
        <span className="font-medium">Camada {camada.camada} ({camada.nome}):</span>{" "}
        <span className="text-muted-foreground">{camada.mensagem}</span>
      </div>
    </div>
  );
}

export default function OperacaoDetailPage() {
  const router = useRouter();
  const params = useParams();
  const opId = params.id as string;

  const [operacao, setOperacao] = useState<OperacaoDetalhada | null>(null);
  const [loading, setLoading] = useState(true);
  const [expandedBoleto, setExpandedBoleto] = useState<string | null>(null);
  const [actionLoading, setActionLoading] = useState(false);
  const [confirmDialog, setConfirmDialog] = useState<"finalizar" | "cancelar" | "envio_auto" | null>(null);
  const [envioMode, setEnvioMode] = useState<"preview" | "automatico">("preview");
  const [envioLoading, setEnvioLoading] = useState(false);
  const [envioResult, setEnvioResult] = useState<EnvioResultado | null>(null);
  const [envios, setEnvios] = useState<EnvioRecord[]>([]);
  const [enviosLoading, setEnviosLoading] = useState(false);

  useEffect(() => {
    fetchOperacao();
  }, [opId]);

  async function fetchOperacao() {
    setLoading(true);
    try {
      const data = await apiFetch<OperacaoDetalhada>(`/operacoes/${opId}`);
      setOperacao(data);
    } catch {
      toast.error("Erro ao carregar operacao");
    } finally {
      setLoading(false);
    }
  }

  async function fetchEnvios() {
    setEnviosLoading(true);
    try {
      const data = await apiFetch<EnvioRecord[]>(`/operacoes/${opId}/envios`);
      setEnvios(data);
    } catch {
      // Silencioso — envios pode nao existir ainda
    } finally {
      setEnviosLoading(false);
    }
  }

  async function handleEnviar() {
    setEnvioLoading(true);
    setConfirmDialog(null);
    setEnvioResult(null);
    try {
      const data = await apiFetch<EnvioResultado>(`/operacoes/${opId}/enviar`, {
        method: "POST",
        body: JSON.stringify({ modo: envioMode }),
      });
      setEnvioResult(data);
      if (envioMode === "preview") {
        toast.success(`${data.emails_criados} rascunho(s) criado(s) no Outlook`);
      } else {
        toast.success(`${data.emails_enviados} email(s) enviado(s) com sucesso`);
      }
      await fetchEnvios();
    } catch (err) {
      toast.error(err instanceof Error ? err.message : "Erro ao enviar");
    } finally {
      setEnvioLoading(false);
    }
  }

  async function handleReprocessar() {
    setActionLoading(true);
    try {
      await apiFetch(`/operacoes/${opId}/reprocessar`, { method: "POST" });
      toast.success("Boletos reprocessados com sucesso");
      await fetchOperacao();
    } catch (err) {
      toast.error(err instanceof Error ? err.message : "Erro ao reprocessar");
    } finally {
      setActionLoading(false);
    }
  }

  async function handleFinalizar() {
    setActionLoading(true);
    setConfirmDialog(null);
    try {
      await apiFetch(`/operacoes/${opId}/finalizar`, { method: "POST" });
      toast.success("Operacao finalizada com sucesso");
      await fetchOperacao();
    } catch (err) {
      toast.error(err instanceof Error ? err.message : "Erro ao finalizar");
    } finally {
      setActionLoading(false);
    }
  }

  async function handleCancelar() {
    setActionLoading(true);
    setConfirmDialog(null);
    try {
      await apiFetch(`/operacoes/${opId}/cancelar`, { method: "POST" });
      toast.success("Operacao cancelada");
      await fetchOperacao();
    } catch (err) {
      toast.error(err instanceof Error ? err.message : "Erro ao cancelar");
    } finally {
      setActionLoading(false);
    }
  }

  function handleDownload(formato: string) {
    const token = localStorage.getItem("token");
    window.open(
      `/api/v1/operacoes/${opId}/relatorio?formato=${formato}&token=${token}`,
      "_blank"
    );
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
    if (value === null) return "—";
    return `R$ ${value.toLocaleString("pt-BR", { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`;
  }

  if (loading) {
    return (
      <div className="flex items-center justify-center py-16">
        <p className="text-muted-foreground">Carregando...</p>
      </div>
    );
  }

  if (!operacao) {
    return (
      <div className="space-y-4">
        <p className="text-destructive">Operacao nao encontrada</p>
        <Button variant="outline" onClick={() => router.push("/historico")}>
          Voltar ao Historico
        </Button>
      </div>
    );
  }

  const isEmProcessamento = operacao.status === "em_processamento";
  const isConcluida = operacao.status === "concluida";
  const temRejeitados = operacao.total_rejeitados > 0;

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col gap-4 sm:flex-row sm:items-start sm:justify-between">
        <div className="space-y-1">
          <div className="flex items-center gap-3">
            <Button
              variant="ghost"
              size="icon"
              onClick={() => router.push("/historico")}
            >
              <ArrowLeft className="h-4 w-4" />
            </Button>
            <h1 className="text-3xl font-bold">{operacao.numero}</h1>
            <StatusBadge status={operacao.status} />
          </div>
          <div className="flex items-center gap-3 pl-12">
            <div
              className="h-3 w-3 rounded-full"
              style={{ backgroundColor: operacao.fidc.cor }}
            />
            <span className="text-muted-foreground">{operacao.fidc.nome}</span>
            <span className="text-muted-foreground">|</span>
            <span className="text-sm text-muted-foreground">
              {formatDate(operacao.created_at)}
            </span>
          </div>
        </div>

        {/* Action buttons */}
        <div className="flex flex-wrap gap-2">
          {isEmProcessamento && temRejeitados && (
            <Button
              variant="outline"
              onClick={handleReprocessar}
              disabled={actionLoading}
              className="gap-2"
            >
              <RefreshCw className="h-4 w-4" />
              Reprocessar Rejeitados
            </Button>
          )}
          {isEmProcessamento && (
            <>
              <Button
                onClick={() => setConfirmDialog("finalizar")}
                disabled={actionLoading}
                className="gap-2"
              >
                <CheckCheck className="h-4 w-4" />
                Finalizar
              </Button>
              <Button
                variant="destructive"
                onClick={() => setConfirmDialog("cancelar")}
                disabled={actionLoading}
                className="gap-2"
              >
                <Ban className="h-4 w-4" />
                Cancelar
              </Button>
            </>
          )}
          {isConcluida && (
            <>
              <Button
                variant="outline"
                onClick={() => handleDownload("txt_aprovados")}
                className="gap-2"
              >
                <Download className="h-4 w-4" />
                TXT Aprovados
              </Button>
              <Button
                variant="outline"
                onClick={() => handleDownload("txt_erros")}
                className="gap-2"
              >
                <Download className="h-4 w-4" />
                TXT Erros
              </Button>
              <Button
                variant="outline"
                onClick={() => handleDownload("json")}
                className="gap-2"
              >
                <Download className="h-4 w-4" />
                JSON
              </Button>
            </>
          )}
        </div>
      </div>

      {/* KPI Cards */}
      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
        <Card>
          <CardHeader className="flex flex-row items-center justify-between pb-2">
            <CardTitle className="text-sm font-medium">Total Boletos</CardTitle>
            <FileText className="h-4 w-4 text-primary" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold font-[family-name:var(--font-barlow-condensed)]">
              {operacao.total_boletos}
            </div>
          </CardContent>
        </Card>
        <Card>
          <CardHeader className="flex flex-row items-center justify-between pb-2">
            <CardTitle className="text-sm font-medium">Aprovados</CardTitle>
            <CheckCircle2 className="h-4 w-4 text-success" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold font-[family-name:var(--font-barlow-condensed)] text-success">
              {operacao.total_aprovados}
            </div>
          </CardContent>
        </Card>
        <Card>
          <CardHeader className="flex flex-row items-center justify-between pb-2">
            <CardTitle className="text-sm font-medium">Rejeitados</CardTitle>
            <XCircle className="h-4 w-4 text-destructive" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold font-[family-name:var(--font-barlow-condensed)] text-destructive">
              {operacao.total_rejeitados}
            </div>
          </CardContent>
        </Card>
        <Card>
          <CardHeader className="flex flex-row items-center justify-between pb-2">
            <CardTitle className="text-sm font-medium">Taxa de Sucesso</CardTitle>
            <TrendingUp className="h-4 w-4 text-primary" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold font-[family-name:var(--font-barlow-condensed)]">
              {operacao.taxa_sucesso.toFixed(1)}%
            </div>
          </CardContent>
        </Card>
      </div>

      {/* Progress bar */}
      {operacao.total_boletos > 0 && (
        <Progress value={operacao.taxa_sucesso} className="h-2" />
      )}

      {/* Tabs: Boletos | XMLs */}
      <Tabs defaultValue="boletos">
        <TabsList>
          <TabsTrigger value="boletos">
            Boletos ({operacao.boletos.length})
          </TabsTrigger>
          <TabsTrigger value="xmls">
            XMLs ({operacao.xmls.length})
          </TabsTrigger>
          <TabsTrigger value="envio" onClick={() => fetchEnvios()}>
            Envio ({envios.length})
          </TabsTrigger>
        </TabsList>

        <TabsContent value="boletos" className="mt-4">
          <Card>
            <CardContent className="pt-6">
              {operacao.boletos.length === 0 ? (
                <p className="text-center text-muted-foreground py-8">
                  Nenhum boleto nesta operacao
                </p>
              ) : (
                <div className="overflow-x-auto">
                <Table>
                  <TableHeader>
                    <TableRow>
                      <TableHead className="w-8"></TableHead>
                      <TableHead>Status</TableHead>
                      <TableHead>Arquivo</TableHead>
                      <TableHead>Pagador</TableHead>
                      <TableHead>NF</TableHead>
                      <TableHead>Vencimento</TableHead>
                      <TableHead className="text-right">Valor</TableHead>
                      <TableHead>Motivo</TableHead>
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    {operacao.boletos.map((boleto) => (
                      <>
                        <TableRow
                          key={boleto.id}
                          className="cursor-pointer hover:bg-muted/50"
                          onClick={() =>
                            setExpandedBoleto(
                              expandedBoleto === boleto.id ? null : boleto.id
                            )
                          }
                        >
                          <TableCell>
                            {expandedBoleto === boleto.id ? (
                              <ChevronUp className="h-4 w-4 text-muted-foreground" />
                            ) : (
                              <ChevronDown className="h-4 w-4 text-muted-foreground" />
                            )}
                          </TableCell>
                          <TableCell>
                            <div className="flex items-center gap-1.5">
                              <StatusBadge status={boleto.status} />
                              {boleto.juros_detectado && (
                                <Badge className="bg-warning text-warning-foreground text-xs">
                                  Juros
                                </Badge>
                              )}
                            </div>
                          </TableCell>
                          <TableCell
                            className="max-w-xs truncate text-sm"
                            title={boleto.arquivo_renomeado || boleto.arquivo_original}
                          >
                            {boleto.arquivo_renomeado || boleto.arquivo_original}
                          </TableCell>
                          <TableCell className="max-w-[180px] truncate">
                            {boleto.pagador || "—"}
                          </TableCell>
                          <TableCell className="font-[family-name:var(--font-barlow-condensed)]">
                            {boleto.numero_nota || "—"}
                          </TableCell>
                          <TableCell>{boleto.vencimento || "—"}</TableCell>
                          <TableCell className="text-right font-[family-name:var(--font-barlow-condensed)]">
                            {boleto.valor_formatado || formatCurrency(boleto.valor)}
                          </TableCell>
                          <TableCell className="max-w-[200px] truncate text-sm text-destructive">
                            {boleto.motivo_rejeicao || ""}
                          </TableCell>
                        </TableRow>

                        {/* Expanded row: 5 camadas */}
                        {expandedBoleto === boleto.id && (
                          <TableRow key={`${boleto.id}-detail`}>
                            <TableCell colSpan={8}>
                              <div className="rounded-lg bg-muted/30 p-4 space-y-2">
                                <p className="text-sm font-semibold mb-3">
                                  Validacao em 5 Camadas
                                </p>
                                <CamadaLine camada={boleto.validacao_camada1} />
                                <CamadaLine camada={boleto.validacao_camada2} />
                                <CamadaLine camada={boleto.validacao_camada3} />
                                <CamadaLine camada={boleto.validacao_camada4} />
                                <CamadaLine camada={boleto.validacao_camada5} />
                                {boleto.juros_detectado && (
                                  <>
                                    <Separator className="my-2" />
                                    <div className="flex items-center gap-2 text-sm text-warning">
                                      <AlertTriangle className="h-4 w-4" />
                                      Juros/multa detectado neste boleto
                                    </div>
                                  </>
                                )}
                              </div>
                            </TableCell>
                          </TableRow>
                        )}
                      </>
                    ))}
                  </TableBody>
                </Table>
                </div>
              )}
            </CardContent>
          </Card>
        </TabsContent>

        <TabsContent value="xmls" className="mt-4">
          <Card>
            <CardContent className="pt-6">
              {operacao.xmls.length === 0 ? (
                <p className="text-center text-muted-foreground py-8">
                  Nenhum XML nesta operacao
                </p>
              ) : (
                <div className="overflow-x-auto">
                <Table>
                  <TableHeader>
                    <TableRow>
                      <TableHead>Arquivo</TableHead>
                      <TableHead>NF</TableHead>
                      <TableHead>CNPJ</TableHead>
                      <TableHead>Destinatario</TableHead>
                      <TableHead className="text-right">Valor</TableHead>
                      <TableHead>Emails</TableHead>
                      <TableHead>Status</TableHead>
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    {operacao.xmls.map((xml) => (
                      <TableRow key={xml.id}>
                        <TableCell className="max-w-[200px] truncate text-sm">
                          {xml.nome_arquivo}
                        </TableCell>
                        <TableCell className="font-[family-name:var(--font-barlow-condensed)]">
                          {xml.numero_nota}
                        </TableCell>
                        <TableCell className="text-sm">{xml.cnpj || "—"}</TableCell>
                        <TableCell className="max-w-[180px] truncate">
                          {xml.nome_destinatario || "—"}
                        </TableCell>
                        <TableCell className="text-right font-[family-name:var(--font-barlow-condensed)]">
                          {formatCurrency(xml.valor_total)}
                        </TableCell>
                        <TableCell className="max-w-[200px] truncate text-sm">
                          {xml.emails.length > 0 ? xml.emails.join(", ") : "—"}
                        </TableCell>
                        <TableCell>
                          {xml.xml_valido ? (
                            <Badge className="bg-success text-success-foreground">
                              Valido
                            </Badge>
                          ) : (
                            <Badge variant="destructive">Invalido</Badge>
                          )}
                        </TableCell>
                      </TableRow>
                    ))}
                  </TableBody>
                </Table>
                </div>
              )}
            </CardContent>
          </Card>
        </TabsContent>

        <TabsContent value="envio" className="mt-4 space-y-4">
          {/* Modo de envio + Botao */}
          {(isEmProcessamento || isConcluida) && operacao.total_aprovados > 0 && (
            <Card>
              <CardHeader>
                <CardTitle className="text-base">Enviar Boletos por Email</CardTitle>
              </CardHeader>
              <CardContent className="space-y-4">
                <div className="flex items-center gap-4">
                  <span className="text-sm font-medium">Modo:</span>
                  <div className="flex rounded-lg border overflow-hidden">
                    <button
                      type="button"
                      className={`flex items-center gap-2 px-4 py-2 text-sm transition-colors ${
                        envioMode === "preview"
                          ? "bg-primary text-primary-foreground"
                          : "hover:bg-muted"
                      }`}
                      onClick={() => setEnvioMode("preview")}
                    >
                      <Eye className="h-4 w-4" />
                      Preview (Rascunho)
                    </button>
                    <button
                      type="button"
                      className={`flex items-center gap-2 px-4 py-2 text-sm transition-colors ${
                        envioMode === "automatico"
                          ? "bg-primary text-primary-foreground"
                          : "hover:bg-muted"
                      }`}
                      onClick={() => setEnvioMode("automatico")}
                    >
                      <Send className="h-4 w-4" />
                      Automatico
                    </button>
                  </div>
                </div>

                <p className="text-sm text-muted-foreground">
                  {envioMode === "preview"
                    ? "Os emails serao criados como rascunhos no Outlook. Voce podera revisar e enviar manualmente."
                    : "Os emails serao enviados diretamente pelo Outlook sem revisao previa."}
                </p>

                <div className="flex items-center gap-3">
                  <Button
                    onClick={() => {
                      if (envioMode === "automatico") {
                        setConfirmDialog("envio_auto");
                      } else {
                        handleEnviar();
                      }
                    }}
                    disabled={envioLoading}
                    className="gap-2"
                  >
                    {envioLoading ? (
                      <Loader2 className="h-4 w-4 animate-spin" />
                    ) : envioMode === "preview" ? (
                      <Eye className="h-4 w-4" />
                    ) : (
                      <Send className="h-4 w-4" />
                    )}
                    {envioLoading
                      ? "Enviando..."
                      : envioMode === "preview"
                      ? "Criar Rascunhos"
                      : "Enviar Emails"}
                  </Button>
                  <span className="text-sm text-muted-foreground">
                    {operacao.total_aprovados} boleto(s) aprovado(s) para envio
                  </span>
                </div>
              </CardContent>
            </Card>
          )}

          {/* Resultado do envio recente */}
          {envioResult && (
            <Card>
              <CardHeader>
                <CardTitle className="text-base">Resultado do Envio</CardTitle>
              </CardHeader>
              <CardContent>
                <div className="flex gap-6 mb-4">
                  <div className="text-center">
                    <div className="text-2xl font-bold font-[family-name:var(--font-barlow-condensed)]">
                      {envioResult.emails_criados}
                    </div>
                    <div className="text-xs text-muted-foreground">Emails criados</div>
                  </div>
                  {envioResult.modo === "automatico" && (
                    <div className="text-center">
                      <div className="text-2xl font-bold font-[family-name:var(--font-barlow-condensed)] text-success">
                        {envioResult.emails_enviados}
                      </div>
                      <div className="text-xs text-muted-foreground">Enviados</div>
                    </div>
                  )}
                </div>
                <div className="overflow-x-auto">
                <Table>
                  <TableHeader>
                    <TableRow>
                      <TableHead>Destinatario</TableHead>
                      <TableHead>CC</TableHead>
                      <TableHead>Assunto</TableHead>
                      <TableHead className="text-center">Boletos</TableHead>
                      <TableHead className="text-center">XMLs</TableHead>
                      <TableHead>Status</TableHead>
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    {envioResult.detalhes.map((d, i) => (
                      <TableRow key={i}>
                        <TableCell className="text-sm max-w-[200px] truncate">
                          {d.email_para.join(", ")}
                        </TableCell>
                        <TableCell className="text-sm max-w-[150px] truncate">
                          {d.email_cc.length > 0 ? d.email_cc.join(", ") : "—"}
                        </TableCell>
                        <TableCell className="text-sm max-w-[200px] truncate">
                          {d.assunto}
                        </TableCell>
                        <TableCell className="text-center font-[family-name:var(--font-barlow-condensed)]">
                          {d.boletos_count}
                        </TableCell>
                        <TableCell className="text-center font-[family-name:var(--font-barlow-condensed)]">
                          {d.xmls_count}
                        </TableCell>
                        <TableCell>
                          {d.status === "enviado" && (
                            <Badge className="bg-success text-success-foreground">Enviado</Badge>
                          )}
                          {d.status === "rascunho" && (
                            <Badge className="bg-warning text-warning-foreground">Rascunho</Badge>
                          )}
                          {d.status === "erro" && (
                            <Badge variant="destructive">Erro</Badge>
                          )}
                          {!["enviado", "rascunho", "erro"].includes(d.status) && (
                            <Badge variant="outline">{d.status}</Badge>
                          )}
                        </TableCell>
                      </TableRow>
                    ))}
                  </TableBody>
                </Table>
                </div>
              </CardContent>
            </Card>
          )}

          {/* Historico de envios */}
          <Card>
            <CardHeader>
              <CardTitle className="text-base flex items-center gap-2">
                <Mail className="h-4 w-4" />
                Historico de Envios
              </CardTitle>
            </CardHeader>
            <CardContent>
              {enviosLoading ? (
                <p className="text-center text-muted-foreground py-4">Carregando...</p>
              ) : envios.length === 0 ? (
                <p className="text-center text-muted-foreground py-8">
                  Nenhum envio realizado ainda
                </p>
              ) : (
                <div className="overflow-x-auto">
                <Table>
                  <TableHeader>
                    <TableRow>
                      <TableHead>Data</TableHead>
                      <TableHead>Destinatario</TableHead>
                      <TableHead>Assunto</TableHead>
                      <TableHead>Modo</TableHead>
                      <TableHead>Status</TableHead>
                      <TableHead className="text-center">Anexos</TableHead>
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    {envios.map((envio) => (
                      <TableRow key={envio.id}>
                        <TableCell className="text-sm whitespace-nowrap">
                          {formatDate(envio.created_at)}
                        </TableCell>
                        <TableCell className="text-sm max-w-[200px] truncate">
                          {envio.email_para.join(", ")}
                        </TableCell>
                        <TableCell className="text-sm max-w-[200px] truncate">
                          {envio.assunto}
                        </TableCell>
                        <TableCell>
                          <Badge variant="outline">
                            {envio.modo === "preview" ? "Preview" : "Automatico"}
                          </Badge>
                        </TableCell>
                        <TableCell>
                          {envio.status === "enviado" && (
                            <Badge className="bg-success text-success-foreground">Enviado</Badge>
                          )}
                          {envio.status === "rascunho" && (
                            <Badge className="bg-warning text-warning-foreground">Rascunho</Badge>
                          )}
                          {envio.status === "erro" && (
                            <Badge variant="destructive" title={envio.erro_detalhes || ""}>
                              Erro
                            </Badge>
                          )}
                          {envio.status === "pendente" && (
                            <Badge variant="outline">Pendente</Badge>
                          )}
                        </TableCell>
                        <TableCell className="text-center font-[family-name:var(--font-barlow-condensed)]">
                          {envio.boletos_ids.length + envio.xmls_anexados.length}
                        </TableCell>
                      </TableRow>
                    ))}
                  </TableBody>
                </Table>
                </div>
              )}
            </CardContent>
          </Card>
        </TabsContent>
      </Tabs>

      {/* Confirmation Dialogs */}
      <Dialog open={confirmDialog === "finalizar"} onOpenChange={() => setConfirmDialog(null)}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Finalizar Operacao</DialogTitle>
            <DialogDescription>
              Ao finalizar, a operacao sera marcada como concluida e os relatorios serao gerados.
              Esta acao nao pode ser desfeita.
            </DialogDescription>
          </DialogHeader>
          <div className="flex justify-end gap-2 mt-4">
            <Button variant="outline" onClick={() => setConfirmDialog(null)}>
              Cancelar
            </Button>
            <Button onClick={handleFinalizar} disabled={actionLoading}>
              Confirmar Finalizacao
            </Button>
          </div>
        </DialogContent>
      </Dialog>

      <Dialog open={confirmDialog === "cancelar"} onOpenChange={() => setConfirmDialog(null)}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Cancelar Operacao</DialogTitle>
            <DialogDescription>
              Ao cancelar, a operacao sera marcada como cancelada e nao podera mais ser editada.
              Esta acao nao pode ser desfeita.
            </DialogDescription>
          </DialogHeader>
          <div className="flex justify-end gap-2 mt-4">
            <Button variant="outline" onClick={() => setConfirmDialog(null)}>
              Voltar
            </Button>
            <Button variant="destructive" onClick={handleCancelar} disabled={actionLoading}>
              Confirmar Cancelamento
            </Button>
          </div>
        </DialogContent>
      </Dialog>

      <Dialog open={confirmDialog === "envio_auto"} onOpenChange={() => setConfirmDialog(null)}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Envio Automatico</DialogTitle>
            <DialogDescription>
              Os emails serao enviados diretamente pelo Outlook sem revisao previa.
              Deseja enviar {operacao.total_aprovados} boleto(s) automaticamente?
            </DialogDescription>
          </DialogHeader>
          <div className="flex justify-end gap-2 mt-4">
            <Button variant="outline" onClick={() => setConfirmDialog(null)}>
              Cancelar
            </Button>
            <Button onClick={handleEnviar} disabled={envioLoading} className="gap-2">
              <Send className="h-4 w-4" />
              Confirmar Envio
            </Button>
          </div>
        </DialogContent>
      </Dialog>
    </div>
  );
}
