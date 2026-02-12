"use client";

import { useEffect, useState } from "react";
import { apiFetch } from "@/lib/api";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Badge } from "@/components/ui/badge";
import {
  Card,
  CardContent,
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
import { toast } from "sonner";
import { Plus, Pencil, Trash2, CheckCircle2, Eye, Mail } from "lucide-react";
import Link from "next/link";

interface EmailLayout {
  id: string;
  nome: string;
  saudacao: string;
  introducao: string;
  mensagem_fechamento: string;
  assinatura_nome: string;
  ativo: boolean;
  created_at: string;
  updated_at: string;
}

const DEFAULTS = {
  saudacao: "Boa tarde,",
  introducao: "Prezado cliente,",
  mensagem_fechamento: "Em caso de duvidas, nossa equipe permanece a disposicao para esclarecimentos.",
  assinatura_nome: "Equipe de Cobranca",
};

const MAX_LAYOUTS = 3;

export default function EmailConfigPage() {
  const [layouts, setLayouts] = useState<EmailLayout[]>([]);
  const [loading, setLoading] = useState(true);
  const [dialogOpen, setDialogOpen] = useState(false);
  const [editingLayout, setEditingLayout] = useState<EmailLayout | null>(null);
  const [saving, setSaving] = useState(false);
  const [deleteConfirm, setDeleteConfirm] = useState<string | null>(null);
  const [previewLayout, setPreviewLayout] = useState<EmailLayout | null>(null);

  // Form fields
  const [formNome, setFormNome] = useState("");
  const [formSaudacao, setFormSaudacao] = useState("");
  const [formIntroducao, setFormIntroducao] = useState("");
  const [formFechamento, setFormFechamento] = useState("");
  const [formAssinatura, setFormAssinatura] = useState("");

  async function loadLayouts() {
    try {
      const data = await apiFetch<EmailLayout[]>("/configuracao/email-layouts");
      setLayouts(data);
    } catch {
      toast.error("Erro ao carregar layouts");
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    loadLayouts();
  }, []);

  function openCreate() {
    setEditingLayout(null);
    setFormNome("");
    setFormSaudacao(DEFAULTS.saudacao);
    setFormIntroducao(DEFAULTS.introducao);
    setFormFechamento(DEFAULTS.mensagem_fechamento);
    setFormAssinatura(DEFAULTS.assinatura_nome);
    setDialogOpen(true);
  }

  function openEdit(layout: EmailLayout) {
    setEditingLayout(layout);
    setFormNome(layout.nome);
    setFormSaudacao(layout.saudacao);
    setFormIntroducao(layout.introducao);
    setFormFechamento(layout.mensagem_fechamento);
    setFormAssinatura(layout.assinatura_nome);
    setDialogOpen(true);
  }

  async function handleSave() {
    if (!formNome.trim()) {
      toast.error("O nome do layout e obrigatorio");
      return;
    }
    setSaving(true);
    try {
      const payload = {
        nome: formNome.trim(),
        saudacao: formSaudacao,
        introducao: formIntroducao,
        mensagem_fechamento: formFechamento,
        assinatura_nome: formAssinatura,
      };
      if (editingLayout) {
        await apiFetch(`/configuracao/email-layouts/${editingLayout.id}`, {
          method: "PUT",
          body: JSON.stringify(payload),
        });
        toast.success(`Layout "${formNome}" atualizado`);
      } else {
        await apiFetch("/configuracao/email-layouts", {
          method: "POST",
          body: JSON.stringify(payload),
        });
        toast.success(`Layout "${formNome}" criado`);
      }
      setDialogOpen(false);
      loadLayouts();
    } catch (err) {
      toast.error(err instanceof Error ? err.message : "Erro ao salvar");
    } finally {
      setSaving(false);
    }
  }

  async function handleAtivar(id: string) {
    try {
      await apiFetch(`/configuracao/email-layouts/${id}/ativar`, { method: "PATCH" });
      toast.success("Layout ativado");
      loadLayouts();
    } catch (err) {
      toast.error(err instanceof Error ? err.message : "Erro ao ativar");
    }
  }

  async function handleDelete(id: string) {
    try {
      await apiFetch(`/configuracao/email-layouts/${id}`, { method: "DELETE" });
      toast.success("Layout excluido");
      setDeleteConfirm(null);
      loadLayouts();
    } catch (err) {
      toast.error(err instanceof Error ? err.message : "Erro ao excluir");
    }
  }

  if (loading) {
    return <div className="text-muted-foreground">Carregando...</div>;
  }

  return (
    <div className="space-y-8">
      <div>
        <h1 className="text-3xl font-bold">Configuracao de Email</h1>
        <p className="text-muted-foreground">
          Gerencie os layouts do template de email. Maximo de {MAX_LAYOUTS} layouts. O layout ativo sera usado em todos os envios.
        </p>
      </div>

      {/* Config sub-navigation */}
      <div className="flex gap-2 border-b pb-2">
        <Link href="/configuracao/fidcs">
          <Button variant="ghost" size="sm">FIDCs</Button>
        </Link>
        <Button variant="secondary" size="sm">Template de Email</Button>
      </div>

      {/* Action bar */}
      <div className="flex justify-end">
        <Button
          onClick={openCreate}
          disabled={layouts.length >= MAX_LAYOUTS}
          className="gap-2"
        >
          <Plus className="h-4 w-4" />
          Novo Layout
          {layouts.length >= MAX_LAYOUTS && (
            <span className="text-xs opacity-70">(limite atingido)</span>
          )}
        </Button>
      </div>

      {/* Layouts grid */}
      {layouts.length === 0 ? (
        <Card>
          <CardContent className="py-12 text-center text-muted-foreground">
            <Mail className="h-10 w-10 mx-auto mb-3 opacity-40" />
            <p>Nenhum layout criado. Clique em "Novo Layout" para comecar.</p>
          </CardContent>
        </Card>
      ) : (
        <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
          {layouts.map((layout) => (
            <Card
              key={layout.id}
              className={`relative transition-shadow ${layout.ativo ? "ring-2 ring-primary shadow-md" : ""}`}
            >
              {layout.ativo && (
                <div className="absolute -top-2 -right-2">
                  <Badge className="bg-primary text-primary-foreground gap-1">
                    <CheckCircle2 className="h-3 w-3" /> Ativo
                  </Badge>
                </div>
              )}
              <CardHeader>
                <CardTitle className="text-lg">{layout.nome}</CardTitle>
              </CardHeader>
              <CardContent className="space-y-3">
                <div>
                  <span className="text-xs font-medium text-muted-foreground uppercase">Saudacao</span>
                  <p className="text-sm">{layout.saudacao}</p>
                </div>
                <div>
                  <span className="text-xs font-medium text-muted-foreground uppercase">Introducao</span>
                  <p className="text-sm">{layout.introducao}</p>
                </div>
                <div>
                  <span className="text-xs font-medium text-muted-foreground uppercase">Fechamento</span>
                  <p className="text-sm line-clamp-2">{layout.mensagem_fechamento}</p>
                </div>
                <div>
                  <span className="text-xs font-medium text-muted-foreground uppercase">Assinatura</span>
                  <p className="text-sm">{layout.assinatura_nome}</p>
                </div>

                {/* Actions */}
                <div className="flex items-center gap-2 pt-2 border-t">
                  <Button variant="ghost" size="sm" onClick={() => setPreviewLayout(layout)} className="gap-1">
                    <Eye className="h-3.5 w-3.5" /> Preview
                  </Button>
                  <Button variant="ghost" size="sm" onClick={() => openEdit(layout)} className="gap-1">
                    <Pencil className="h-3.5 w-3.5" /> Editar
                  </Button>
                  {!layout.ativo && (
                    <>
                      <Button variant="ghost" size="sm" onClick={() => handleAtivar(layout.id)} className="gap-1 text-primary hover:text-primary">
                        <CheckCircle2 className="h-3.5 w-3.5" /> Ativar
                      </Button>
                      <Button variant="ghost" size="sm" onClick={() => setDeleteConfirm(layout.id)} className="gap-1 text-destructive hover:text-destructive">
                        <Trash2 className="h-3.5 w-3.5" /> Excluir
                      </Button>
                    </>
                  )}
                </div>
              </CardContent>
            </Card>
          ))}
        </div>
      )}

      {/* Create/Edit Dialog */}
      <Dialog open={dialogOpen} onOpenChange={setDialogOpen}>
        <DialogContent className="max-w-2xl">
          <DialogHeader>
            <DialogTitle>{editingLayout ? `Editar "${editingLayout.nome}"` : "Novo Layout"}</DialogTitle>
            <DialogDescription>
              Configure os textos do template de email. As partes dinamicas (NFs, valores, dados do FIDC) sao preenchidas automaticamente.
            </DialogDescription>
          </DialogHeader>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-6 pt-4">
            {/* Form */}
            <div className="space-y-4">
              <div className="space-y-2">
                <Label>Nome do Layout</Label>
                <Input
                  value={formNome}
                  onChange={(e) => setFormNome(e.target.value)}
                  placeholder="Ex: Padrao, Formal, Resumido"
                />
              </div>
              <div className="space-y-2">
                <Label>Saudacao</Label>
                <Input
                  value={formSaudacao}
                  onChange={(e) => setFormSaudacao(e.target.value)}
                  placeholder="Boa tarde,"
                />
              </div>
              <div className="space-y-2">
                <Label>Introducao (antes do nome do cliente)</Label>
                <Input
                  value={formIntroducao}
                  onChange={(e) => setFormIntroducao(e.target.value)}
                  placeholder="Prezado cliente,"
                />
              </div>
              <div className="space-y-2">
                <Label>Mensagem de Fechamento</Label>
                <textarea
                  className="flex min-h-[80px] w-full rounded-md border border-input bg-background px-3 py-2 text-sm ring-offset-background placeholder:text-muted-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2"
                  value={formFechamento}
                  onChange={(e) => setFormFechamento(e.target.value)}
                  placeholder="Em caso de duvidas..."
                />
              </div>
              <div className="space-y-2">
                <Label>Nome da Assinatura</Label>
                <Input
                  value={formAssinatura}
                  onChange={(e) => setFormAssinatura(e.target.value)}
                  placeholder="Equipe de Cobranca"
                />
              </div>
              <div className="flex justify-end gap-2 pt-2">
                <Button variant="outline" onClick={() => setDialogOpen(false)}>Cancelar</Button>
                <Button onClick={handleSave} disabled={saving}>
                  {saving ? "Salvando..." : editingLayout ? "Salvar" : "Criar Layout"}
                </Button>
              </div>
            </div>

            {/* Live Preview */}
            <div className="space-y-2">
              <Label className="text-muted-foreground">Preview do Email</Label>
              <div className="rounded-md border bg-white p-4 text-sm space-y-3 max-h-[400px] overflow-y-auto" style={{ fontFamily: "Arial, sans-serif", fontSize: "13px", color: "#333" }}>
                <p>{formSaudacao || "Boa tarde,"}</p>
                <p>
                  {formIntroducao || "Prezado cliente,"}<br />
                  <strong>EMPRESA EXEMPLO LTDA</strong>,
                </p>
                <p>Enviamos anexo o(s) seu(s) boletos emitidos conforme a(s) notas: <strong>12345, 12346</strong></p>
                <p>Valor: R$ 1.500,00, Vencimento: 15/03/2026</p>
                <p>Valor: R$ 2.300,00, Vencimento: 20/03/2026</p>
                <p>O(s) boletos estao com beneficiario nominal a <strong>CAPITAL RS FIDC NP MULTISSETORIAL</strong>, CNPJ: <strong>12.910.463/0001-70</strong>.</p>
                <p>Vide boletos e notas em anexo.<br />Favor confirmar recebimento.</p>
                <p>{formFechamento || "Em caso de duvidas, nossa equipe permanece a disposicao para esclarecimentos."}</p>
                <p>
                  Atenciosamente,<br />
                  <strong>{formAssinatura || "Equipe de Cobranca"}</strong>
                </p>
                <div className="text-xs text-muted-foreground italic border-t pt-2 mt-2">[Imagem da assinatura JotaJota]</div>
              </div>
            </div>
          </div>
        </DialogContent>
      </Dialog>

      {/* Preview Dialog (read-only) */}
      <Dialog open={!!previewLayout} onOpenChange={() => setPreviewLayout(null)}>
        <DialogContent className="max-w-lg">
          <DialogHeader>
            <DialogTitle>Preview: {previewLayout?.nome}</DialogTitle>
            <DialogDescription>Visualizacao do email com dados de exemplo</DialogDescription>
          </DialogHeader>
          {previewLayout && (
            <div className="rounded-md border bg-white p-4 text-sm space-y-3" style={{ fontFamily: "Arial, sans-serif", fontSize: "13px", color: "#333" }}>
              <p>{previewLayout.saudacao}</p>
              <p>
                {previewLayout.introducao}<br />
                <strong>EMPRESA EXEMPLO LTDA</strong>,
              </p>
              <p>Enviamos anexo o(s) seu(s) boletos emitidos conforme a(s) notas: <strong>12345, 12346</strong></p>
              <p>Valor: R$ 1.500,00, Vencimento: 15/03/2026</p>
              <p>Valor: R$ 2.300,00, Vencimento: 20/03/2026</p>
              <p>O(s) boletos estao com beneficiario nominal a <strong>CAPITAL RS FIDC NP MULTISSETORIAL</strong>, CNPJ: <strong>12.910.463/0001-70</strong>.</p>
              <p>Vide boletos e notas em anexo.<br />Favor confirmar recebimento.</p>
              <p>{previewLayout.mensagem_fechamento}</p>
              <p>
                Atenciosamente,<br />
                <strong>{previewLayout.assinatura_nome}</strong>
              </p>
              <div className="text-xs text-muted-foreground italic border-t pt-2 mt-2">[Imagem da assinatura JotaJota]</div>
            </div>
          )}
        </DialogContent>
      </Dialog>

      {/* Delete Confirmation */}
      <Dialog open={!!deleteConfirm} onOpenChange={() => setDeleteConfirm(null)}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Excluir Layout</DialogTitle>
            <DialogDescription>
              Tem certeza que deseja excluir este layout? Esta acao nao pode ser desfeita.
            </DialogDescription>
          </DialogHeader>
          <div className="flex justify-end gap-3 mt-4">
            <Button variant="outline" onClick={() => setDeleteConfirm(null)}>Cancelar</Button>
            <Button variant="destructive" onClick={() => deleteConfirm && handleDelete(deleteConfirm)}>
              Excluir
            </Button>
          </div>
        </DialogContent>
      </Dialog>
    </div>
  );
}
