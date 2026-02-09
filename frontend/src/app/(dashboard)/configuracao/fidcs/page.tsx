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
import { toast } from "sonner";
import { Pencil } from "lucide-react";

interface Fidc {
  id: string;
  nome: string;
  nome_completo: string;
  cnpj: string | null;
  cc_emails: string[];
  palavras_chave: string[];
  cor: string;
  ativo: boolean;
}

export default function FidcsPage() {
  const [fidcs, setFidcs] = useState<Fidc[]>([]);
  const [loading, setLoading] = useState(true);
  const [editingFidc, setEditingFidc] = useState<Fidc | null>(null);
  const [editEmails, setEditEmails] = useState("");
  const [editKeywords, setEditKeywords] = useState("");
  const [saving, setSaving] = useState(false);

  async function loadFidcs() {
    try {
      const data = await apiFetch<Fidc[]>("/fidcs");
      setFidcs(data);
    } catch {
      toast.error("Erro ao carregar FIDCs");
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    loadFidcs();
  }, []);

  function openEdit(fidc: Fidc) {
    setEditingFidc(fidc);
    setEditEmails(fidc.cc_emails.join(", "));
    setEditKeywords(fidc.palavras_chave.join(", "));
  }

  async function handleSave() {
    if (!editingFidc) return;
    setSaving(true);
    try {
      await apiFetch(`/fidcs/${editingFidc.id}`, {
        method: "PUT",
        body: JSON.stringify({
          cc_emails: editEmails.split(",").map((e) => e.trim()).filter(Boolean),
          palavras_chave: editKeywords.split(",").map((k) => k.trim()).filter(Boolean),
        }),
      });
      toast.success(`FIDC ${editingFidc.nome} atualizado`);
      setEditingFidc(null);
      loadFidcs();
    } catch {
      toast.error("Erro ao salvar");
    } finally {
      setSaving(false);
    }
  }

  if (loading) {
    return <div className="text-muted-foreground">Carregando...</div>;
  }

  return (
    <div className="space-y-8">
      <div>
        <h1 className="text-3xl font-bold">Configuração de FIDCs</h1>
        <p className="text-muted-foreground">
          Gerencie as configurações de cada FIDC (emails CC, palavras-chave)
        </p>
      </div>

      <div className="grid gap-4 md:grid-cols-2">
        {fidcs.map((fidc) => (
          <Card key={fidc.id} className="relative">
            <div
              className="absolute left-0 top-0 h-full w-1 rounded-l-xl"
              style={{ backgroundColor: fidc.cor }}
            />
            <CardHeader className="flex flex-row items-start justify-between">
              <div>
                <CardTitle className="flex items-center gap-2">
                  <span
                    className="inline-block h-3 w-3 rounded-full"
                    style={{ backgroundColor: fidc.cor }}
                  />
                  {fidc.nome}
                </CardTitle>
                <CardDescription className="mt-1">
                  {fidc.nome_completo}
                </CardDescription>
              </div>
              <Button
                variant="ghost"
                size="icon"
                onClick={() => openEdit(fidc)}
              >
                <Pencil className="h-4 w-4" />
              </Button>
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
              <div>
                <span className="text-sm font-medium text-muted-foreground">
                  Emails CC:
                </span>
                <div className="mt-1 flex flex-wrap gap-1">
                  {fidc.cc_emails.map((email) => (
                    <Badge key={email} variant="secondary">
                      {email}
                    </Badge>
                  ))}
                </div>
              </div>
              <div>
                <span className="text-sm font-medium text-muted-foreground">
                  Palavras-chave:
                </span>
                <div className="mt-1 flex flex-wrap gap-1">
                  {fidc.palavras_chave.map((kw) => (
                    <Badge key={kw} variant="outline">
                      {kw}
                    </Badge>
                  ))}
                </div>
              </div>
            </CardContent>
          </Card>
        ))}
      </div>

      {/* Edit Dialog */}
      <Dialog
        open={!!editingFidc}
        onOpenChange={(open) => !open && setEditingFidc(null)}
      >
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Editar {editingFidc?.nome}</DialogTitle>
            <DialogDescription>
              Atualize os emails CC e palavras-chave de detecção
            </DialogDescription>
          </DialogHeader>
          <div className="space-y-4 pt-4">
            <div className="space-y-2">
              <Label>Emails CC (separados por vírgula)</Label>
              <Input
                value={editEmails}
                onChange={(e) => setEditEmails(e.target.value)}
                placeholder="email1@example.com, email2@example.com"
              />
            </div>
            <div className="space-y-2">
              <Label>Palavras-chave (separadas por vírgula)</Label>
              <Input
                value={editKeywords}
                onChange={(e) => setEditKeywords(e.target.value)}
                placeholder="CAPITAL RS, CAPITAL RS FIDC"
              />
            </div>
            <div className="flex justify-end gap-2">
              <Button
                variant="outline"
                onClick={() => setEditingFidc(null)}
              >
                Cancelar
              </Button>
              <Button onClick={handleSave} disabled={saving}>
                {saving ? "Salvando..." : "Salvar"}
              </Button>
            </div>
          </div>
        </DialogContent>
      </Dialog>
    </div>
  );
}
