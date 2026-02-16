"use client";

import { useEffect, useState } from "react";
import { useRouter, usePathname } from "next/navigation";
import Link from "next/link";
import {
  LayoutDashboard,
  FilePlus,
  Settings,
  LogOut,
  FileText,
  Search,
  Menu,
  Plus,
  X,
} from "lucide-react";
import { Button } from "@/components/ui/button";
import {
  Sheet,
  SheetContent,
  SheetTitle,
  SheetTrigger,
} from "@/components/ui/sheet";
import {
  OperationTabsProvider,
  useOperationTabs,
} from "@/contexts/operation-tabs";
import { VersionBadge } from "@/components/version-dialog";

const NAV_ITEMS = [
  { href: "/", label: "Dashboard", icon: LayoutDashboard },
  { href: "/nova-operacao", label: "Criar Operação", icon: FilePlus },
  { href: "/historico", label: "Histórico", icon: FileText },
  { href: "/auditoria", label: "Auditoria", icon: Search },
  { href: "/configuracao/fidcs", label: "Configuração", icon: Settings },
];

export default function DashboardLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  const router = useRouter();
  const pathname = usePathname();
  const [userName, setUserName] = useState("");
  const [sheetOpen, setSheetOpen] = useState(false);

  useEffect(() => {
    const token = localStorage.getItem("token");
    if (!token) {
      router.push("/login");
      return;
    }
    const user = JSON.parse(localStorage.getItem("user") || "{}");
    setUserName(user.nome || "");
  }, [router]);

  function handleLogout() {
    localStorage.removeItem("token");
    localStorage.removeItem("user");
    router.push("/login");
  }

  function GlobalTabBar() {
    const { tabs, activeTabId, addTab, removeTab, setActiveTab } =
      useOperationTabs();

    if (tabs.length === 0) return null;

    function handleTabClick(tabId: string) {
      setActiveTab(tabId);
      if (pathname !== "/nova-operacao") {
        router.push("/nova-operacao");
      }
    }

    function handleRemoveTab(tabId: string) {
      removeTab(tabId);
    }

    return (
      <div className="px-4 md:px-8 pt-4 md:pt-6">
        <div className="flex items-center gap-1 overflow-x-auto pb-3">
          {tabs.map((tab) => {
            const isActive = tab.tabId === activeTabId;
            const label = tab.operacaoNumero || "Nova OP";
            return (
              <button
                key={tab.tabId}
                type="button"
                onClick={() => handleTabClick(tab.tabId)}
                className={`group flex items-center gap-1.5 rounded-t-lg border px-3 py-1.5 text-sm font-medium whitespace-nowrap transition-colors ${
                  isActive
                    ? "border-b-transparent bg-background border-border shadow-sm"
                    : "border-transparent bg-muted/40 text-muted-foreground hover:bg-muted hover:text-foreground"
                }`}
              >
                {tab.fidcCor && (
                  <span
                    className="h-2 w-2 rounded-full shrink-0"
                    style={{ backgroundColor: tab.fidcCor || "#999" }}
                  />
                )}
                <span>{label}</span>
                <span
                  role="button"
                  tabIndex={0}
                  onClick={(e) => {
                    e.stopPropagation();
                    handleRemoveTab(tab.tabId);
                  }}
                  onKeyDown={(e) => {
                    if (e.key === "Enter") {
                      e.stopPropagation();
                      handleRemoveTab(tab.tabId);
                    }
                  }}
                  className="ml-1 rounded p-0.5 opacity-0 group-hover:opacity-100 hover:bg-destructive/10 hover:text-destructive transition-opacity"
                >
                  <X className="h-3 w-3" />
                </span>
              </button>
            );
          })}
          {tabs.length < 10 && (
            <button
              type="button"
              onClick={() => {
                addTab();
                if (pathname !== "/nova-operacao") {
                  router.push("/nova-operacao");
                }
              }}
              className="flex items-center gap-1 rounded-lg border border-dashed border-muted-foreground/30 px-2.5 py-1.5 text-sm text-muted-foreground hover:bg-muted hover:text-foreground transition-colors"
              title="Nova aba"
            >
              <Plus className="h-3.5 w-3.5" />
            </button>
          )}
        </div>
        <div className="border-b-2 border-primary" />
      </div>
    );
  }

  function SidebarNav({ onNavigate }: { onNavigate?: () => void }) {
    return (
      <>
        <nav className="flex-1 space-y-1 p-4">
          {NAV_ITEMS.map((item) => {
            const isActive =
              item.href === "/nova-operacao"
                ? pathname === "/nova-operacao"
                : pathname === item.href;

            return (
              <Link
                key={item.href}
                href={item.href}
                onClick={onNavigate}
                className={`flex items-center gap-3 rounded-lg px-3 py-2 text-sm font-medium transition-colors ${
                  isActive
                    ? "bg-primary text-primary-foreground"
                    : "text-sidebar-foreground hover:bg-sidebar-accent"
                }`}
              >
                <item.icon className="h-4 w-4" />
                {item.label}
              </Link>
            );
          })}
        </nav>

        <div className="border-t p-4">
          <div className="mb-2 truncate text-sm text-muted-foreground">
            {userName}
          </div>
          <Button
            variant="ghost"
            size="sm"
            className="w-full justify-start gap-2"
            onClick={handleLogout}
          >
            <LogOut className="h-4 w-4" />
            Sair
          </Button>
          <div className="mt-3 flex justify-center">
            <VersionBadge />
          </div>
        </div>
      </>
    );
  }

  return (
    <OperationTabsProvider>
    <div className="flex min-h-screen">
      {/* Desktop Sidebar — hidden on mobile */}
      <aside className="hidden md:flex w-64 flex-col border-r bg-sidebar">
        <div className="flex h-16 items-center border-b px-6">
          <span className="text-xl font-bold">
            <span className="text-primary">Jota</span>Jota
          </span>
        </div>
        <SidebarNav />
      </aside>

      {/* Main wrapper */}
      <div className="flex flex-1 flex-col">
        {/* Mobile header — visible only on mobile */}
        <header className="flex md:hidden h-14 items-center border-b bg-sidebar px-4 gap-3">
          <Sheet open={sheetOpen} onOpenChange={setSheetOpen}>
            <SheetTrigger asChild>
              <Button variant="ghost" size="icon">
                <Menu className="h-5 w-5" />
                <span className="sr-only">Menu</span>
              </Button>
            </SheetTrigger>
            <SheetContent side="left" className="w-64 p-0 bg-sidebar">
              <SheetTitle className="sr-only">Menu de navegacao</SheetTitle>
              <div className="flex h-16 items-center border-b px-6">
                <span className="text-xl font-bold">
                  <span className="text-primary">Jota</span>Jota
                </span>
              </div>
              <SidebarNav onNavigate={() => setSheetOpen(false)} />
            </SheetContent>
          </Sheet>
          <span className="text-lg font-bold">
            <span className="text-primary">Jota</span>Jota
          </span>
        </header>

        {/* Tab bar (global — all pages) */}
        <GlobalTabBar />

        {/* Main content */}
        <main className="flex-1 overflow-auto">
          <div className="p-4 md:p-8">{children}</div>
        </main>
      </div>
    </div>
    </OperationTabsProvider>
  );
}
