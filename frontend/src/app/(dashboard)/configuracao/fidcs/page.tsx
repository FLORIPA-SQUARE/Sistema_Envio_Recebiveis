"use client";

import { useEffect, useState, useCallback } from "react";
import { apiFetch } from "@/lib/api";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Badge } from "@/components/ui/badge";
import { Switch } from "@/components/ui/switch";
import { Textarea } from "@/components/ui/textarea";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { toast } from "sonner";
import {
  Plus,
  Pencil,
  Mail,
  Power,
  PowerOff,
  X,
  Loader2,
  Eye,
} from "lucide-react";
import Link from "next/link";

interface Fidc {
  id: string;
  nome: string;
  nome_completo: string;
  cnpj: string | null;
  cc_emails: string[];
  palavras_chave: string[];
  cor: string;
  ativo: boolean;
  email_introducao: string | null;
  email_mensagem_fechamento: string | null;
  email_assinatura_nome: string | null;
}

type DialogMode = "create" | "edit" | null;

interface FormData {
  nome: string;
  nome_completo: string;
  cnpj: string;
  cor: string;
  cc_emails: string[];
  palavras_chave: string[];
  email_introducao: string;
  email_mensagem_fechamento: string;
  email_assinatura_nome: string;
}

const EMPTY_FORM: FormData = {
  nome: "",
  nome_completo: "",
  cnpj: "",
  cor: "#999999",
  cc_emails: [],
  palavras_chave: [],
  email_introducao: "",
  email_mensagem_fechamento: "",
  email_assinatura_nome: "",
};

