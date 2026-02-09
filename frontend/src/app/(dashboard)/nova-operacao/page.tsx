"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
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
import { Separator } from "@/components/ui/separator";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { toast } from "sonner";
import {
  FileText,
  FileCode,
  Play,
  CheckCircle2,
  XCircle,
  AlertTriangle,
  Loader2,
} from "lucide-react";
import { FileDropzone } from "@/components/file-dropzone";

interface Fidc {
  id: string;
  nome: string;
  nome_completo: string;
  cor: string;
}

interface BoletoResumo {
  id: string;
  arquivo_original: string;
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

interface BoletoCompleto {
  id: string;
  arquivo_original: string;
  arquivo_renomeado: string | null;
  pagador: string | null;
  numero_nota: string | null;
  vencimento: string | null;
  valor_formatado: string | null;
  status: string;
  motivo_rejeicao: string | null;
  juros_detectado: boolean;
}

interface ResultadoProcessamento {
  total: number;
  aprovados: number;
  rejeitados: number;
  taxa_sucesso: number;
  boletos: BoletoCompleto[];
}

type Step = "config" | "upload" | "result";

export default function NovaOperacaoPage() {
  const router = useRouter();
  const [fidcs, setFidcs] = useState<Fidc[]>([]);
  const [selectedFidc, setSelectedFidc] = useState("");
  const [numero, setNumero] = useState("");
  const [operacaoId, setOperacaoId] = useState<string | null>(null);
  const [step, setStep] = useState<Step>("config");

  // Upload state
  const [pdfFiles, setPdfFiles] = useState<File[]>([]);
  const [xmlFiles, setXmlFiles] = useState<File[]>([]);
  const [uploadedBoletos, setUploadedBoletos] = useState<BoletoResumo[]>([]);
  const [uploadedXmls, setUploadedXmls] = useState<XmlResumo[]>([]);
  const [uploading, setUploading] = useState(false);

  // Processing state
  const [processing, setProcessing] = useState(false);
  const [resultado, setResultado] = useState<ResultadoProcessamento | null>(null);

  useEffect(() => {
    apiFetch<Fidc[]>("/fidcs").then(setFidcs).catch(() => toast.error("Erro ao carregar FIDCs"));
  }, []);

  // ── Step 1: Create operation ──────────────────────────────

  async function handleCreateOperation() {
    if (!selectedFidc) {
      toast.error("Selecione um FIDC");
      return;
    }

    try {
      const op = await apiFetch<{ id: string }>("/operacoes", {
        method: "POST",
        body: JSON.stringify({
          fidc_id: selectedFidc,
          numero: numero || undefined,
        }),
      });
      setOperacaoId(op.id);
      setStep("upload");
      toast.success("Operação criada");
    } catch {
      toast.error("Erro ao criar operação");
    }
  }

  // ── Step 2: Upload files ──────────────────────────────────

  async function handleUpload() {
    if (!operacaoId) return;
    if (pdfFiles.length === 0) {
      toast.error("Selecione ao menos um boleto PDF");
      return;
    }

    setUploading(true);

    try {
      // Upload PDFs
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

      // Upload XMLs (if any)
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

  // ── Step 3: Process ───────────────────────────────────────

  async function handleProcess() {
    if (!operacaoId) return;
    setProcessing(true);

    try {
      const result = await apiFetch<ResultadoProcessamento>(
        `/operacoes/${operacaoId}/processar`,
        { method: "POST" }
      );
      setResultado(result);
      setStep("result");
      toast.success(
        `Processamento concluido: ${result.aprovados} aprovados, ${result.rejeitados} rejeitados`
      );
    } catch {
      toast.error("Erro ao processar operação");
    } finally {
      setProcessing(false);
    }
  }

  // ── Render ────────────────────────────────────────────────

  const selectedFidcObj = fidcs.find((f) => f.id === selectedFidc);

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-3xl font-bold">Nova Operação</h1>
        <p className="text-muted-foreground">
          Upload de boletos e XMLs para processamento
        </p>
      </div>

      {/* Steps indicator */}
      <div className="flex items-center gap-2">
        {["config", "upload", "result"].map((s, i) => (
          <div key={s} className="flex items-center gap-2">
            {i > 0 && <Separator className="w-8" />}
            <div
              className={`flex h-8 w-8 items-center justify-center rounded-full text-sm font-bold ${
                step === s
                  ? "bg-primary text-primary-foreground"
                  : s === "result" && step !== "result"
                  ? "bg-muted text-muted-foreground"
                  : "bg-primary/20 text-primary"
              }`}
            >
              {i + 1}
            </div>
            <span className="text-sm font-medium capitalize">{s === "config" ? "Configurar" : s === "upload" ? "Upload" : "Resultado"}</span>
          </div>
        ))}
      </div>

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
                <SelectTrigger>
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
              <Label>Número da Operação (opcional)</Label>
              <Input
                value={numero}
                onChange={(e) => setNumero(e.target.value)}
                placeholder="Ex: OP-0001 (gerado automaticamente se vazio)"
              />
            </div>
            <Button onClick={handleCreateOperation} disabled={!selectedFidc}>
              Criar Operação
            </Button>
          </CardContent>
        </Card>
      )}

      {/* Step 2: Upload */}
      {step === "upload" && (
        <div className="space-y-4">
          {selectedFidcObj && (
            <div className="flex items-center gap-2">
              <span
                className="inline-block h-3 w-3 rounded-full"
                style={{ backgroundColor: selectedFidcObj.cor }}
              />
              <span className="font-medium">{selectedFidcObj.nome}</span>
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
                XMLs NFe
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
                    accept=".xml"
                    label="Arraste XMLs de NFe aqui"
                    icon="xml"
                    files={xmlFiles}
                    onFilesChange={setXmlFiles}
                  />
                </CardContent>
              </Card>
            </TabsContent>
          </Tabs>

          {/* Uploaded XMLs preview table */}
          {uploadedXmls.length > 0 && (
            <Card>
              <CardHeader>
                <CardTitle className="text-base">XMLs Parseados</CardTitle>
              </CardHeader>
              <CardContent>
                <div className="overflow-x-auto">
                <Table>
                  <TableHeader>
                    <TableRow>
                      <TableHead>NF</TableHead>
                      <TableHead>Destinatário</TableHead>
                      <TableHead>CNPJ</TableHead>
                      <TableHead className="text-right">Valor</TableHead>
                      <TableHead>Emails</TableHead>
                      <TableHead>Status</TableHead>
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    {uploadedXmls.map((xml) => (
                      <TableRow key={xml.id}>
                        <TableCell className="font-[family-name:var(--font-barlow-condensed)] font-semibold">
                          {xml.numero_nota}
                        </TableCell>
                        <TableCell>{xml.nome_destinatario || "—"}</TableCell>
                        <TableCell className="font-[family-name:var(--font-barlow-condensed)]">
                          {xml.cnpj || "—"}
                        </TableCell>
                        <TableCell className="text-right font-[family-name:var(--font-barlow-condensed)]">
                          {xml.valor_total
                            ? `R$ ${xml.valor_total.toLocaleString("pt-BR", { minimumFractionDigits: 2 })}`
                            : "—"}
                        </TableCell>
                        <TableCell>
                          <div className="flex flex-col gap-0.5">
                            {xml.emails.map((e) => (
                              <span key={e} className="text-xs">{e}</span>
                            ))}
                            {xml.emails_invalidos.map((e) => (
                              <span key={e} className="text-xs text-destructive line-through">{e}</span>
                            ))}
                          </div>
                        </TableCell>
                        <TableCell>
                          {xml.xml_valido ? (
                            <Badge className="bg-success text-success-foreground">Válido</Badge>
                          ) : (
                            <Badge variant="destructive">Inválido</Badge>
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

          <div className="flex gap-3">
            <Button onClick={handleUpload} disabled={uploading || pdfFiles.length === 0}>
              {uploading && <Loader2 className="mr-2 h-4 w-4 animate-spin" />}
              {uploading ? "Enviando..." : "Enviar Arquivos"}
            </Button>

            {uploadedBoletos.length > 0 && (
              <Button onClick={handleProcess} disabled={processing} className="gap-2">
                {processing ? (
                  <Loader2 className="h-4 w-4 animate-spin" />
                ) : (
                  <Play className="h-4 w-4" />
                )}
                {processing ? "Processando..." : "Processar Operação"}
              </Button>
            )}
          </div>
        </div>
      )}

      {/* Step 3: Result */}
      {step === "result" && resultado && (
        <div className="space-y-4">
          {/* Summary cards */}
          <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
            <Card>
              <CardContent className="pt-6">
                <div className="text-sm text-muted-foreground">Total</div>
                <div className="text-3xl font-bold font-[family-name:var(--font-barlow-condensed)]">
                  {resultado.total}
                </div>
              </CardContent>
            </Card>
            <Card>
              <CardContent className="pt-6">
                <div className="flex items-center gap-1 text-sm text-success">
                  <CheckCircle2 className="h-4 w-4" /> Aprovados
                </div>
                <div className="text-3xl font-bold font-[family-name:var(--font-barlow-condensed)] text-success">
                  {resultado.aprovados}
                </div>
              </CardContent>
            </Card>
            <Card>
              <CardContent className="pt-6">
                <div className="flex items-center gap-1 text-sm text-destructive">
                  <XCircle className="h-4 w-4" /> Rejeitados
                </div>
                <div className="text-3xl font-bold font-[family-name:var(--font-barlow-condensed)] text-destructive">
                  {resultado.rejeitados}
                </div>
              </CardContent>
            </Card>
            <Card>
              <CardContent className="pt-6">
                <div className="text-sm text-muted-foreground">Taxa de Sucesso</div>
                <div className="text-3xl font-bold font-[family-name:var(--font-barlow-condensed)]">
                  {resultado.taxa_sucesso.toFixed(1)}%
                </div>
                <Progress value={resultado.taxa_sucesso} className="mt-2" />
              </CardContent>
            </Card>
          </div>

          {/* Boletos table */}
          <Card>
            <CardHeader>
              <CardTitle>Boletos Processados</CardTitle>
            </CardHeader>
            <CardContent>
              <div className="overflow-x-auto">
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead>Status</TableHead>
                    <TableHead>Arquivo Renomeado</TableHead>
                    <TableHead>Pagador</TableHead>
                    <TableHead>NF</TableHead>
                    <TableHead>Vencimento</TableHead>
                    <TableHead className="text-right">Valor</TableHead>
                    <TableHead>Motivo</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {resultado.boletos.map((b) => (
                    <TableRow key={b.id}>
                      <TableCell>
                        {b.status === "aprovado" ? (
                          <Badge className="bg-success text-success-foreground">Aprovado</Badge>
                        ) : (
                          <Badge variant="destructive">Rejeitado</Badge>
                        )}
                        {b.juros_detectado && (
                          <Badge variant="outline" className="ml-1 border-warning text-warning">
                            <AlertTriangle className="mr-1 h-3 w-3" />
                            Juros
                          </Badge>
                        )}
                      </TableCell>
                      <TableCell className="max-w-[200px] truncate text-xs">
                        {b.arquivo_renomeado || b.arquivo_original}
                      </TableCell>
                      <TableCell>{b.pagador || "—"}</TableCell>
                      <TableCell className="font-[family-name:var(--font-barlow-condensed)] font-semibold">
                        {b.numero_nota || "—"}
                      </TableCell>
                      <TableCell className="font-[family-name:var(--font-barlow-condensed)]">
                        {b.vencimento || "—"}
                      </TableCell>
                      <TableCell className="text-right font-[family-name:var(--font-barlow-condensed)]">
                        {b.valor_formatado || "—"}
                      </TableCell>
                      <TableCell className="max-w-[200px] truncate text-xs text-destructive">
                        {b.motivo_rejeicao || ""}
                      </TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
              </div>
            </CardContent>
          </Card>

          <Button variant="outline" onClick={() => router.push("/")}>
            Voltar ao Dashboard
          </Button>
        </div>
      )}
    </div>
  );
}
