"use client";

import { Fragment, useEffect, useRef, useState } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import { apiFetch } from "@/lib/api";
import { Button } from "@/components/ui/button";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { Badge } from "@/components/ui/badge";
import { Progress } from "@/components/ui/progress";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { toast } from "sonner";
import {
  FileText,
  FileCode,
  Play,
  CheckCircle2,
  XCircle,
  AlertTriangle,
  Loader2,
  Lock,
  Mail,
  Send,
  Eye,
  RefreshCw,
  TrendingUp,
  ChevronDown,
  ChevronUp,
  ArrowLeft,
  Ban,
  CheckCheck,
  Download,
  Trash2,
  Pencil,
  Plus,
  ChevronRight,
  Maximize2,
} from "lucide-react";
import { Separator } from "@/components/ui/separator";
import { FileDropzone } from "@/components/file-dropzone";
import { useOperationTabs, type OperationTab } from "@/contexts/operation-tabs";

// -- Interfaces --

interface Fidc {
  id: string;
  nome: string;
  nome_completo: string;
  cor: string;
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

interface CamadaResult {
  camada: number;
  nome: string;
  aprovado: boolean;
  mensagem: string;
  bloqueia: boolean;
}

interface BoletoCompleto {
  id: string;
  arquivo_original: string;
  arquivo_renomeado: string | null;
  pagador: string | null;
  cnpj: string | null;
  numero_nota: string | null;
  vencimento: string | null;
  valor: number | null;
  valor_formatado: string | null;
  status: string;
  motivo_rejeicao: string | null;
  juros_detectado: boolean;
  validacao_camada1: CamadaResult | null;
  validacao_camada2: CamadaResult | null;
  validacao_camada3: CamadaResult | null;
  validacao_camada4: CamadaResult | null;
  validacao_camada5: CamadaResult | null;
}

interface ResultadoProcessamento {
  total: number;
  aprovados: number;
  rejeitados: number;
  taxa_sucesso: number;
  boletos: BoletoCompleto[];
}

interface OperacaoDetalhada {
  id: string;
  numero: string;
  fidc: { id: string; nome: string; cor: string };
  status: string;
  total_boletos: number;
  total_aprovados: number;
  total_rejeitados: number;
  taxa_sucesso: number;
  boletos: BoletoCompleto[];
  xmls: XmlResumo[];
  created_at: string;
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

interface PreviewEnvioGrupo {
  email_para: string[];
  email_cc: string[];
  assunto: string;
  boletos: BoletoCompleto[];
  xmls: XmlResumo[];
}

interface PreviewEnvioResponse {
  total_grupos: number;
  total_aprovados: number;
  grupos: PreviewEnvioGrupo[];
}

type Step = "config" | "upload" | "processamento" | "resultado";

// -- Page (wrapper) --

export default function NovaOperacaoPage() {
  const { tabs, activeTabId, addTab } = useOperationTabs();

  // Auto-create first tab if none exist
  useEffect(() => {
    if (tabs.length === 0) {
      addTab();
    }
  }, []);

  const activeTab = tabs.find((t) => t.tabId === activeTabId);

  return (
    <div className="space-y-3">
      {activeTab ? (
        <OperationEditor key={activeTab.tabId} tabId={activeTab.tabId} />
      ) : (
        <div className="py-16 text-center text-muted-foreground">
          Clique em + para abrir uma nova operação
        </div>
      )}
    </div>
  );
}

// -- Operation Editor (all existing logic) --

function OperationEditor({ tabId }: { tabId: string }) {
  const router = useRouter();
  const searchParams = useSearchParams();
  const { updateTab, removeTab, tabs } = useOperationTabs();
  const tab = tabs.find((t) => t.tabId === tabId)!;

  const [fidcs, setFidcs] = useState<Fidc[]>([]);
  const [selectedFidc, setSelectedFidc] = useState(tab.fidcId || "");
  const [numero, setNumero] = useState("");
  const [savedFidc, setSavedFidc] = useState(tab.fidcId || "");
  const [savedNumero, setSavedNumero] = useState("");
  const [saving, setSaving] = useState(false);
  const [operacaoId, setOperacaoId] = useState<string | null>(tab.operacaoId);
  const [operacaoNumero, setOperacaoNumero] = useState<string | null>(tab.operacaoNumero);
  const [step, setStep] = useState<Step>(tab.step || "config");
  const [addingToExisting, setAddingToExisting] = useState(false);
  const [restoring, setRestoring] = useState(false);
  const [lockedHover, setLockedHover] = useState(false);
  const [createBtnHover, setCreateBtnHover] = useState(false);
  const [justUnlocked, setJustUnlocked] = useState(false);
  const prevOperacaoId = useRef<string | null>(tab.operacaoId);

  useEffect(() => {
    if (operacaoId && !prevOperacaoId.current) {
      setJustUnlocked(true);
      const timer = setTimeout(() => setJustUnlocked(false), 800);
      return () => clearTimeout(timer);
    }
    prevOperacaoId.current = operacaoId;
  }, [operacaoId]);

  // Typewriter animation for title
  const titleTarget = addingToExisting
    ? "Adicionar Arquivos"
    : operacaoNumero ?? "Nova Operação";
  const [displayTitle, setDisplayTitle] = useState(titleTarget);
  const prevTarget = useRef(titleTarget);

  useEffect(() => {
    if (titleTarget === prevTarget.current) return;
    const oldText = prevTarget.current;
    prevTarget.current = titleTarget;

    let cancelled = false;
    const ERASE_MS = 30;
    const TYPE_MS = 50;

    async function animate() {
      for (let i = oldText.length; i >= 0; i--) {
        if (cancelled) return;
        setDisplayTitle(oldText.slice(0, i));
        await new Promise((r) => setTimeout(r, ERASE_MS));
      }
      for (let i = 0; i <= titleTarget.length; i++) {
        if (cancelled) return;
        setDisplayTitle(titleTarget.slice(0, i));
        await new Promise((r) => setTimeout(r, TYPE_MS));
      }
    }

    animate();
    return () => { cancelled = true; };
  }, [titleTarget]);

  // Upload state
  const [pdfFiles, setPdfFiles] = useState<File[]>([]);
  const [xmlFiles, setXmlFiles] = useState<File[]>([]);
  const [uploadedBoletos, setUploadedBoletos] = useState<BoletoCompleto[]>([]);
  const [uploadedXmls, setUploadedXmls] = useState<XmlResumo[]>([]);
  const [uploading, setUploading] = useState(false);

  // Processing state
  const [processing, setProcessing] = useState(false);
  const [resultado, setResultado] = useState<ResultadoProcessamento | null>(null);

  // Envio state
  const [envioMode, setEnvioMode] = useState<"preview" | "automatico">("preview");
  const [envioLoading, setEnvioLoading] = useState(false);
  const [envioResult, setEnvioResult] = useState<EnvioResultado | null>(null);
  const [envios, setEnvios] = useState<EnvioRecord[]>([]);
  const [enviosLoading, setEnviosLoading] = useState(false);
  const [verificarLoading, setVerificarLoading] = useState(false);
  const [marcarEnviadoId, setMarcarEnviadoId] = useState<string | null>(null);
  const [confirmEnvioAuto, setConfirmEnvioAuto] = useState(false);
  const [expandedBoleto, setExpandedBoleto] = useState<string | null>(null);
  const [actionLoading, setActionLoading] = useState(false);
  const [operacaoCreatedAt, setOperacaoCreatedAt] = useState<string | null>(null);
  const [confirmDialog, setConfirmDialog] = useState<"finalizar" | "cancelar" | "excluir" | null>(null);
  const [editingXmlId, setEditingXmlId] = useState<string | null>(null);
  const [editEmailsList, setEditEmailsList] = useState<string[]>([]);
  const [editEmailInput, setEditEmailInput] = useState("");
  const [savingEmails, setSavingEmails] = useState(false);

  // Document preview state
  const [expandedUploadBoleto, setExpandedUploadBoleto] = useState<string | null>(null);
  const [expandedUploadXml, setExpandedUploadXml] = useState<string | null>(null);
  const [previewModal, setPreviewModal] = useState<{ url: string; title: string } | null>(null);
  const [previewBlobUrls, setPreviewBlobUrls] = useState<Record<string, string>>({});

  // Processamento & envio preview state
  const [envioPreview, setEnvioPreview] = useState<PreviewEnvioResponse | null>(null);
  const [expandedEnvioGroup, setExpandedEnvioGroup] = useState<number | null>(null);
  const [expandedUploadNf, setExpandedUploadNf] = useState<string | null>(null);

  // Load FIDCs
  useEffect(() => {
    apiFetch<Fidc[]>("/fidcs").then(setFidcs).catch(() => toast.error("Erro ao carregar FIDCs"));
  }, []);

  // Detect query params for "add files to existing operation"
  useEffect(() => {
    const opId = searchParams.get("operacao_id");
    const fidcId = searchParams.get("fidc_id");
    if (opId && fidcId) {
      setOperacaoId(opId);
      setSelectedFidc(fidcId);
      setStep("upload");
      setAddingToExisting(true);
    }
  }, [searchParams]);

  // Restore state from API when re-mounting a tab with an existing operacaoId
  useEffect(() => {
    if (!tab.operacaoId || tab.step === "config") return;

    setRestoring(true);
    apiFetch<OperacaoDetalhada>(`/operacoes/${tab.operacaoId}`)
      .then((op) => {
        setOperacaoId(op.id);
        setOperacaoNumero(op.numero);
        setNumero(op.numero);
        setSelectedFidc(op.fidc.id);
        setSavedFidc(op.fidc.id);
        setSavedNumero(op.numero);
        setOperacaoCreatedAt(op.created_at);

        if (op.status === "em_processamento" || op.status === "concluida") {
          // Restore resultado from operation data
          setResultado({
            total: op.total_boletos,
            aprovados: op.total_aprovados,
            rejeitados: op.total_rejeitados,
            taxa_sucesso: op.taxa_sucesso,
            boletos: op.boletos,
          });
          // Carregar preview envio e historico
          apiFetch<PreviewEnvioResponse>(`/operacoes/${op.id}/preview-envio`)
            .then(setEnvioPreview)
            .catch(() => {});
          apiFetch<EnvioRecord[]>(`/operacoes/${op.id}/envios`)
            .then(setEnvios)
            .catch(() => {});
          // Determinar step
          if (tab.step === "resultado" && op.status === "concluida") {
            setStep("resultado");
          } else {
            setStep("processamento");
          }
        } else if (op.boletos.length > 0) {
          setStep("upload");
        } else {
          setStep("upload");
        }

        setUploadedXmls(op.xmls);
        setUploadedBoletos(op.boletos);
      })
      .catch(() => {
        toast.error("Erro ao restaurar operação");
        setStep("config");
      })
      .finally(() => setRestoring(false));
  }, []);

  // Sync step/operacao changes back to tab context
  function syncTab(updates: Partial<OperationTab>) {
    updateTab(tabId, updates);
  }

  // -- Step 1: Create operation --

  async function handleCreateOperation() {
    if (!selectedFidc) {
      toast.error("Selecione um FIDC");
      return;
    }

    try {
      const fidcObj = fidcs.find((f) => f.id === selectedFidc);
      const op = await apiFetch<{ id: string; numero: string }>("/operacoes", {
        method: "POST",
        body: JSON.stringify({
          fidc_id: selectedFidc,
          numero: numero || undefined,
        }),
      });
      setOperacaoId(op.id);
      setOperacaoNumero(op.numero);
      setSavedFidc(selectedFidc);
      setSavedNumero(op.numero);
      setNumero(op.numero);
      setOperacaoCreatedAt(new Date().toISOString());
      setStep("upload");
      syncTab({
        operacaoId: op.id,
        operacaoNumero: op.numero,
        step: "upload",
        fidcId: selectedFidc,
        fidcNome: fidcObj?.nome || "",
        fidcCor: fidcObj?.cor || "",
      });
      toast.success("Operação criada");
    } catch {
      toast.error("Erro ao criar operação");
    }
  }

  async function handleSaveChanges() {
    if (!operacaoId) return;
    setSaving(true);
    try {
      const fidcObj = fidcs.find((f) => f.id === selectedFidc);
      await apiFetch(`/operacoes/${operacaoId}`, {
        method: "PATCH",
        body: JSON.stringify({
          fidc_id: selectedFidc !== savedFidc ? selectedFidc : undefined,
          numero: numero !== savedNumero ? numero : undefined,
        }),
      });
      setSavedFidc(selectedFidc);
      setSavedNumero(numero);
      setOperacaoNumero(numero);
      syncTab({
        operacaoNumero: numero,
        fidcId: selectedFidc,
        fidcNome: fidcObj?.nome || "",
        fidcCor: fidcObj?.cor || "",
      });
      toast.success("Alterações salvas");
    } catch {
      toast.error("Erro ao salvar alterações");
    } finally {
      setSaving(false);
    }
  }

  // -- Step 2: Upload files --

  async function handleUpload() {
    if (!operacaoId) return;
    if (pdfFiles.length === 0) {
      toast.error("Selecione ao menos um boleto PDF");
      return;
    }

    setUploading(true);

    try {
      const pdfForm = new FormData();
      pdfFiles.forEach((f) => pdfForm.append("files", f));

      const token = localStorage.getItem("token");
      const pdfRes = await fetch(`/api/v1/operacoes/${operacaoId}/boletos/upload`, {
        method: "POST",
        headers: { Authorization: `Bearer ${token}` },
        body: pdfForm,
      });

      if (!pdfRes.ok) {
        const err = await pdfRes.json().catch(() => ({}));
        throw new Error(err.detail || "Erro ao enviar boletos");
      }

      const pdfData = await pdfRes.json();
      setUploadedBoletos(pdfData.boletos);
      toast.success(`${pdfData.boletos_criados} boleto(s) detectado(s)`);

      if (xmlFiles.length > 0) {
        const xmlForm = new FormData();
        xmlFiles.forEach((f) => xmlForm.append("files", f));

        const xmlRes = await fetch(`/api/v1/operacoes/${operacaoId}/xmls/upload`, {
          method: "POST",
          headers: { Authorization: `Bearer ${token}` },
          body: xmlForm,
        });

        if (!xmlRes.ok) {
          const err = await xmlRes.json().catch(() => ({}));
          throw new Error(err.detail || "Erro ao enviar XMLs");
        }

        const xmlData = await xmlRes.json();
        setUploadedXmls(xmlData.xmls);
        toast.success(`${xmlData.total_xmls} XML(s) carregado(s)`);
      }
    } catch (err) {
      toast.error(err instanceof Error ? err.message : "Erro no upload");
    } finally {
      setUploading(false);
    }
  }

  // -- Email editing --

  function startEditEmails(xml: XmlResumo) {
    setEditingXmlId(xml.id);
    setEditEmailsList([...xml.emails, ...xml.emails_invalidos]);
    setEditEmailInput("");
  }

  function addEmailToList() {
    const trimmed = editEmailInput.trim();
    if (trimmed && !editEmailsList.includes(trimmed)) {
      setEditEmailsList([...editEmailsList, trimmed]);
      setEditEmailInput("");
    }
  }

  function removeEmailFromList(email: string) {
    setEditEmailsList(editEmailsList.filter((e) => e !== email));
  }

  async function handleSaveEmails() {
    if (!operacaoId || !editingXmlId) return;
    setSavingEmails(true);
    try {
      const updated = await apiFetch<XmlResumo>(
        `/operacoes/${operacaoId}/xmls/${editingXmlId}/emails`,
        {
          method: "PATCH",
          body: JSON.stringify({ emails: editEmailsList }),
        }
      );
      setUploadedXmls((prev) =>
        prev.map((x) => (x.id === editingXmlId ? updated : x))
      );
      setEditingXmlId(null);
      toast.success("Emails atualizados");
    } catch {
      toast.error("Erro ao salvar emails");
    } finally {
      setSavingEmails(false);
    }
  }

  // -- Process --

  async function handleProcess() {
    if (!operacaoId) return;
    setProcessing(true);

    try {
      const result = await apiFetch<ResultadoProcessamento>(
        `/operacoes/${operacaoId}/processar`,
        { method: "POST" }
      );
      setResultado(result);
      toast.success(
        `Processamento concluido: ${result.aprovados} aprovados, ${result.rejeitados} rejeitados`
      );
      // Carregar preview de envio apos processar
      await fetchEnvioPreview();
    } catch {
      toast.error("Erro ao processar operacao");
    } finally {
      setProcessing(false);
    }
  }

  async function fetchEnvioPreview() {
    if (!operacaoId) return;
    try {
      const data = await apiFetch<PreviewEnvioResponse>(
        `/operacoes/${operacaoId}/preview-envio`
      );
      setEnvioPreview(data);
    } catch {
      // silently fail — preview is optional
    }
  }

  // -- Document preview --

  async function loadPreview(path: string, key: string) {
    if (previewBlobUrls[key]) return;
    const token = localStorage.getItem("token");
    try {
      const res = await fetch(`/api/v1${path}`, {
        headers: { Authorization: `Bearer ${token}` },
      });
      if (!res.ok) {
        toast.error(`Erro ao carregar preview: ${res.status}`);
        return;
      }
      const blob = await res.blob();
      const url = URL.createObjectURL(blob);
      setPreviewBlobUrls((prev) => ({ ...prev, [key]: url }));
    } catch (err) {
      toast.error("Erro ao carregar preview do documento");
      console.error("loadPreview error:", err);
    }
  }

  // -- Envio --

  function formatDate(dateStr: string) {
    return new Date(dateStr).toLocaleDateString("pt-BR", {
      day: "2-digit",
      month: "2-digit",
      year: "numeric",
      hour: "2-digit",
      minute: "2-digit",
    });
  }

  async function fetchEnvios() {
    if (!operacaoId) return;
    setEnviosLoading(true);
    try {
      const data = await apiFetch<EnvioRecord[]>(`/operacoes/${operacaoId}/envios`);
      setEnvios(data);
    } catch {
      // silencioso
    } finally {
      setEnviosLoading(false);
    }
  }

  async function handleEnviar() {
    if (!operacaoId) return;
    setEnvioLoading(true);
    setEnvioResult(null);
    try {
      const data = await apiFetch<EnvioResultado>(`/operacoes/${operacaoId}/enviar`, {
        method: "POST",
        body: JSON.stringify({ modo: envioMode }),
      });
      setEnvioResult(data);
      if (envioMode === "preview") {
        toast.success(`${data.emails_criados} rascunho(s) criado(s) no Outlook`);
      } else {
        toast.success(`${data.emails_enviados} email(s) enviado(s)`);
      }
      await fetchEnvios();
    } catch (err) {
      toast.error(err instanceof Error ? err.message : "Erro ao enviar");
    } finally {
      setEnvioLoading(false);
    }
  }

  async function handleVerificarStatus() {
    if (!operacaoId) return;
    setVerificarLoading(true);
    try {
      const data = await apiFetch<{ verificados: number; atualizados: number }>(
        `/operacoes/${operacaoId}/envios/verificar-status`,
        { method: "POST" }
      );
      if (data.atualizados > 0) {
        toast.success(`${data.atualizados} de ${data.verificados} envio(s) atualizado(s) para "enviado"`);
      } else {
        toast.info(`${data.verificados} rascunho(s) verificado(s), nenhum encontrado nos Itens Enviados`);
      }
      await fetchEnvios();
    } catch (err) {
      toast.error(err instanceof Error ? err.message : "Erro ao verificar status");
    } finally {
      setVerificarLoading(false);
    }
  }

  async function handleMarcarEnviado(envioId: string) {
    try {
      await apiFetch(`/operacoes/${operacaoId}/envios/${envioId}/status`, {
        method: "PATCH",
        body: JSON.stringify({ status: "enviado" }),
      });
      toast.success("Envio marcado como enviado");
      setMarcarEnviadoId(null);
      await fetchEnvios();
    } catch (err) {
      toast.error(err instanceof Error ? err.message : "Erro ao atualizar status");
    }
  }

  // -- Resultado (actions) --

  async function handleReprocessar() {
    if (!operacaoId) return;
    setActionLoading(true);
    try {
      const result = await apiFetch<ResultadoProcessamento>(
        `/operacoes/${operacaoId}/reprocessar`,
        { method: "POST" }
      );
      setResultado(result);
      toast.success(`Reprocessamento: ${result.aprovados} aprovados, ${result.rejeitados} rejeitados`);
    } catch {
      toast.error("Erro ao reprocessar");
    } finally {
      setActionLoading(false);
    }
  }

  async function handleFinalizar() {
    if (!operacaoId) return;
    setActionLoading(true);
    setConfirmDialog(null);
    try {
      await apiFetch(`/operacoes/${operacaoId}/finalizar`, { method: "POST" });
      toast.success("Operação finalizada");
      const op = await apiFetch<OperacaoDetalhada>(`/operacoes/${operacaoId}`);
      setResultado({
        total: op.total_boletos,
        aprovados: op.total_aprovados,
        rejeitados: op.total_rejeitados,
        taxa_sucesso: op.taxa_sucesso,
        boletos: op.boletos,
      });
      setUploadedXmls(op.xmls);
    } catch {
      toast.error("Erro ao finalizar");
    } finally {
      setActionLoading(false);
    }
  }

  async function handleCancelar() {
    if (!operacaoId) return;
    setActionLoading(true);
    setConfirmDialog(null);
    try {
      await apiFetch(`/operacoes/${operacaoId}/cancelar`, { method: "POST" });
      toast.success("Operação cancelada");
      removeTab(tabId);
      router.push("/historico");
    } catch {
      toast.error("Erro ao cancelar");
    } finally {
      setActionLoading(false);
    }
  }

  async function handleExcluir() {
    if (!operacaoId) return;
    setActionLoading(true);
    setConfirmDialog(null);
    try {
      await apiFetch(`/operacoes/${operacaoId}`, { method: "DELETE" });
      toast.success("Operação excluída");
      removeTab(tabId);
      router.push("/historico");
    } catch {
      toast.error("Erro ao excluir");
    } finally {
      setActionLoading(false);
    }
  }

  function handleDownload(tipo: string) {
    if (!operacaoId) return;
    const token = localStorage.getItem("token");
    window.open(
      `/api/v1/operacoes/${operacaoId}/relatorio?tipo=${tipo}&token=${token}`,
      "_blank"
    );
  }

  async function handleDownloadZip(tipo: "boletos" | "xmls" | "nfs") {
    if (!operacaoId) return;
    try {
      const token = localStorage.getItem("token");
      const res = await fetch(`/api/v1/operacoes/${operacaoId}/download-arquivos?tipo=${tipo}`, {
        headers: { Authorization: `Bearer ${token}` },
      });
      if (!res.ok) {
        const errData = await res.json().catch(() => null);
        throw new Error(errData?.detail || "Erro ao baixar");
      }
      const blob = await res.blob();
      if (blob.size === 0) throw new Error("Arquivo vazio");
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = res.headers.get("content-disposition")?.match(/filename="(.+)"/)?.[1] || `${tipo}.zip`;
      document.body.appendChild(a);
      a.click();
      setTimeout(() => { a.remove(); URL.revokeObjectURL(url); }, 1000);
    } catch (e) {
      toast.error(e instanceof Error ? e.message : "Erro ao baixar arquivos");
    }
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

  function ConfrontoBoletoNF({ boleto, xml }: { boleto: BoletoCompleto; xml: XmlResumo | null }) {
    if (!xml) {
      return <p className="text-sm text-muted-foreground py-2">Nenhuma nota fiscal vinculada a este boleto</p>;
    }

    type MatchStatus = "ok" | "divergente" | "parcial" | "n/a";
    const rows: { campo: string; bolVal: string; nfVal: string; match: MatchStatus }[] = [];

    // Numero NF
    const bNf = (boleto.numero_nota || "").replace(/^0+/, "") || "";
    const xNf = (xml.numero_nota || "").replace(/^0+/, "") || "";
    rows.push({ campo: "Numero NF", bolVal: boleto.numero_nota || "—", nfVal: xml.numero_nota || "—", match: bNf && xNf ? (bNf === xNf ? "ok" : "divergente") : "n/a" });

    // Valor
    const bVal = boleto.valor;
    const xVal = xml.valor_total;
    rows.push({
      campo: "Valor",
      bolVal: boleto.valor_formatado || "—",
      nfVal: xVal != null ? `R$ ${xVal.toLocaleString("pt-BR", { minimumFractionDigits: 2 })}` : "—",
      match: bVal != null && xVal != null ? (Math.abs(bVal - xVal) < 0.01 ? "ok" : "divergente") : "n/a",
    });

    // Nome
    const bNome = (boleto.pagador || "").toUpperCase().trim();
    const xNome = (xml.nome_destinatario || "").toUpperCase().trim();
    let nomeMatch: MatchStatus = "n/a";
    if (bNome && xNome) {
      if (bNome === xNome) nomeMatch = "ok";
      else if (bNome.includes(xNome) || xNome.includes(bNome)) nomeMatch = "parcial";
      else {
        const bWords = new Set(bNome.split(/\s+/).filter(w => w.length > 2));
        const xWords = new Set(xNome.split(/\s+/).filter(w => w.length > 2));
        let common = 0;
        for (const w of bWords) if (xWords.has(w)) common++;
        const total = Math.max(bWords.size, xWords.size);
        nomeMatch = total > 0 && common / total >= 0.5 ? "parcial" : "divergente";
      }
    }
    rows.push({ campo: "Nome", bolVal: boleto.pagador || "—", nfVal: xml.nome_destinatario || "—", match: nomeMatch });

    // CNPJ
    const bCnpj = (boleto.cnpj || "").replace(/\D/g, "");
    const xCnpj = (xml.cnpj || "").replace(/\D/g, "");
    rows.push({ campo: "CNPJ", bolVal: boleto.cnpj || "—", nfVal: xml.cnpj || "—", match: bCnpj && xCnpj ? (bCnpj === xCnpj ? "ok" : "divergente") : "n/a" });

    // Email
    rows.push({ campo: "Email", bolVal: "—", nfVal: xml.emails.length > 0 ? xml.emails.join(", ") : "—", match: xml.emails.length > 0 ? "ok" : "n/a" });

    return (
      <div className="rounded-lg bg-background p-4">
        <p className="text-sm font-semibold mb-3">Confronto: Boleto vs Nota Fiscal</p>
        <div className="overflow-x-auto">
          <table className="w-full text-sm border-collapse">
            <thead>
              <tr className="border-b">
                <th className="text-left py-2 pr-4 font-medium text-muted-foreground w-[120px]">Campo</th>
                <th className="text-left py-2 pr-4 font-medium">Boleto (extraido)</th>
                <th className="text-left py-2 pr-4 font-medium">Nota Fiscal (XML)</th>
                <th className="text-center py-2 font-medium w-[80px]">Status</th>
              </tr>
            </thead>
            <tbody>
              {rows.map((r) => (
                <tr key={r.campo} className="border-b last:border-0">
                  <td className="py-2 pr-4 font-medium text-muted-foreground">{r.campo}</td>
                  <td className="py-2 pr-4 font-[family-name:var(--font-barlow-condensed)]">{r.bolVal}</td>
                  <td className="py-2 pr-4 font-[family-name:var(--font-barlow-condensed)]">{r.nfVal}</td>
                  <td className="py-2 text-center">
                    {r.match === "ok" && <span className="inline-flex items-center gap-1 text-success"><CheckCircle2 className="h-4 w-4" /> OK</span>}
                    {r.match === "parcial" && <span className="inline-flex items-center gap-1 text-warning"><AlertTriangle className="h-4 w-4" /> Parcial</span>}
                    {r.match === "divergente" && <span className="inline-flex items-center gap-1 text-destructive"><XCircle className="h-4 w-4" /> Divergente</span>}
                    {r.match === "n/a" && <span className="text-muted-foreground text-xs">N/A</span>}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    );
  }

  // -- Render --

  if (restoring) {
    return (
      <div className="flex items-center justify-center py-16 gap-2">
        <Loader2 className="h-5 w-5 animate-spin text-muted-foreground" />
        <span className="text-muted-foreground">Restaurando operação...</span>
      </div>
    );
  }

  const selectedFidcObj = fidcs.find((f) => f.id === selectedFidc);
  const fidcDisplay = selectedFidcObj
    ? { nome: selectedFidcObj.nome, cor: selectedFidcObj.cor }
    : addingToExisting
    ? { nome: searchParams.get("fidc_nome") || "", cor: searchParams.get("fidc_cor") || "#999" }
    : tab.fidcNome
    ? { nome: tab.fidcNome, cor: tab.fidcCor }
    : null;

  return (
    <div className="space-y-6">
      <div>
        <div className="flex items-center gap-3">
          <h1 className="text-3xl font-bold">
            {displayTitle}
            <span className="animate-pulse text-primary">|</span>
          </h1>
          {operacaoId && (
            <Badge className="bg-warning text-warning-foreground hover:bg-warning/90">
              Em Processamento
            </Badge>
          )}
        </div>
        <p className="text-muted-foreground">
          {addingToExisting
            ? "Adicione mais boletos e notas fiscais a esta operação"
            : "Upload de boletos e XMLs para processamento"}
        </p>
      </div>

      {/* Steps indicator */}
      {!addingToExisting && (() => {
        const steps: { key: Step; label: string }[] = [
          { key: "config", label: "Configurar" },
          { key: "upload", label: "Upload" },
          { key: "processamento", label: "Processamento" },
          { key: "resultado", label: "Resultado" },
        ];
        const unlocked = !!operacaoId;
        const stepIdx = steps.findIndex((s) => s.key === step);
        // Max reachable step: config(0) → upload(1) → processamento(2) → resultado(3)
        const hasBoletos = uploadedBoletos.length > 0;
        const hasResultado = !!resultado;
        const maxStepIdx = !unlocked ? 0 : !hasBoletos ? 1 : !hasResultado ? 2 : steps.length - 1;

        return (
          <div className="flex items-center gap-3">
            {steps.map((s, i) => {
              const isActive = step === s.key;
              const isPast = i < stepIdx;
              const isBeyondMax = i > maxStepIdx;

              // Render locked group: stacked circles with lock icons
              // Triggers at the first step beyond maxStepIdx
              if (isBeyondMax) {
                if (i > maxStepIdx + 1) return null; // only render once
                const lockedSteps = steps.slice(maxStepIdx + 1);
                const tooltipMsg = !unlocked
                  ? "É necessário criar a operação para seguir para próximas etapas"
                  : "É necessário processar a operação para avançar";
                return (
                  <div
                    key="locked-group"
                    className="relative flex items-center gap-3"
                    onMouseEnter={() => setLockedHover(true)}
                    onMouseLeave={() => setLockedHover(false)}
                  >
                    <div className="h-px w-8 bg-border" />
                    <div className="flex items-center -space-x-2.5 cursor-not-allowed">
                      {lockedSteps.map((ls, li) => (
                        <div
                          key={ls.key}
                          className="flex h-8 w-8 shrink-0 items-center justify-center rounded-full bg-muted text-muted-foreground border-2 border-background"
                          style={{ zIndex: lockedSteps.length - li }}
                        >
                          <Lock className="h-3.5 w-3.5" />
                        </div>
                      ))}
                    </div>
                    <div
                      className={`absolute left-1/2 top-full z-50 mt-2 -translate-x-1/2 whitespace-nowrap rounded-md bg-popover px-3 py-1.5 text-xs text-popover-foreground shadow-md border transition-opacity duration-200 ${
                        lockedHover ? "opacity-100" : "opacity-0 pointer-events-none"
                      }`}
                    >
                      {tooltipMsg}
                    </div>
                  </div>
                );
              }

              // Reachable steps: clickable
              const canClick = unlocked && !isActive && i <= maxStepIdx;
              const unlockAnim = justUnlocked && i > 0;
              return (
                <div
                  key={s.key}
                  className={`flex items-center gap-3 ${unlockAnim ? "animate-step-unlock" : ""}`}
                  style={unlockAnim ? { animationDelay: `${(i - 1) * 150}ms` } : undefined}
                >
                  {i > 0 && <div className={`h-px w-8 bg-border ${unlockAnim ? "animate-step-unlock" : ""}`} style={unlockAnim ? { animationDelay: `${(i - 1) * 150}ms` } : undefined} />}
                  <button
                    type="button"
                    disabled={!canClick}
                    onClick={() => {
                      if (canClick) {
                        setStep(s.key);
                        syncTab({ step: s.key });
                      }
                    }}
                    className={`flex h-8 w-8 shrink-0 items-center justify-center rounded-full text-sm font-bold transition-colors ${
                      isActive
                        ? "bg-primary text-primary-foreground"
                        : isPast
                        ? "bg-primary/20 text-primary hover:bg-primary/30 cursor-pointer"
                        : "bg-muted text-muted-foreground hover:bg-muted/80 cursor-pointer"
                    }`}
                  >
                    {i + 1}
                  </button>
                  <span
                    className={`text-sm font-medium ${canClick ? "cursor-pointer hover:text-primary" : ""}`}
                    onClick={() => {
                      if (canClick) {
                        setStep(s.key);
                        syncTab({ step: s.key });
                      }
                    }}
                  >
                    {s.label}
                  </span>
                </div>
              );
            })}
          </div>
        );
      })()}

      {/* Step 1: Config */}
      {step === "config" && (
        <Card>
          <CardHeader>
            <CardTitle>Configurar Operação</CardTitle>
            <CardDescription>Selecione o FIDC e nomeie a operação</CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="space-y-2">
              <Label>FIDC</Label>
              <Select value={selectedFidc} onValueChange={setSelectedFidc}>
                <SelectTrigger
                  className={`transition-transform duration-300 ${!selectedFidc && createBtnHover ? "scale-[1.02] ring-2 ring-primary/40" : ""}`}
                >
                  <SelectValue placeholder="Selecione um FIDC" />
                </SelectTrigger>
                <SelectContent>
                  {fidcs.map((f) => (
                    <SelectItem key={f.id} value={f.id}>
                      <div className="flex items-center gap-2">
                        <span
                          className="inline-block h-3 w-3 rounded-full"
                          style={{ backgroundColor: f.cor }}
                        />
                        {f.nome}
                      </div>
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
            <div className="space-y-2">
              <Label>Número ou referência da operação (opcional)</Label>
              <Input
                value={numero}
                onChange={(e) => setNumero(e.target.value)}
                placeholder="Se vazio, gera automaticamente (OP-0001, OP-0002...)"
              />
            </div>
            {operacaoId ? (() => {
              const hasChanges = selectedFidc !== savedFidc || numero !== savedNumero;
              return (
                <Button
                  onClick={handleSaveChanges}
                  disabled={!hasChanges || saving}
                  className="transition-transform duration-300"
                >
                  {saving && <Loader2 className="mr-2 h-4 w-4 animate-spin" />}
                  Salvar Alterações
                </Button>
              );
            })() : (
              <div
                className="relative inline-block"
                onMouseEnter={() => { if (!selectedFidc) setCreateBtnHover(true); }}
                onMouseLeave={() => setCreateBtnHover(false)}
              >
                <Button
                  onClick={handleCreateOperation}
                  disabled={!selectedFidc}
                  className={`transition-transform duration-300 ${lockedHover ? "scale-105 ring-2 ring-primary/40" : ""}`}
                >
                  Criar Operação
                </Button>
                {/* Tooltip: selecione FIDC */}
                <div
                  className={`absolute left-1/2 bottom-full z-50 mb-2 -translate-x-1/2 whitespace-nowrap rounded-md bg-popover px-3 py-1.5 text-xs text-popover-foreground shadow-md border transition-opacity duration-200 ${
                    createBtnHover && !selectedFidc ? "opacity-100" : "opacity-0 pointer-events-none"
                  }`}
                >
                  Selecione uma FIDC
                </div>
              </div>
            )}
          </CardContent>
        </Card>
      )}

      {/* Step 2: Upload */}
      {step === "upload" && (
        <div className="space-y-4">
          {fidcDisplay && (
            <div className="flex items-center gap-2">
              <span
                className="inline-block h-3 w-3 rounded-full"
                style={{ backgroundColor: fidcDisplay.cor }}
              />
              <span className="font-medium">{fidcDisplay.nome}</span>
              <Badge variant="outline">
                {uploadedBoletos.length} boletos | {uploadedXmls.length} XMLs
              </Badge>
            </div>
          )}

          <Tabs defaultValue="boletos">
            <TabsList>
              <TabsTrigger value="boletos" className="gap-2">
                <FileText className="h-4 w-4" />
                Boletos PDF
              </TabsTrigger>
              <TabsTrigger value="xmls" className="gap-2">
                <FileCode className="h-4 w-4" />
                Notas Fiscais PDF
              </TabsTrigger>
            </TabsList>

            <TabsContent value="boletos">
              <Card>
                <CardContent className="pt-6">
                  <FileDropzone
                    accept=".pdf"
                    label="Arraste boletos PDF aqui"
                    icon="pdf"
                    files={pdfFiles}
                    onFilesChange={setPdfFiles}
                  />
                </CardContent>
              </Card>
            </TabsContent>

            <TabsContent value="xmls">
              <Card>
                <CardContent className="pt-6">
                  <FileDropzone
                    accept=".xml,.pdf"
                    label="Arraste Notas Fiscais (PDF ou XML) aqui"
                    icon="pdf"
                    files={xmlFiles}
                    onFilesChange={setXmlFiles}
                  />
                </CardContent>
              </Card>
            </TabsContent>
          </Tabs>

          {/* Uploaded XMLs preview table (only .xml files) */}
          {uploadedXmls.filter((x) => x.nome_arquivo.toLowerCase().endsWith(".xml")).length > 0 && (
            <Card>
              <CardHeader className="flex flex-row items-center justify-between">
                <CardTitle className="text-base">XMLs Parseados ({uploadedXmls.filter((x) => x.nome_arquivo.toLowerCase().endsWith(".xml")).length})</CardTitle>
                <Button variant="outline" size="sm" className="gap-2" onClick={() => handleDownloadZip("xmls")}>
                  <Download className="h-3.5 w-3.5" /> Baixar Todos os XMLs
                </Button>
              </CardHeader>
              <CardContent>
                <div className="overflow-x-auto">
                <Table>
                  <TableHeader>
                    <TableRow>
                      <TableHead className="w-8 px-2" />
                      <TableHead>Arquivo</TableHead>
                      <TableHead>NF</TableHead>
                      <TableHead className="text-right">Valor</TableHead>
                      <TableHead>Destinatário</TableHead>
                      <TableHead>CNPJ</TableHead>
                      <TableHead>Emails</TableHead>
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    {uploadedXmls.filter((x) => x.nome_arquivo.toLowerCase().endsWith(".xml")).map((xml) => (
                      <Fragment key={xml.id}>
                        <TableRow
                          className="cursor-pointer hover:bg-muted/50"
                          onClick={() => {
                            const isExpanding = expandedUploadXml !== xml.id;
                            setExpandedUploadXml(isExpanding ? xml.id : null);
                            if (isExpanding && operacaoId) {
                              loadPreview(`/operacoes/${operacaoId}/xmls/${xml.id}/arquivo`, `xml-${xml.id}`);
                            }
                          }}
                        >
                          <TableCell className="w-8 px-2">
                            {expandedUploadXml === xml.id
                              ? <ChevronDown className="h-4 w-4 text-muted-foreground" />
                              : <ChevronRight className="h-4 w-4 text-muted-foreground" />}
                          </TableCell>
                          <TableCell className="max-w-[200px] truncate text-sm" title={xml.nome_arquivo}>
                            {xml.nome_arquivo}
                          </TableCell>
                          <TableCell className="font-[family-name:var(--font-barlow-condensed)] font-semibold">
                            {xml.numero_nota}
                          </TableCell>
                          <TableCell className="text-right font-[family-name:var(--font-barlow-condensed)]">
                            {xml.valor_total
                              ? `R$ ${xml.valor_total.toLocaleString("pt-BR", { minimumFractionDigits: 2 })}`
                              : "—"}
                          </TableCell>
                          <TableCell>{xml.nome_destinatario || "—"}</TableCell>
                          <TableCell className="font-[family-name:var(--font-barlow-condensed)]">
                            {xml.cnpj || "—"}
                          </TableCell>
                          <TableCell onClick={(e) => e.stopPropagation()}>
                            {editingXmlId === xml.id ? (
                              <div className="space-y-2 min-w-[220px]">
                                <div className="flex flex-wrap gap-1">
                                  {editEmailsList.map((email) => (
                                    <span
                                      key={email}
                                      className="inline-flex items-center gap-1 rounded-md bg-muted px-2 py-0.5 text-xs"
                                    >
                                      {email}
                                      <button
                                        type="button"
                                        onClick={() => removeEmailFromList(email)}
                                        className="text-muted-foreground hover:text-destructive"
                                      >
                                        <XCircle className="h-3 w-3" />
                                      </button>
                                    </span>
                                  ))}
                                </div>
                                <div className="flex gap-1">
                                  <Input
                                    value={editEmailInput}
                                    onChange={(e) => setEditEmailInput(e.target.value)}
                                    onKeyDown={(e) => {
                                      if (e.key === "Enter") { e.preventDefault(); addEmailToList(); }
                                    }}
                                    placeholder="novo@email.com"
                                    className="h-7 text-xs"
                                  />
                                  <Button
                                    size="icon"
                                    variant="ghost"
                                    className="h-7 w-7 shrink-0"
                                    onClick={addEmailToList}
                                    disabled={!editEmailInput.trim()}
                                  >
                                    <Plus className="h-3.5 w-3.5" />
                                  </Button>
                                </div>
                                <div className="flex gap-1">
                                  <Button
                                    size="sm"
                                    className="h-7 text-xs"
                                    onClick={handleSaveEmails}
                                    disabled={savingEmails}
                                  >
                                    {savingEmails ? <Loader2 className="h-3 w-3 animate-spin mr-1" /> : null}
                                    Salvar
                                  </Button>
                                  <Button
                                    size="sm"
                                    variant="ghost"
                                    className="h-7 text-xs"
                                    onClick={() => setEditingXmlId(null)}
                                  >
                                    Cancelar
                                  </Button>
                                </div>
                              </div>
                            ) : (
                              <div className="flex items-center gap-1.5">
                                <div className="flex flex-col gap-0.5">
                                  {xml.emails.map((e) => (
                                    <span key={e} className="text-xs">{e}</span>
                                  ))}
                                  {xml.emails_invalidos.map((e) => (
                                    <span key={e} className="text-xs text-destructive line-through">{e}</span>
                                  ))}
                                  {xml.emails.length === 0 && xml.emails_invalidos.length === 0 && (
                                    <span className="text-xs text-muted-foreground">—</span>
                                  )}
                                </div>
                                <Button
                                  size="icon"
                                  variant="ghost"
                                  className="h-6 w-6 shrink-0"
                                  onClick={(e) => { e.stopPropagation(); startEditEmails(xml); }}
                                  title="Editar emails"
                                >
                                  <Pencil className="h-3 w-3" />
                                </Button>
                              </div>
                            )}
                          </TableCell>
                        </TableRow>
                        {expandedUploadXml === xml.id && (
                          <TableRow>
                            <TableCell colSpan={7} className="p-0">
                              <div className="bg-muted/30 p-4">
                                {previewBlobUrls[`xml-${xml.id}`] ? (
                                  <div className="space-y-2">
                                    <iframe
                                      src={previewBlobUrls[`xml-${xml.id}`]}
                                      className="w-full h-64 rounded border bg-white"
                                      title={xml.nome_arquivo}
                                    />
                                    <Button
                                      size="sm"
                                      variant="outline"
                                      className="gap-2"
                                      onClick={() => setPreviewModal({ url: previewBlobUrls[`xml-${xml.id}`], title: xml.nome_arquivo })}
                                    >
                                      <Maximize2 className="h-3.5 w-3.5" />
                                      Ampliar
                                    </Button>
                                  </div>
                                ) : (
                                  <div className="flex items-center justify-center h-32 text-muted-foreground">
                                    <Loader2 className="h-5 w-5 animate-spin mr-2" />
                                    Carregando preview...
                                  </div>
                                )}
                              </div>
                            </TableCell>
                          </TableRow>
                        )}
                      </Fragment>
                    ))}
                  </TableBody>
                </Table>
                </div>
              </CardContent>
            </Card>
          )}

          {/* Uploaded NF PDFs preview table */}
          {uploadedXmls.filter((x) => x.nome_arquivo.toLowerCase().endsWith(".pdf")).length > 0 && (() => {
            const nfPdfs = uploadedXmls.filter((x) => x.nome_arquivo.toLowerCase().endsWith(".pdf"));
            const boletaByNota = new Map(
              uploadedBoletos.map((b) => [(b.numero_nota || "").replace(/^0+/, "") || "0", b])
            );
            return (
              <Card>
                <CardHeader className="flex flex-row items-center justify-between">
                  <CardTitle className="text-base">Notas Fiscais ({nfPdfs.length})</CardTitle>
                  <Button variant="outline" size="sm" className="gap-2" onClick={() => handleDownloadZip("nfs")}>
                    <Download className="h-3.5 w-3.5" /> Baixar Todas as Notas Fiscais
                  </Button>
                </CardHeader>
                <CardContent>
                  <div className="overflow-x-auto">
                  <Table>
                    <TableHeader>
                      <TableRow>
                        <TableHead className="w-8 px-2" />
                        <TableHead>Arquivo</TableHead>
                        <TableHead>NF</TableHead>
                        <TableHead className="text-right">Valor</TableHead>
                        <TableHead>Vencimento</TableHead>
                        <TableHead>Destinatário</TableHead>
                      </TableRow>
                    </TableHeader>
                    <TableBody>
                      {nfPdfs.map((nf) => {
                        const nfKey = (nf.numero_nota || "").replace(/^0+/, "") || "0";
                        const boleto = boletaByNota.get(nfKey);
                        return (
                          <Fragment key={nf.id}>
                            <TableRow
                              className="cursor-pointer hover:bg-muted/50"
                              onClick={() => {
                                const isExpanding = expandedUploadNf !== nf.id;
                                setExpandedUploadNf(isExpanding ? nf.id : null);
                                if (isExpanding && operacaoId) {
                                  loadPreview(`/operacoes/${operacaoId}/xmls/${nf.id}/arquivo`, `xml-${nf.id}`);
                                }
                              }}
                            >
                              <TableCell className="w-8 px-2">
                                {expandedUploadNf === nf.id
                                  ? <ChevronDown className="h-4 w-4 text-muted-foreground" />
                                  : <ChevronRight className="h-4 w-4 text-muted-foreground" />}
                              </TableCell>
                              <TableCell className="max-w-[250px] truncate text-sm" title={nf.nome_arquivo}>
                                {nf.nome_arquivo}
                              </TableCell>
                              <TableCell className="font-[family-name:var(--font-barlow-condensed)] font-semibold">
                                {nf.numero_nota || "—"}
                              </TableCell>
                              <TableCell className="text-right font-[family-name:var(--font-barlow-condensed)]">
                                {boleto?.valor_formatado || "—"}
                              </TableCell>
                              <TableCell className="font-[family-name:var(--font-barlow-condensed)]">
                                {boleto?.vencimento || "—"}
                              </TableCell>
                              <TableCell className="max-w-[180px] truncate">
                                {boleto?.pagador || "—"}
                              </TableCell>
                            </TableRow>
                            {expandedUploadNf === nf.id && (
                              <TableRow>
                                <TableCell colSpan={6} className="p-0">
                                  <div className="bg-muted/30 p-4">
                                    {previewBlobUrls[`xml-${nf.id}`] ? (
                                      <div className="space-y-2">
                                        <iframe
                                          src={previewBlobUrls[`xml-${nf.id}`]}
                                          className="w-full h-64 rounded border bg-white"
                                          title={nf.nome_arquivo}
                                        />
                                        <Button
                                          size="sm"
                                          variant="outline"
                                          className="gap-2"
                                          onClick={(e) => {
                                            e.stopPropagation();
                                            setPreviewModal({ url: previewBlobUrls[`xml-${nf.id}`], title: nf.nome_arquivo });
                                          }}
                                        >
                                          <Maximize2 className="h-3.5 w-3.5" />
                                          Ampliar
                                        </Button>
                                      </div>
                                    ) : (
                                      <div className="flex items-center justify-center h-32 text-muted-foreground">
                                        <Loader2 className="h-5 w-5 animate-spin mr-2" />
                                        Carregando preview...
                                      </div>
                                    )}
                                  </div>
                                </TableCell>
                              </TableRow>
                            )}
                          </Fragment>
                        );
                      })}
                    </TableBody>
                  </Table>
                  </div>
                </CardContent>
              </Card>
            );
          })()}

          {/* Uploaded Boletos preview table */}
          {uploadedBoletos.length > 0 && (() => {
            const xmlByNota = new Map(
              uploadedXmls.map((x) => [x.numero_nota.replace(/^0+/, "") || "0", x])
            );
            return (
              <Card>
                <CardHeader className="flex flex-row items-center justify-between">
                  <CardTitle className="text-base">Boletos Carregados ({uploadedBoletos.length})</CardTitle>
                  <Button variant="outline" size="sm" className="gap-2" onClick={() => handleDownloadZip("boletos")}>
                    <Download className="h-3.5 w-3.5" /> Baixar Todos os Boletos
                  </Button>
                </CardHeader>
                <CardContent>
                  <div className="overflow-x-auto">
                  <Table>
                    <TableHeader>
                      <TableRow>
                        <TableHead className="w-8 px-2" />
                        <TableHead>Arquivo</TableHead>
                        <TableHead>NF</TableHead>
                        <TableHead className="text-right">Valor</TableHead>
                        <TableHead>Vencimento</TableHead>
                        <TableHead>Destinatario</TableHead>
                        <TableHead>Email</TableHead>
                      </TableRow>
                    </TableHeader>
                    <TableBody>
                      {uploadedBoletos.map((boleto) => {
                        const nfKey = (boleto.numero_nota || "").replace(/^0+/, "") || "0";
                        const xml = xmlByNota.get(nfKey);
                        return (
                          <Fragment key={boleto.id}>
                            <TableRow
                              className="cursor-pointer hover:bg-muted/50"
                              onClick={() => {
                                const isExpanding = expandedUploadBoleto !== boleto.id;
                                setExpandedUploadBoleto(isExpanding ? boleto.id : null);
                                if (isExpanding && operacaoId) {
                                  loadPreview(`/operacoes/${operacaoId}/boletos/${boleto.id}/arquivo`, `boleto-${boleto.id}`);
                                }
                              }}
                            >
                              <TableCell className="w-8 px-2">
                                {expandedUploadBoleto === boleto.id
                                  ? <ChevronDown className="h-4 w-4 text-muted-foreground" />
                                  : <ChevronRight className="h-4 w-4 text-muted-foreground" />}
                              </TableCell>
                              <TableCell className="max-w-[200px] truncate text-sm" title={boleto.arquivo_renomeado || boleto.arquivo_original}>
                                {boleto.arquivo_renomeado || boleto.arquivo_original}
                              </TableCell>
                              <TableCell className="font-[family-name:var(--font-barlow-condensed)] font-semibold">
                                {boleto.numero_nota || "—"}
                              </TableCell>
                              <TableCell className="text-right font-[family-name:var(--font-barlow-condensed)]">
                                {boleto.valor_formatado || "—"}
                              </TableCell>
                              <TableCell className="font-[family-name:var(--font-barlow-condensed)]">
                                {boleto.vencimento || "—"}
                              </TableCell>
                              <TableCell className="max-w-[180px] truncate">
                                {xml?.nome_destinatario || "—"}
                              </TableCell>
                              <TableCell className="max-w-[200px] truncate text-sm">
                                {xml && xml.emails.length > 0 ? xml.emails.join(", ") : "—"}
                              </TableCell>
                            </TableRow>
                            {expandedUploadBoleto === boleto.id && (
                              <TableRow>
                                <TableCell colSpan={7} className="p-0">
                                  <div className="bg-muted/30 p-4 space-y-4">
                                    {previewBlobUrls[`boleto-${boleto.id}`] ? (
                                      <div className="space-y-2">
                                        <iframe
                                          src={previewBlobUrls[`boleto-${boleto.id}`]}
                                          className="w-full h-64 rounded border bg-white"
                                          title={boleto.arquivo_renomeado || boleto.arquivo_original}
                                        />
                                        <Button
                                          size="sm"
                                          variant="outline"
                                          className="gap-2"
                                          onClick={(e) => {
                                            e.stopPropagation();
                                            setPreviewModal({
                                              url: previewBlobUrls[`boleto-${boleto.id}`],
                                              title: boleto.arquivo_renomeado || boleto.arquivo_original,
                                            });
                                          }}
                                        >
                                          <Maximize2 className="h-3.5 w-3.5" />
                                          Ampliar
                                        </Button>
                                      </div>
                                    ) : (
                                      <div className="flex items-center justify-center h-32 text-muted-foreground">
                                        <Loader2 className="h-5 w-5 animate-spin mr-2" />
                                        Carregando preview...
                                      </div>
                                    )}
                                    <ConfrontoBoletoNF boleto={boleto} xml={xml || null} />
                                  </div>
                                </TableCell>
                              </TableRow>
                            )}
                          </Fragment>
                        );
                      })}
                    </TableBody>
                  </Table>
                  </div>
                </CardContent>
              </Card>
            );
          })()}

          <div className="flex gap-3">
            <Button onClick={handleUpload} disabled={uploading || pdfFiles.length === 0}>
              {uploading && <Loader2 className="mr-2 h-4 w-4 animate-spin" />}
              {uploading ? "Salvando..." : "Salvar Upload"}
            </Button>

            {uploadedBoletos.length > 0 && !addingToExisting && (
              <Button
                className="gap-2"
                onClick={() => { setStep("processamento"); syncTab({ step: "processamento" }); }}
              >
                <Play className="h-4 w-4" />
                Continuar para Processamento
              </Button>
            )}

            {addingToExisting && (
              <Button
                variant="outline"
                onClick={() => { setStep("processamento"); syncTab({ step: "processamento" }); }}
              >
                Ver Processamento
              </Button>
            )}
          </div>
        </div>
      )}

      {/* Step 3: Processamento & Envio */}
      {step === "processamento" && operacaoId && (
        <div className="space-y-6">

          {/* Processar button (antes de processar) */}
          {!resultado && (
            <Card>
              <CardContent className="pt-6">
                <div className="flex flex-col items-center gap-4 py-8">
                  <div className="rounded-full bg-primary/10 p-4">
                    <Play className="h-8 w-8 text-primary" />
                  </div>
                  <div className="text-center space-y-1">
                    <h3 className="text-lg font-semibold">Pronto para Processar</h3>
                    <p className="text-sm text-muted-foreground">
                      {uploadedBoletos.length} boleto(s) e {uploadedXmls.length} XML(s) serao validados com as 5 camadas de verificacao
                    </p>
                  </div>
                  <Button onClick={handleProcess} disabled={processing} size="lg" className="gap-2">
                    {processing ? (
                      <Loader2 className="h-5 w-5 animate-spin" />
                    ) : (
                      <Play className="h-5 w-5" />
                    )}
                    {processing ? "Processando..." : "Processar Operacao"}
                  </Button>
                </div>
              </CardContent>
            </Card>
          )}

          {/* KPIs resumo (apos processar) */}
          {resultado && (() => {
            const valorTotal = resultado.boletos.reduce((acc, b) => {
              const raw = (b.valor_formatado || "").replace(/[^\d.,]/g, "").replace(".", "").replace(",", ".");
              return acc + (parseFloat(raw) || 0);
            }, 0);
            const qtdBoletos = uploadedBoletos.length;
            const qtdNfPdfs = uploadedXmls.filter((x) => x.nome_arquivo.toLowerCase().endsWith(".pdf")).length;
            const qtdXmls = uploadedXmls.filter((x) => x.nome_arquivo.toLowerCase().endsWith(".xml")).length;
            return (
              <>
                <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
                  <Card>
                    <CardContent className="pt-6">
                      <p className="text-sm text-muted-foreground">Valor Total</p>
                      <p className="text-2xl font-bold font-[family-name:var(--font-barlow-condensed)]">
                        R$ {valorTotal.toLocaleString("pt-BR", { minimumFractionDigits: 2, maximumFractionDigits: 2 })}
                      </p>
                    </CardContent>
                  </Card>
                  <Card>
                    <CardContent className="pt-6">
                      <p className="text-sm text-muted-foreground">Boletos</p>
                      <p className="text-2xl font-bold font-[family-name:var(--font-barlow-condensed)]">{qtdBoletos}</p>
                    </CardContent>
                  </Card>
                  <Card>
                    <CardContent className="pt-6">
                      <p className="text-sm text-muted-foreground">Notas Fiscais</p>
                      <p className="text-2xl font-bold font-[family-name:var(--font-barlow-condensed)]">{qtdNfPdfs}</p>
                    </CardContent>
                  </Card>
                  <Card>
                    <CardContent className="pt-6">
                      <p className="text-sm text-muted-foreground">XMLs</p>
                      <p className="text-2xl font-bold font-[family-name:var(--font-barlow-condensed)]">{qtdXmls}</p>
                    </CardContent>
                  </Card>
                </div>
                <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
                  <Card>
                    <CardContent className="pt-6">
                      <p className="text-sm text-muted-foreground">Total Processados</p>
                      <p className="text-2xl font-bold font-[family-name:var(--font-barlow-condensed)]">{resultado.total}</p>
                    </CardContent>
                  </Card>
                  <Card>
                    <CardContent className="pt-6">
                      <p className="text-sm text-muted-foreground">Aprovados</p>
                      <p className="text-2xl font-bold text-success font-[family-name:var(--font-barlow-condensed)]">{resultado.aprovados}</p>
                    </CardContent>
                  </Card>
                  <Card>
                    <CardContent className="pt-6">
                      <p className="text-sm text-muted-foreground">Rejeitados</p>
                      <p className="text-2xl font-bold text-destructive font-[family-name:var(--font-barlow-condensed)]">{resultado.rejeitados}</p>
                    </CardContent>
                  </Card>
                  <Card>
                    <CardContent className="pt-6">
                      <p className="text-sm text-muted-foreground">Taxa de Sucesso</p>
                      <p className="text-2xl font-bold font-[family-name:var(--font-barlow-condensed)]">{resultado.taxa_sucesso.toFixed(1)}%</p>
                    </CardContent>
                  </Card>
                </div>
                {resultado.total > 0 && (
                  <Progress value={resultado.taxa_sucesso} className="h-2" />
                )}
              </>
            );
          })()}

          {/* Email Groups preview */}
          {envioPreview && envioPreview.grupos.length > 0 && (
            <Card>
              <CardHeader>
                <CardTitle className="text-base flex items-center gap-2">
                  <Mail className="h-4 w-4" />
                  Emails para Envio ({envioPreview.total_grupos})
                </CardTitle>
                <CardDescription>
                  {envioPreview.total_aprovados} boleto(s) aprovado(s) agrupados em {envioPreview.total_grupos} email(s). Clique para ver os documentos anexados.
                </CardDescription>
              </CardHeader>
              <CardContent>
                <div className="overflow-x-auto">
                  <Table>
                    <TableHeader>
                      <TableRow>
                        <TableHead className="w-8 px-2" />
                        <TableHead>Destinatario</TableHead>
                        <TableHead>Assunto</TableHead>
                        <TableHead className="text-center">Boletos</TableHead>
                        <TableHead className="text-center">Notas</TableHead>
                        <TableHead className="text-center">Total Anexos</TableHead>
                      </TableRow>
                    </TableHeader>
                    <TableBody>
                      {envioPreview.grupos.map((grupo, idx) => (
                        <Fragment key={idx}>
                          <TableRow
                            className="cursor-pointer hover:bg-muted/50"
                            onClick={() => setExpandedEnvioGroup(expandedEnvioGroup === idx ? null : idx)}
                          >
                            <TableCell className="w-8 px-2">
                              {expandedEnvioGroup === idx
                                ? <ChevronDown className="h-4 w-4 text-muted-foreground" />
                                : <ChevronRight className="h-4 w-4 text-muted-foreground" />}
                            </TableCell>
                            <TableCell className="max-w-[250px]">
                              <div className="flex flex-col gap-0.5">
                                {grupo.email_para.map((e) => (
                                  <span key={e} className="text-sm">{e}</span>
                                ))}
                              </div>
                            </TableCell>
                            <TableCell className="max-w-[250px] truncate text-sm" title={grupo.assunto}>
                              {grupo.assunto}
                            </TableCell>
                            <TableCell className="text-center font-[family-name:var(--font-barlow-condensed)] font-semibold">
                              {grupo.boletos.length}
                            </TableCell>
                            <TableCell className="text-center font-[family-name:var(--font-barlow-condensed)] font-semibold">
                              {grupo.xmls.length}
                            </TableCell>
                            <TableCell className="text-center font-[family-name:var(--font-barlow-condensed)] font-semibold">
                              {grupo.boletos.length + grupo.xmls.length}
                            </TableCell>
                          </TableRow>
                          {expandedEnvioGroup === idx && (
                            <TableRow>
                              <TableCell colSpan={6} className="p-0">
                                <div className="bg-muted/30 p-4 space-y-4">
                                  {/* CC */}
                                  {grupo.email_cc.length > 0 && (
                                    <p className="text-xs text-muted-foreground">CC: {grupo.email_cc.join(", ")}</p>
                                  )}

                                  {/* Boletos do grupo */}
                                  {grupo.boletos.length > 0 && (
                                    <div>
                                      <p className="text-sm font-medium mb-2">Boletos ({grupo.boletos.length})</p>
                                      <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
                                        {grupo.boletos.map((boleto) => {
                                          const blobKey = `boleto-${boleto.id}`;
                                          const blobUrl = previewBlobUrls[blobKey];
                                          if (!blobUrl && operacaoId) {
                                            loadPreview(`/operacoes/${operacaoId}/boletos/${boleto.id}/arquivo`, blobKey);
                                          }
                                          return (
                                            <div
                                              key={boleto.id}
                                              className="border rounded-lg overflow-hidden bg-white cursor-pointer hover:ring-2 hover:ring-primary/50 transition-all"
                                              onClick={() => {
                                                if (blobUrl) setPreviewModal({ url: blobUrl, title: boleto.arquivo_renomeado || boleto.arquivo_original });
                                              }}
                                            >
                                              {blobUrl ? (
                                                <iframe src={blobUrl} className="w-full h-32 pointer-events-none" title={boleto.arquivo_original} />
                                              ) : (
                                                <div className="w-full h-32 flex items-center justify-center bg-muted/50">
                                                  <Loader2 className="h-4 w-4 animate-spin text-muted-foreground" />
                                                </div>
                                              )}
                                              <div className="p-2 border-t space-y-0.5">
                                                <p className="text-xs font-medium truncate" title={boleto.arquivo_renomeado || boleto.arquivo_original}>
                                                  {boleto.arquivo_renomeado || boleto.arquivo_original}
                                                </p>
                                                <div className="flex items-center justify-between text-xs text-muted-foreground">
                                                  <span>{boleto.vencimento || "—"}</span>
                                                  <span className="font-[family-name:var(--font-barlow-condensed)] font-semibold">{boleto.valor_formatado || "—"}</span>
                                                </div>
                                              </div>
                                            </div>
                                          );
                                        })}
                                      </div>
                                    </div>
                                  )}

                                  {/* XMLs/NFs do grupo */}
                                  {grupo.xmls.length > 0 && (
                                    <div>
                                      <p className="text-sm font-medium mb-2">Notas Fiscais ({grupo.xmls.length})</p>
                                      <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
                                        {grupo.xmls.map((xml) => {
                                          const blobKey = `xml-${xml.id}`;
                                          const blobUrl = previewBlobUrls[blobKey];
                                          if (!blobUrl && operacaoId) {
                                            loadPreview(`/operacoes/${operacaoId}/xmls/${xml.id}/arquivo`, blobKey);
                                          }
                                          return (
                                            <div
                                              key={xml.id}
                                              className="border rounded-lg overflow-hidden bg-white cursor-pointer hover:ring-2 hover:ring-primary/50 transition-all"
                                              onClick={() => {
                                                if (blobUrl) setPreviewModal({ url: blobUrl, title: xml.nome_arquivo });
                                              }}
                                            >
                                              {blobUrl ? (
                                                <iframe src={blobUrl} className="w-full h-32 pointer-events-none" title={xml.nome_arquivo} />
                                              ) : (
                                                <div className="w-full h-32 flex items-center justify-center bg-muted/50">
                                                  <Loader2 className="h-4 w-4 animate-spin text-muted-foreground" />
                                                </div>
                                              )}
                                              <div className="p-2 border-t space-y-0.5">
                                                <p className="text-xs font-medium truncate" title={xml.nome_arquivo}>
                                                  NF {xml.numero_nota}
                                                </p>
                                                <p className="text-xs text-muted-foreground truncate">
                                                  {xml.nome_destinatario || "—"}
                                                </p>
                                              </div>
                                            </div>
                                          );
                                        })}
                                      </div>
                                    </div>
                                  )}

                                  {/* Confronto por boleto */}
                                  {grupo.boletos.length > 0 && (
                                    <div>
                                      <p className="text-sm font-medium mb-2">Confronto Boleto vs Nota Fiscal</p>
                                      <div className="space-y-3">
                                        {grupo.boletos.map((boleto) => {
                                          const nfKey = (boleto.numero_nota || "").replace(/^0+/, "") || "0";
                                          const xmlMatch = grupo.xmls.find(x => ((x.numero_nota || "").replace(/^0+/, "") || "0") === nfKey) || null;
                                          return (
                                            <div key={`confronto-${boleto.id}`} className="border rounded-lg p-3 bg-background">
                                              <p className="text-xs font-medium mb-2 truncate" title={boleto.arquivo_renomeado || boleto.arquivo_original}>
                                                {boleto.arquivo_renomeado || boleto.arquivo_original}
                                              </p>
                                              <ConfrontoBoletoNF boleto={boleto} xml={xmlMatch} />
                                            </div>
                                          );
                                        })}
                                      </div>
                                    </div>
                                  )}
                                </div>
                              </TableCell>
                            </TableRow>
                          )}
                        </Fragment>
                      ))}
                    </TableBody>
                  </Table>
                </div>
              </CardContent>
            </Card>
          )}

          {/* Controles de envio */}
          {resultado && resultado.aprovados > 0 && (
            <Card>
              <CardHeader>
                <CardTitle className="text-base">Enviar Boletos por Email</CardTitle>
              </CardHeader>
              <CardContent className="space-y-4">
                <div className="flex items-center gap-4">
                  <span className="text-sm font-medium">Modo:</span>
                  <div className="flex rounded-lg border overflow-hidden">
                    <button type="button" className={`flex items-center gap-2 px-4 py-2 text-sm transition-colors ${envioMode === "preview" ? "bg-primary text-primary-foreground" : "hover:bg-muted"}`} onClick={() => setEnvioMode("preview")}>
                      <Eye className="h-4 w-4" /> Preview (Rascunho)
                    </button>
                    <button type="button" className={`flex items-center gap-2 px-4 py-2 text-sm transition-colors ${envioMode === "automatico" ? "bg-primary text-primary-foreground" : "hover:bg-muted"}`} onClick={() => setEnvioMode("automatico")}>
                      <Send className="h-4 w-4" /> Automatico
                    </button>
                  </div>
                </div>
                <p className="text-sm text-muted-foreground">
                  {envioMode === "preview" ? "Os emails serao criados como rascunhos no Outlook." : "Os emails serao enviados diretamente pelo Outlook."}
                </p>
                <div className="flex items-center gap-3">
                  <Button onClick={() => { if (envioMode === "automatico") { setConfirmEnvioAuto(true); } else { handleEnviar(); } }} disabled={envioLoading} className="gap-2">
                    {envioLoading ? <Loader2 className="h-4 w-4 animate-spin" /> : envioMode === "preview" ? <Eye className="h-4 w-4" /> : <Send className="h-4 w-4" />}
                    {envioLoading ? "Enviando..." : envioMode === "preview" ? "Criar Rascunhos" : "Enviar Emails"}
                  </Button>
                  <span className="text-sm text-muted-foreground">{resultado.aprovados} boleto(s) aprovado(s) para envio</span>
                </div>
              </CardContent>
            </Card>
          )}

          {/* Botao para ver resultado detalhado */}
          {resultado && (
            <div className="flex justify-end">
              <Button
                variant="outline"
                className="gap-2"
                onClick={() => { setStep("resultado"); syncTab({ step: "resultado" }); }}
              >
                <TrendingUp className="h-4 w-4" />
                Ver Resultado Detalhado
              </Button>
            </div>
          )}
        </div>
      )}

      {/* Step 4: Resultado */}
      {step === "resultado" && operacaoId && resultado && (
        <div className="space-y-6">
          {/* Action bar: date + buttons */}
          <div className="flex items-center justify-between">
            <div className="text-sm text-muted-foreground">
              {operacaoCreatedAt && (
                <span>Criada em {formatDate(operacaoCreatedAt)}</span>
              )}
            </div>
            <div className="flex items-center gap-2">
              {resultado.rejeitados > 0 && (
                <Button
                  variant="outline"
                  onClick={handleReprocessar}
                  disabled={actionLoading}
                  className="gap-2"
                >
                  <RefreshCw className="h-4 w-4" />
                  Reprocessar
                </Button>
              )}
              <Button
                size="icon"
                onClick={() => setConfirmDialog("finalizar")}
                disabled={actionLoading}
                title="Finalizar — Marca a operação como concluída e gera relatórios"
              >
                <CheckCheck className="h-4 w-4" />
              </Button>
              <Button
                size="icon"
                variant="outline"
                onClick={() => setConfirmDialog("cancelar")}
                disabled={actionLoading}
                className="border-warning text-warning hover:bg-warning/10 hover:text-warning"
                title="Cancelar — Marca a operação como cancelada (irreversível)"
              >
                <Ban className="h-4 w-4" />
              </Button>
              <Button
                size="icon"
                variant="outline"
                onClick={() => setConfirmDialog("excluir")}
                disabled={actionLoading}
                className="border-destructive text-destructive hover:bg-destructive/10 hover:text-destructive"
                title="Excluir — Remove permanentemente a operação e todos os dados"
              >
                <Trash2 className="h-4 w-4" />
              </Button>
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
                  {resultado.total}
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
                  {resultado.aprovados}
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
                  {resultado.rejeitados}
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
                  {resultado.taxa_sucesso.toFixed(1)}%
                </div>
              </CardContent>
            </Card>
          </div>

          {/* Progress bar */}
          {resultado.total > 0 && (
            <Progress value={resultado.taxa_sucesso} className="h-2" />
          )}

          {/* Tabs: Boletos | XMLs | Envio */}
          <Tabs defaultValue="boletos">
            <TabsList>
              <TabsTrigger value="boletos">Boletos ({resultado.boletos.length})</TabsTrigger>
              <TabsTrigger value="xmls">XMLs ({uploadedXmls.filter((x) => x.nome_arquivo.toLowerCase().endsWith(".xml")).length})</TabsTrigger>
              <TabsTrigger value="nfs">Notas Fiscais ({uploadedXmls.filter((x) => x.nome_arquivo.toLowerCase().endsWith(".pdf")).length})</TabsTrigger>
              <TabsTrigger value="envio" onClick={() => fetchEnvios()}>Envio ({envios.length})</TabsTrigger>
            </TabsList>

            {/* Boletos tab with expandable validation + preview */}
            <TabsContent value="boletos" className="mt-4">
              <Card>
                <CardHeader className="flex flex-row items-center justify-between">
                  <CardTitle className="text-base">Boletos ({resultado.boletos.length})</CardTitle>
                  {resultado.boletos.length > 0 && (
                    <Button variant="outline" size="sm" className="gap-2" onClick={() => handleDownloadZip("boletos")}>
                      <Download className="h-3.5 w-3.5" /> Baixar Todos os Boletos
                    </Button>
                  )}
                </CardHeader>
                <CardContent>
                  {resultado.boletos.length === 0 ? (
                    <p className="text-center text-muted-foreground py-8">
                      Nenhum boleto nesta operacao
                    </p>
                  ) : (() => {
                    const xmlByNota = new Map(
                      uploadedXmls.filter((x) => x.nome_arquivo.toLowerCase().endsWith(".xml")).map((x) => [(x.numero_nota || "").replace(/^0+/, "") || "0", x])
                    );
                    return (
                    <div className="overflow-x-auto">
                    <Table>
                      <TableHeader>
                        <TableRow>
                          <TableHead className="w-8 px-2" />
                          <TableHead>Status</TableHead>
                          <TableHead>Arquivo</TableHead>
                          <TableHead>NF</TableHead>
                          <TableHead className="text-right">Valor</TableHead>
                          <TableHead>Vencimento</TableHead>
                          <TableHead>Destinatário</TableHead>
                          <TableHead>Email</TableHead>
                          <TableHead>Motivo</TableHead>
                        </TableRow>
                      </TableHeader>
                      <TableBody>
                        {resultado.boletos.map((boleto) => {
                          const nfKey = (boleto.numero_nota || "").replace(/^0+/, "") || "0";
                          const xml = xmlByNota.get(nfKey);
                          return (
                          <Fragment key={boleto.id}>
                            <TableRow
                              className="cursor-pointer hover:bg-muted/50"
                              onClick={() =>
                                setExpandedBoleto(
                                  expandedBoleto === boleto.id ? null : boleto.id
                                )
                              }
                            >
                              <TableCell className="w-8 px-2">
                                {expandedBoleto === boleto.id ? (
                                  <ChevronDown className="h-4 w-4 text-muted-foreground" />
                                ) : (
                                  <ChevronRight className="h-4 w-4 text-muted-foreground" />
                                )}
                              </TableCell>
                              <TableCell>
                                <div className="flex items-center gap-1.5">
                                  {boleto.status === "aprovado" ? (
                                    <Badge className="bg-success text-success-foreground">Aprovado</Badge>
                                  ) : (
                                    <Badge variant="destructive">Rejeitado</Badge>
                                  )}
                                  {boleto.juros_detectado && (
                                    <Badge className="bg-warning text-warning-foreground text-xs">Juros</Badge>
                                  )}
                                </div>
                              </TableCell>
                              <TableCell className="max-w-[200px] truncate text-sm" title={boleto.arquivo_renomeado || boleto.arquivo_original}>
                                {boleto.arquivo_renomeado || boleto.arquivo_original}
                              </TableCell>
                              <TableCell className="font-[family-name:var(--font-barlow-condensed)] font-semibold">{boleto.numero_nota || "—"}</TableCell>
                              <TableCell className="text-right font-[family-name:var(--font-barlow-condensed)]">
                                {boleto.valor_formatado || "—"}
                              </TableCell>
                              <TableCell className="font-[family-name:var(--font-barlow-condensed)]">{boleto.vencimento || "—"}</TableCell>
                              <TableCell className="max-w-[180px] truncate">
                                {xml?.nome_destinatario || "—"}
                              </TableCell>
                              <TableCell className="max-w-[200px] truncate text-sm">
                                {xml && xml.emails.length > 0 ? xml.emails.join(", ") : "—"}
                              </TableCell>
                              <TableCell className="max-w-[200px] truncate text-sm text-destructive">
                                {boleto.motivo_rejeicao || ""}
                              </TableCell>
                            </TableRow>

                            {/* Expanded: 5 camadas + preview PDF */}
                            {expandedBoleto === boleto.id && (() => {
                              const blobKey = `boleto-${boleto.id}`;
                              if (!previewBlobUrls[blobKey] && operacaoId) {
                                loadPreview(`/operacoes/${operacaoId}/boletos/${boleto.id}/arquivo`, blobKey);
                              }
                              return (
                              <TableRow>
                                <TableCell colSpan={9} className="p-0">
                                  <div className="bg-muted/30 p-4 space-y-4">
                                    {/* Preview PDF */}
                                    {previewBlobUrls[blobKey] ? (
                                      <div className="space-y-2">
                                        <iframe
                                          src={previewBlobUrls[blobKey]}
                                          className="w-full h-64 rounded border bg-white"
                                          title={boleto.arquivo_renomeado || boleto.arquivo_original}
                                        />
                                        <Button
                                          size="sm"
                                          variant="outline"
                                          className="gap-2"
                                          onClick={(e) => { e.stopPropagation(); setPreviewModal({ url: previewBlobUrls[blobKey], title: boleto.arquivo_renomeado || boleto.arquivo_original }); }}
                                        >
                                          <Maximize2 className="h-3.5 w-3.5" />
                                          Ampliar
                                        </Button>
                                      </div>
                                    ) : (
                                      <div className="flex items-center justify-center h-32 text-muted-foreground">
                                        <Loader2 className="h-5 w-5 animate-spin mr-2" />
                                        Carregando preview...
                                      </div>
                                    )}
                                    {/* Confronto Boleto vs NF */}
                                    <ConfrontoBoletoNF boleto={boleto} xml={xml ?? null} />
                                    {/* 5 Camadas */}
                                    <div className="rounded-lg bg-background p-4 space-y-2">
                                      <p className="text-sm font-semibold mb-3">Validacao em 5 Camadas</p>
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
                                  </div>
                                </TableCell>
                              </TableRow>
                              );
                            })()}
                          </Fragment>
                          );
                        })}
                      </TableBody>
                    </Table>
                    </div>
                    );
                  })()}
                </CardContent>
              </Card>
            </TabsContent>

            {/* XMLs tab (only .xml files) */}
            <TabsContent value="xmls" className="mt-4">
              <Card>
                <CardHeader className="flex flex-row items-center justify-between">
                  <CardTitle className="text-base">XMLs ({uploadedXmls.filter((x) => x.nome_arquivo.toLowerCase().endsWith(".xml")).length})</CardTitle>
                  {uploadedXmls.filter((x) => x.nome_arquivo.toLowerCase().endsWith(".xml")).length > 0 && (
                    <Button variant="outline" size="sm" className="gap-2" onClick={() => handleDownloadZip("xmls")}>
                      <Download className="h-3.5 w-3.5" /> Baixar Todos os XMLs
                    </Button>
                  )}
                </CardHeader>
                <CardContent>
                  {uploadedXmls.filter((x) => x.nome_arquivo.toLowerCase().endsWith(".xml")).length === 0 ? (
                    <p className="text-center text-muted-foreground py-8">Nenhum XML nesta operacao</p>
                  ) : (
                    <div className="overflow-x-auto">
                    <Table>
                      <TableHeader>
                        <TableRow>
                          <TableHead className="w-8 px-2" />
                          <TableHead>Arquivo</TableHead>
                          <TableHead>NF</TableHead>
                          <TableHead className="text-right">Valor</TableHead>
                          <TableHead>Destinatário</TableHead>
                          <TableHead>CNPJ</TableHead>
                          <TableHead>Emails</TableHead>
                        </TableRow>
                      </TableHeader>
                      <TableBody>
                        {uploadedXmls.filter((x) => x.nome_arquivo.toLowerCase().endsWith(".xml")).map((xml) => (
                          <Fragment key={xml.id}>
                            <TableRow
                              className="cursor-pointer hover:bg-muted/50"
                              onClick={() => {
                                const isExpanding = expandedUploadXml !== xml.id;
                                setExpandedUploadXml(isExpanding ? xml.id : null);
                                if (isExpanding && operacaoId) {
                                  loadPreview(`/operacoes/${operacaoId}/xmls/${xml.id}/arquivo`, `xml-${xml.id}`);
                                }
                              }}
                            >
                              <TableCell className="w-8 px-2">
                                {expandedUploadXml === xml.id
                                  ? <ChevronDown className="h-4 w-4 text-muted-foreground" />
                                  : <ChevronRight className="h-4 w-4 text-muted-foreground" />}
                              </TableCell>
                              <TableCell className="max-w-[200px] truncate text-sm" title={xml.nome_arquivo}>
                                {xml.nome_arquivo}
                              </TableCell>
                              <TableCell className="font-[family-name:var(--font-barlow-condensed)] font-semibold">
                                {xml.numero_nota}
                              </TableCell>
                              <TableCell className="text-right font-[family-name:var(--font-barlow-condensed)]">
                                {xml.valor_total != null ? `R$ ${xml.valor_total.toLocaleString("pt-BR", { minimumFractionDigits: 2 })}` : "—"}
                              </TableCell>
                              <TableCell className="max-w-[180px] truncate">{xml.nome_destinatario || "—"}</TableCell>
                              <TableCell className="font-[family-name:var(--font-barlow-condensed)]">{xml.cnpj || "—"}</TableCell>
                              <TableCell className="max-w-[200px] truncate text-sm">
                                {xml.emails.length > 0 ? xml.emails.join(", ") : "—"}
                              </TableCell>
                            </TableRow>
                            {expandedUploadXml === xml.id && (
                              <TableRow>
                                <TableCell colSpan={7} className="p-0">
                                  <div className="bg-muted/30 p-4">
                                    {previewBlobUrls[`xml-${xml.id}`] ? (
                                      <div className="space-y-2">
                                        <iframe
                                          src={previewBlobUrls[`xml-${xml.id}`]}
                                          className="w-full h-64 rounded border bg-white"
                                          title={xml.nome_arquivo}
                                        />
                                        <Button
                                          size="sm"
                                          variant="outline"
                                          className="gap-2"
                                          onClick={(e) => { e.stopPropagation(); setPreviewModal({ url: previewBlobUrls[`xml-${xml.id}`], title: xml.nome_arquivo }); }}
                                        >
                                          <Maximize2 className="h-3.5 w-3.5" />
                                          Ampliar
                                        </Button>
                                      </div>
                                    ) : (
                                      <div className="flex items-center justify-center h-32 text-muted-foreground">
                                        <Loader2 className="h-5 w-5 animate-spin mr-2" />
                                        Carregando preview...
                                      </div>
                                    )}
                                  </div>
                                </TableCell>
                              </TableRow>
                            )}
                          </Fragment>
                        ))}
                      </TableBody>
                    </Table>
                    </div>
                  )}
                </CardContent>
              </Card>
            </TabsContent>

            {/* Notas Fiscais PDF tab */}
            <TabsContent value="nfs" className="mt-4">
              <Card>
                <CardHeader className="flex flex-row items-center justify-between">
                  <CardTitle className="text-base">Notas Fiscais ({uploadedXmls.filter((x) => x.nome_arquivo.toLowerCase().endsWith(".pdf")).length})</CardTitle>
                  {uploadedXmls.filter((x) => x.nome_arquivo.toLowerCase().endsWith(".pdf")).length > 0 && (
                    <Button variant="outline" size="sm" className="gap-2" onClick={() => handleDownloadZip("nfs")}>
                      <Download className="h-3.5 w-3.5" /> Baixar Todas as Notas Fiscais
                    </Button>
                  )}
                </CardHeader>
                <CardContent>
                  {uploadedXmls.filter((x) => x.nome_arquivo.toLowerCase().endsWith(".pdf")).length === 0 ? (
                    <p className="text-center text-muted-foreground py-8">Nenhuma nota fiscal em PDF nesta operacao</p>
                  ) : (() => {
                    const nfPdfs = uploadedXmls.filter((x) => x.nome_arquivo.toLowerCase().endsWith(".pdf"));
                    const boletaByNota = new Map(
                      uploadedBoletos.map((b) => [(b.numero_nota || "").replace(/^0+/, "") || "0", b])
                    );
                    return (
                      <div className="overflow-x-auto">
                      <Table>
                        <TableHeader>
                          <TableRow>
                            <TableHead className="w-8 px-2" />
                            <TableHead>Arquivo</TableHead>
                            <TableHead>NF</TableHead>
                            <TableHead className="text-right">Valor</TableHead>
                            <TableHead>Vencimento</TableHead>
                            <TableHead>Destinatário</TableHead>
                          </TableRow>
                        </TableHeader>
                        <TableBody>
                          {nfPdfs.map((nf) => {
                            const nfKey = (nf.numero_nota || "").replace(/^0+/, "") || "0";
                            const boleto = boletaByNota.get(nfKey);
                            return (
                              <Fragment key={nf.id}>
                                <TableRow
                                  className="cursor-pointer hover:bg-muted/50"
                                  onClick={() => {
                                    const isExpanding = expandedUploadNf !== nf.id;
                                    setExpandedUploadNf(isExpanding ? nf.id : null);
                                    if (isExpanding && operacaoId) {
                                      loadPreview(`/operacoes/${operacaoId}/xmls/${nf.id}/arquivo`, `xml-${nf.id}`);
                                    }
                                  }}
                                >
                                  <TableCell className="w-8 px-2">
                                    {expandedUploadNf === nf.id
                                      ? <ChevronDown className="h-4 w-4 text-muted-foreground" />
                                      : <ChevronRight className="h-4 w-4 text-muted-foreground" />}
                                  </TableCell>
                                  <TableCell className="max-w-[250px] truncate text-sm" title={nf.nome_arquivo}>
                                    {nf.nome_arquivo}
                                  </TableCell>
                                  <TableCell className="font-[family-name:var(--font-barlow-condensed)] font-semibold">
                                    {nf.numero_nota || "—"}
                                  </TableCell>
                                  <TableCell className="text-right font-[family-name:var(--font-barlow-condensed)]">
                                    {boleto?.valor_formatado || "—"}
                                  </TableCell>
                                  <TableCell className="font-[family-name:var(--font-barlow-condensed)]">
                                    {boleto?.vencimento || "—"}
                                  </TableCell>
                                  <TableCell className="max-w-[180px] truncate">
                                    {boleto?.pagador || "—"}
                                  </TableCell>
                                </TableRow>
                                {expandedUploadNf === nf.id && (
                                  <TableRow>
                                    <TableCell colSpan={6} className="p-0">
                                      <div className="bg-muted/30 p-4">
                                        {previewBlobUrls[`xml-${nf.id}`] ? (
                                          <div className="space-y-2">
                                            <iframe
                                              src={previewBlobUrls[`xml-${nf.id}`]}
                                              className="w-full h-64 rounded border bg-white"
                                              title={nf.nome_arquivo}
                                            />
                                            <Button
                                              size="sm"
                                              variant="outline"
                                              className="gap-2"
                                              onClick={(e) => {
                                                e.stopPropagation();
                                                setPreviewModal({ url: previewBlobUrls[`xml-${nf.id}`], title: nf.nome_arquivo });
                                              }}
                                            >
                                              <Maximize2 className="h-3.5 w-3.5" />
                                              Ampliar
                                            </Button>
                                          </div>
                                        ) : (
                                          <div className="flex items-center justify-center h-32 text-muted-foreground">
                                            <Loader2 className="h-5 w-5 animate-spin mr-2" />
                                            Carregando preview...
                                          </div>
                                        )}
                                      </div>
                                    </TableCell>
                                  </TableRow>
                                )}
                              </Fragment>
                            );
                          })}
                        </TableBody>
                      </Table>
                      </div>
                    );
                  })()}
                </CardContent>
              </Card>
            </TabsContent>

            {/* Envio tab — historico only */}
            <TabsContent value="envio" className="mt-4 space-y-4">
              {/* Historico de envios */}
              <Card>
                <CardHeader className="flex flex-row items-center justify-between">
                  <CardTitle className="text-base flex items-center gap-2">
                    <Mail className="h-4 w-4" /> Historico de Envios
                  </CardTitle>
                  {envios.some((e) => e.status === "rascunho") && (
                    <Button variant="outline" size="sm" onClick={handleVerificarStatus} disabled={verificarLoading} className="gap-2">
                      {verificarLoading ? <Loader2 className="h-3.5 w-3.5 animate-spin" /> : <RefreshCw className="h-3.5 w-3.5" />}
                      Verificar Status
                    </Button>
                  )}
                </CardHeader>
                <CardContent>
                  {enviosLoading ? (
                    <p className="text-center text-muted-foreground py-4">Carregando...</p>
                  ) : envios.length === 0 ? (
                    <p className="text-center text-muted-foreground py-8">Nenhum envio realizado ainda</p>
                  ) : (
                    <div className="overflow-x-auto">
                    <Table>
                      <TableHeader>
                        <TableRow>
                          <TableHead>Criado em</TableHead>
                          <TableHead>Enviado em</TableHead>
                          <TableHead>Destinatario</TableHead>
                          <TableHead>Assunto</TableHead>
                          <TableHead>Modo</TableHead>
                          <TableHead>Status</TableHead>
                          <TableHead className="text-center">Anexos</TableHead>
                          <TableHead className="text-center">Ações</TableHead>
                        </TableRow>
                      </TableHeader>
                      <TableBody>
                        {envios.map((envio) => (
                          <TableRow key={envio.id}>
                            <TableCell className="text-sm whitespace-nowrap">{formatDate(envio.created_at)}</TableCell>
                            <TableCell className="text-sm whitespace-nowrap">{envio.timestamp_envio ? formatDate(envio.timestamp_envio) : "—"}</TableCell>
                            <TableCell className="text-sm max-w-[200px] truncate">{envio.email_para.join(", ")}</TableCell>
                            <TableCell className="text-sm max-w-[200px] truncate">{envio.assunto}</TableCell>
                            <TableCell><Badge variant="outline">{envio.modo === "preview" ? "Preview" : "Automatico"}</Badge></TableCell>
                            <TableCell>
                              {envio.status === "enviado" && <Badge className="bg-success text-success-foreground">Enviado</Badge>}
                              {envio.status === "rascunho" && <Badge className="bg-warning text-warning-foreground">Rascunho</Badge>}
                              {envio.status === "erro" && <Badge variant="destructive" title={envio.erro_detalhes || ""}>Erro</Badge>}
                              {envio.status === "pendente" && <Badge variant="outline">Pendente</Badge>}
                            </TableCell>
                            <TableCell className="text-center font-[family-name:var(--font-barlow-condensed)]">{envio.boletos_ids.length + envio.xmls_anexados.length}</TableCell>
                            <TableCell className="text-center">
                              {envio.status === "rascunho" ? (
                                <Button variant="ghost" size="icon" onClick={() => setMarcarEnviadoId(envio.id)} className="h-8 w-8 text-success hover:text-success" title="Marcar como enviado">
                                  <CheckCircle2 className="h-4 w-4" />
                                </Button>
                              ) : <span className="text-muted-foreground">—</span>}
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
        </div>
      )}


      {/* Preview modal */}
      <Dialog open={!!previewModal} onOpenChange={() => setPreviewModal(null)}>
        <DialogContent className="max-w-5xl w-[95vw]">
          <DialogHeader>
            <DialogTitle className="truncate">{previewModal?.title}</DialogTitle>
            <DialogDescription>Preview do documento</DialogDescription>
          </DialogHeader>
          {previewModal && (
            <iframe
              src={previewModal.url}
              className="w-full h-[75vh] rounded border bg-white"
              title={previewModal.title}
            />
          )}
        </DialogContent>
      </Dialog>

      {/* Dialogs */}
      <Dialog open={confirmEnvioAuto} onOpenChange={setConfirmEnvioAuto}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Envio Automatico</DialogTitle>
            <DialogDescription>
              Deseja enviar {resultado?.aprovados || 0} boleto(s) automaticamente?
              Os emails serao enviados diretamente sem possibilidade de revisao.
            </DialogDescription>
          </DialogHeader>
          <div className="flex justify-end gap-3 mt-4">
            <Button variant="outline" onClick={() => setConfirmEnvioAuto(false)}>Cancelar</Button>
            <Button onClick={() => { setConfirmEnvioAuto(false); handleEnviar(); }} disabled={envioLoading} className="gap-2">
              <Send className="h-4 w-4" />
              Confirmar Envio
            </Button>
          </div>
        </DialogContent>
      </Dialog>

      <Dialog open={!!marcarEnviadoId} onOpenChange={() => setMarcarEnviadoId(null)}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Marcar como Enviado</DialogTitle>
            <DialogDescription>
              Confirma que este email foi enviado manualmente?
              O status sera atualizado de &quot;rascunho&quot; para &quot;enviado&quot;.
            </DialogDescription>
          </DialogHeader>
          <div className="flex justify-end gap-3 mt-4">
            <Button variant="outline" onClick={() => setMarcarEnviadoId(null)}>Cancelar</Button>
            <Button onClick={() => { if (marcarEnviadoId) handleMarcarEnviado(marcarEnviadoId); }} className="gap-2">
              <CheckCircle2 className="h-4 w-4" />
              Confirmar
            </Button>
          </div>
        </DialogContent>
      </Dialog>

      <Dialog open={confirmDialog === "finalizar"} onOpenChange={() => setConfirmDialog(null)}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Finalizar Operação</DialogTitle>
            <DialogDescription>
              Ao finalizar, a operação será marcada como concluída e os relatórios serão gerados.
              Esta ação não pode ser desfeita.
            </DialogDescription>
          </DialogHeader>
          <div className="flex justify-end gap-3 mt-4">
            <Button variant="outline" onClick={() => setConfirmDialog(null)}>Voltar</Button>
            <Button onClick={handleFinalizar} disabled={actionLoading}>Confirmar Finalização</Button>
          </div>
        </DialogContent>
      </Dialog>

      <Dialog open={confirmDialog === "cancelar"} onOpenChange={() => setConfirmDialog(null)}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Cancelar Operação</DialogTitle>
            <DialogDescription>
              Ao cancelar, a operação será marcada como cancelada e não poderá mais ser editada.
              Esta ação não pode ser desfeita.
            </DialogDescription>
          </DialogHeader>
          <div className="flex justify-end gap-3 mt-4">
            <Button variant="outline" onClick={() => setConfirmDialog(null)}>Voltar</Button>
            <Button className="bg-warning text-warning-foreground hover:bg-warning/90" onClick={handleCancelar} disabled={actionLoading}>Confirmar Cancelamento</Button>
          </div>
        </DialogContent>
      </Dialog>

      <Dialog open={confirmDialog === "excluir"} onOpenChange={() => setConfirmDialog(null)}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Excluir Operação</DialogTitle>
            <DialogDescription>
              Esta ação vai excluir permanentemente a operação {operacaoNumero} e todos os dados
              relacionados (boletos, XMLs, envios, logs). Esta ação não pode ser desfeita.
            </DialogDescription>
          </DialogHeader>
          <div className="flex justify-end gap-3 mt-4">
            <Button variant="outline" onClick={() => setConfirmDialog(null)}>Voltar</Button>
            <Button variant="destructive" onClick={handleExcluir} disabled={actionLoading}>Excluir Permanentemente</Button>
          </div>
        </DialogContent>
      </Dialog>
    </div>
  );
}