export default function FidcsPage() {
  const [fidcs, setFidcs] = useState<Fidc[]>([]);
  const [loading, setLoading] = useState(true);
  const [dialogMode, setDialogMode] = useState<DialogMode>(null);
  const [editingFidcId, setEditingFidcId] = useState<string | null>(null);
  const [form, setForm] = useState<FormData>(EMPTY_FORM);
  const [saving, setSaving] = useState(false);
  const [toggling, setToggling] = useState<string | null>(null);

  // Preview state
  const [previewOpen, setPreviewOpen] = useState(false);
  const [previewHtml, setPreviewHtml] = useState<string>("");
  const [previewLoading, setPreviewLoading] = useState(false);

  // Chip inputs
  const [emailInput, setEmailInput] = useState("");
  const [keywordInput, setKeywordInput] = useState("");

  const loadFidcs = useCallback(async () => {
    try {
      const data = await apiFetch<Fidc[]>("/fidcs");
      setFidcs(data);
    } catch {
      toast.error("Erro ao carregar FIDCs");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    loadFidcs();
  }, [loadFidcs]);

  function openCreate() {
    setDialogMode("create");
    setEditingFidcId(null);
    setForm(EMPTY_FORM);
    setEmailInput("");
    setKeywordInput("");
  }

  function openEdit(fidc: Fidc) {
    setDialogMode("edit");
    setEditingFidcId(fidc.id);
    setForm({
      nome: fidc.nome,
      nome_completo: fidc.nome_completo,
      cnpj: fidc.cnpj || "",
      cor: fidc.cor,
      cc_emails: [...fidc.cc_emails],
      palavras_chave: [...fidc.palavras_chave],
      email_introducao: fidc.email_introducao || "",
      email_mensagem_fechamento: fidc.email_mensagem_fechamento || "",
      email_assinatura_nome: fidc.email_assinatura_nome || "",
    });
    setEmailInput("");
    setKeywordInput("");
  }

  function closeDialog() {
    setDialogMode(null);
    setEditingFidcId(null);
  }

  function addChip(
    field: "cc_emails" | "palavras_chave",
    value: string,
    setInput: (v: string) => void,
  ) {
    const trimmed = value.trim();
    if (!trimmed) return;
    if (form[field].includes(trimmed)) {
      toast.error("Item ja adicionado");
      return;
    }
    setForm((prev) => ({ ...prev, [field]: [...prev[field], trimmed] }));
    setInput("");
  }

  function removeChip(field: "cc_emails" | "palavras_chave", idx: number) {
    setForm((prev) => ({
      ...prev,
      [field]: prev[field].filter((_, i) => i !== idx),
    }));
  }

  async function handleSave() {
    if (!form.nome.trim()) {
      toast.error("Nome e obrigatorio");
      return;
    }
    if (!form.nome_completo.trim()) {
      toast.error("Nome completo e obrigatorio");
      return;
    }

    setSaving(true);
    try {
      if (dialogMode === "create") {
        await apiFetch("/fidcs", {
          method: "POST",
          body: JSON.stringify({
            nome: form.nome.trim().toUpperCase(),
            nome_completo: form.nome_completo.trim(),
            cnpj: form.cnpj.trim() || null,
            cor: form.cor,
            cc_emails: form.cc_emails,
            palavras_chave: form.palavras_chave,
            email_introducao: form.email_introducao.trim() || null,
            email_mensagem_fechamento:
              form.email_mensagem_fechamento.trim() || null,
            email_assinatura_nome:
              form.email_assinatura_nome.trim() || null,
          }),
        });
        toast.success(`FIDC ${form.nome.toUpperCase()} criado com sucesso`);
      } else if (dialogMode === "edit" && editingFidcId) {
        await apiFetch(`/fidcs/${editingFidcId}`, {
          method: "PUT",
          body: JSON.stringify({
            nome_completo: form.nome_completo.trim(),
            cnpj: form.cnpj.trim() || null,
            cor: form.cor,
            cc_emails: form.cc_emails,
            palavras_chave: form.palavras_chave,
            email_introducao: form.email_introducao.trim() || null,
            email_mensagem_fechamento:
              form.email_mensagem_fechamento.trim() || null,
            email_assinatura_nome:
              form.email_assinatura_nome.trim() || null,
          }),
        });
        toast.success(`FIDC ${form.nome} atualizado`);
      }
      closeDialog();
      loadFidcs();
    } catch (err: unknown) {
      const msg =
        err instanceof Error ? err.message : "Erro ao salvar";
      toast.error(msg);
    } finally {
      setSaving(false);
    }
  }

  async function toggleAtivo(fidc: Fidc) {
    setToggling(fidc.id);
    try {
      await apiFetch(`/fidcs/${fidc.id}`, {
        method: "PUT",
        body: JSON.stringify({ ativo: !fidc.ativo }),
      });
      toast.success(
        `${fidc.nome} ${fidc.ativo ? "desativado" : "ativado"}`,
      );
      loadFidcs();
    } catch {
      toast.error("Erro ao alterar status");
    } finally {
      setToggling(null);
    }
  }

  const hasCustomEmail = (f: Fidc) =>
    !!(f.email_introducao || f.email_mensagem_fechamento || f.email_assinatura_nome);

  async function handlePreview() {
    setPreviewLoading(true);
    try {
      const data = await apiFetch<{ html: string }>("/fidcs/preview-email", {
        method: "POST",
        body: JSON.stringify({
          nome_completo: form.nome_completo || "FIDC EXEMPLO",
          cnpj: form.cnpj || null,
          email_introducao: form.email_introducao || null,
          email_mensagem_fechamento: form.email_mensagem_fechamento || null,
          email_assinatura_nome: form.email_assinatura_nome || null,
        }),
      });
      const html = data.html.replace(
        /src="cid:assinatura_jj"/g,
        'src="/api/v1/assets/assinatura.jpg"'
      );
      setPreviewHtml(html);
      setPreviewOpen(true);
    } catch (err) {
      toast.error(err instanceof Error ? err.message : "Erro ao gerar preview");
    } finally {
      setPreviewLoading(false);
    }
  }

  async function handlePreviewFromCard(fidc: Fidc) {
    setPreviewLoading(true);
    try {
      const data = await apiFetch<{ html: string }>("/fidcs/preview-email", {
        method: "POST",
        body: JSON.stringify({
          nome_completo: fidc.nome_completo,
          cnpj: fidc.cnpj || null,
          email_introducao: fidc.email_introducao || null,
          email_mensagem_fechamento: fidc.email_mensagem_fechamento || null,
          email_assinatura_nome: fidc.email_assinatura_nome || null,
        }),
      });
      const html = data.html.replace(
        /src="cid:assinatura_jj"/g,
        'src="/api/v1/assets/assinatura.jpg"'
      );
      setPreviewHtml(html);
      setPreviewOpen(true);
    } catch (err) {
      toast.error(err instanceof Error ? err.message : "Erro ao gerar preview");
    } finally {
      setPreviewLoading(false);
    }
  }

  if (loading) {
    return (
      <div className="flex items-center gap-2 text-muted-foreground py-12 justify-center">
        <Loader2 className="h-4 w-4 animate-spin" />
        Carregando FIDCs...
      </div>
    );
  }

  return (
    <div className="space-y-8">
      <div className="flex items-start justify-between">
        <div>
          <h1 className="text-3xl font-bold">Configuracao de FIDCs</h1>
          <p className="text-muted-foreground">
            Gerencie FIDCs: dados cadastrais, emails CC, palavras-chave e textos
            de email personalizados
          </p>
        </div>
        <Button onClick={openCreate} className="gap-2">
          <Plus className="h-4 w-4" />
          Novo FIDC
        </Button>
      </div>

      {/* Config sub-navigation */}
      <div className="flex gap-2 border-b pb-2">
        <Button variant="secondary" size="sm">
          FIDCs
        </Button>
        <Link href="/configuracao/email">
          <Button variant="ghost" size="sm">
            Template de Email
          </Button>
        </Link>
      </div>

      {/* Grid de cards */}
      <div className="grid gap-4 md:grid-cols-2">
        {fidcs.map((fidc) => (
          <Card
            key={fidc.id}
            className={`relative transition-opacity ${!fidc.ativo ? "opacity-50" : ""}`}
          >
            <div
              className="absolute left-0 top-0 h-full w-1 rounded-l-xl"
              style={{ backgroundColor: fidc.cor }}
            />
            <CardHeader className="flex flex-row items-start justify-between">
              <div className="min-w-0 flex-1">
                <CardTitle className="flex items-center gap-2 flex-wrap">
                  <span
                    className="inline-block h-3 w-3 rounded-full shrink-0"
                    style={{ backgroundColor: fidc.cor }}
                  />
                  <span>{fidc.nome}</span>
                  {!fidc.ativo && (
                    <Badge variant="secondary" className="text-xs">
                      Inativo
                    </Badge>
                  )}
                  {hasCustomEmail(fidc) && (
                    <Mail className="h-3.5 w-3.5 text-primary shrink-0" />
                  )}
                </CardTitle>
                <CardDescription className="mt-1">
                  {fidc.nome_completo}
                </CardDescription>
              </div>
              <div className="flex gap-1 shrink-0">
                <Button
                  variant="ghost"
                  size="icon"
                  onClick={() => handlePreviewFromCard(fidc)}
                  disabled={previewLoading}
                  title="Visualizar email"
                >
                  <Eye className="h-4 w-4" />
                </Button>
                <Button
                  variant="ghost"
                  size="icon"
                  onClick={() => openEdit(fidc)}
                  title="Editar"
                >
                  <Pencil className="h-4 w-4" />
                </Button>
                <Button
                  variant="ghost"
                  size="icon"
                  onClick={() => toggleAtivo(fidc)}
                  disabled={toggling === fidc.id}
                  title={fidc.ativo ? "Desativar" : "Ativar"}
                >
                  {toggling === fidc.id ? (
                    <Loader2 className="h-4 w-4 animate-spin" />
                  ) : fidc.ativo ? (
                    <PowerOff className="h-4 w-4 text-muted-foreground" />
                  ) : (
                    <Power className="h-4 w-4 text-emerald-600" />
                  )}
                </Button>
              </div>
            </CardHeader>
            <CardContent className="space-y-3">
              {fidc.cnpj && (
                <div>
                  <span className="text-sm font-medium text-muted-foreground">
                    CNPJ:
                  </span>{" "}
                  <span className="font-[family-name:var(--font-barlow-condensed)]">
                    {fidc.cnpj}
                  </span>
                </div>
              )}
              {fidc.cc_emails.length > 0 && (
                <div>
                  <span className="text-sm font-medium text-muted-foreground">
                    Emails CC:
                  </span>
                  <div className="mt-1 flex flex-wrap gap-1">
                    {fidc.cc_emails.map((email) => (
                      <Badge key={email} variant="secondary" className="text-xs">
                        {email}
                      </Badge>
                    ))}
                  </div>
                </div>
              )}
              {fidc.palavras_chave.length > 0 && (
                <div>
                  <span className="text-sm font-medium text-muted-foreground">
                    Palavras-chave:
                  </span>
                  <div className="mt-1 flex flex-wrap gap-1">
                    {fidc.palavras_chave.map((kw) => (
                      <Badge key={kw} variant="outline" className="text-xs">
                        {kw}
                      </Badge>
                    ))}
                  </div>
                </div>
              )}
            </CardContent>
          </Card>
        ))}
      </div>

      {fidcs.length === 0 && (
        <div className="text-center py-12 text-muted-foreground">
          Nenhum FIDC cadastrado.{" "}
          <button
            onClick={openCreate}
            className="text-primary underline cursor-pointer"
          >
            Criar primeiro FIDC
          </button>
        </div>
      )}

      {/* Create/Edit Dialog */}
      <Dialog open={dialogMode !== null} onOpenChange={(open) => !open && closeDialog()}>
        <DialogContent className="sm:max-w-lg max-h-[90vh] overflow-y-auto">
          <DialogHeader>
            <DialogTitle>
              {dialogMode === "create" ? "Novo FIDC" : `Editar ${form.nome}`}
            </DialogTitle>
            <DialogDescription>
              {dialogMode === "create"
                ? "Preencha os dados do novo FIDC"
                : "Atualize os dados cadastrais e textos de email"}
            </DialogDescription>
          </DialogHeader>

          <Tabs defaultValue="dados" className="mt-2">
            <TabsList className="w-full">
              <TabsTrigger value="dados" className="flex-1">
                Dados Gerais
              </TabsTrigger>
              <TabsTrigger value="email" className="flex-1">
                Texto de Email
              </TabsTrigger>
            </TabsList>

            {/* Tab: Dados Gerais */}
            <TabsContent value="dados" className="space-y-4 pt-2">
              {/* Nome */}
              <div className="space-y-2">
                <Label htmlFor="nome">
                  Nome (identificador) <span className="text-destructive">*</span>
                </Label>
                <Input
                  id="nome"
                  value={form.nome}
                  onChange={(e) =>
                    setForm((prev) => ({
                      ...prev,
                      nome: e.target.value.toUpperCase(),
                    }))
                  }
                  placeholder="Ex: CAPITAL, NOVAX"
                  disabled={dialogMode === "edit"}
                  className={dialogMode === "edit" ? "opacity-60" : ""}
                />
                {dialogMode === "edit" && (
                  <p className="text-xs text-muted-foreground">
                    O nome nao pode ser alterado apos criacao
                  </p>
                )}
              </div>

              {/* Nome Completo */}
              <div className="space-y-2">
                <Label htmlFor="nome_completo">
                  Nome Completo <span className="text-destructive">*</span>
                </Label>
                <Input
                  id="nome_completo"
                  value={form.nome_completo}
                  onChange={(e) =>
                    setForm((prev) => ({
                      ...prev,
                      nome_completo: e.target.value,
                    }))
                  }
                  placeholder="Ex: CAPITAL RS FIDC LTDA"
                />
              </div>

              {/* CNPJ */}
              <div className="space-y-2">
                <Label htmlFor="cnpj">CNPJ</Label>
                <Input
                  id="cnpj"
                  value={form.cnpj}
                  onChange={(e) =>
                    setForm((prev) => ({ ...prev, cnpj: e.target.value }))
                  }
                  placeholder="00.000.000/0001-00"
                />
              </div>

              {/* Cor */}
              <div className="space-y-2">
                <Label>Cor</Label>
                <div className="flex items-center gap-3">
                  <input
                    type="color"
                    value={form.cor}
                    onChange={(e) =>
                      setForm((prev) => ({ ...prev, cor: e.target.value }))
                    }
                    className="h-9 w-12 rounded border cursor-pointer"
                  />
                  <Input
                    value={form.cor}
                    onChange={(e) =>
                      setForm((prev) => ({ ...prev, cor: e.target.value }))
                    }
                    className="w-28 font-[family-name:var(--font-barlow-condensed)]"
                    maxLength={7}
                  />
                </div>
              </div>

              {/* CC Emails (chips) */}
              <div className="space-y-2">
                <Label>Emails CC</Label>
                <div className="flex gap-2">
                  <Input
                    value={emailInput}
                    onChange={(e) => setEmailInput(e.target.value)}
                    onKeyDown={(e) => {
                      if (e.key === "Enter") {
                        e.preventDefault();
                        addChip("cc_emails", emailInput, setEmailInput);
                      }
                    }}
                    placeholder="email@exemplo.com + Enter"
                    className="flex-1"
                  />
                  <Button
                    type="button"
                    variant="outline"
                    size="sm"
                    onClick={() =>
                      addChip("cc_emails", emailInput, setEmailInput)
                    }
                  >
                    <Plus className="h-4 w-4" />
                  </Button>
                </div>
                {form.cc_emails.length > 0 && (
                  <div className="flex flex-wrap gap-1 mt-1">
                    {form.cc_emails.map((email, idx) => (
                      <Badge
                        key={idx}
                        variant="secondary"
                        className="gap-1 pr-1"
                      >
                        {email}
                        <button
                          type="button"
                          onClick={() => removeChip("cc_emails", idx)}
                          className="hover:text-destructive"
                        >
                          <X className="h-3 w-3" />
                        </button>
                      </Badge>
                    ))}
                  </div>
                )}
              </div>

              {/* Palavras-chave (chips) */}
              <div className="space-y-2">
                <Label>Palavras-chave</Label>
                <div className="flex gap-2">
                  <Input
                    value={keywordInput}
                    onChange={(e) => setKeywordInput(e.target.value)}
                    onKeyDown={(e) => {
                      if (e.key === "Enter") {
                        e.preventDefault();
                        addChip(
                          "palavras_chave",
                          keywordInput,
                          setKeywordInput,
                        );
                      }
                    }}
                    placeholder="Palavra-chave + Enter"
                    className="flex-1"
                  />
                  <Button
                    type="button"
                    variant="outline"
                    size="sm"
                    onClick={() =>
                      addChip(
                        "palavras_chave",
                        keywordInput,
                        setKeywordInput,
                      )
                    }
                  >
                    <Plus className="h-4 w-4" />
                  </Button>
                </div>
                {form.palavras_chave.length > 0 && (
                  <div className="flex flex-wrap gap-1 mt-1">
                    {form.palavras_chave.map((kw, idx) => (
                      <Badge
                        key={idx}
                        variant="outline"
                        className="gap-1 pr-1"
                      >
                        {kw}
                        <button
                          type="button"
                          onClick={() => removeChip("palavras_chave", idx)}
                          className="hover:text-destructive"
                        >
                          <X className="h-3 w-3" />
                        </button>
                      </Badge>
                    ))}
                  </div>
                )}
              </div>
            </TabsContent>

            {/* Tab: Texto de Email */}
            <TabsContent value="email" className="space-y-4 pt-2">
              <p className="text-xs text-muted-foreground">
                Personalize os textos de email para este FIDC. Campos vazios
                utilizam o template global.
              </p>

              <div className="space-y-2">
                <Label htmlFor="email_introducao">Introducao</Label>
                <Textarea
                  id="email_introducao"
                  value={form.email_introducao}
                  onChange={(e) =>
                    setForm((prev) => ({
                      ...prev,
                      email_introducao: e.target.value,
                    }))
                  }
                  placeholder="(Usar padrao global)"
                  rows={3}
                />
              </div>

              <div className="space-y-2">
                <Label htmlFor="email_mensagem_fechamento">
                  Mensagem de Fechamento
                </Label>
                <Textarea
                  id="email_mensagem_fechamento"
                  value={form.email_mensagem_fechamento}
                  onChange={(e) =>
                    setForm((prev) => ({
                      ...prev,
                      email_mensagem_fechamento: e.target.value,
                    }))
                  }
                  placeholder="(Usar padrao global)"
                  rows={3}
                />
              </div>

              <div className="space-y-2">
                <Label htmlFor="email_assinatura_nome">
                  Nome da Assinatura
                </Label>
                <Input
                  id="email_assinatura_nome"
                  value={form.email_assinatura_nome}
                  onChange={(e) =>
                    setForm((prev) => ({
                      ...prev,
                      email_assinatura_nome: e.target.value,
                    }))
                  }
                  placeholder="(Usar padrao global)"
                />
              </div>

              <Button
                type="button"
                variant="outline"
                className="w-full gap-2"
                onClick={handlePreview}
                disabled={previewLoading}
              >
                {previewLoading ? (
                  <Loader2 className="h-4 w-4 animate-spin" />
                ) : (
                  <Eye className="h-4 w-4" />
                )}
                Visualizar Email
              </Button>
              <p className="text-xs text-muted-foreground text-center -mt-2">
                Preview com dados de exemplo
              </p>
            </TabsContent>
          </Tabs>

          {/* Dialog Actions */}
          <div className="flex justify-end gap-2 pt-2 border-t">
            <Button variant="outline" onClick={closeDialog}>
              Cancelar
            </Button>
            <Button onClick={handleSave} disabled={saving}>
              {saving ? (
                <>
                  <Loader2 className="h-4 w-4 animate-spin mr-2" />
                  Salvando...
                </>
              ) : dialogMode === "create" ? (
                "Criar FIDC"
              ) : (
                "Salvar"
              )}
            </Button>
          </div>
        </DialogContent>
      </Dialog>

      {/* Preview Dialog */}
      <Dialog open={previewOpen} onOpenChange={setPreviewOpen}>
        <DialogContent className="sm:max-w-2xl max-h-[90vh]">
          <DialogHeader>
            <DialogTitle>Preview do Email</DialogTitle>
            <DialogDescription>
              Visualizacao do email com dados de exemplo
            </DialogDescription>
          </DialogHeader>
          <div className="border rounded-md overflow-hidden bg-white" style={{ height: "60vh" }}>
            <iframe
              srcDoc={previewHtml}
              sandbox="allow-same-origin"
              className="w-full h-full border-0"
              title="Email preview"
            />
          </div>
          <div className="flex justify-end">
            <Button variant="outline" onClick={() => setPreviewOpen(false)}>
              Fechar
            </Button>
          </div>
        </DialogContent>
      </Dialog>
    </div>
  );
}
