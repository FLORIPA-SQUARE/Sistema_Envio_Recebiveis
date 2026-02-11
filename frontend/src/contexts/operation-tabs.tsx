"use client";

import {
  createContext,
  useCallback,
  useContext,
  useState,
  type ReactNode,
} from "react";

export interface OperationTab {
  tabId: string;
  operacaoId: string | null;
  operacaoNumero: string | null;
  step: "config" | "upload" | "resultado";
  fidcId: string;
  fidcNome: string;
  fidcCor: string;
}

interface OpenOperationParams {
  operacaoId: string;
  operacaoNumero: string;
  fidcId?: string;
  fidcNome?: string;
  fidcCor?: string;
}

interface OperationTabsContextType {
  tabs: OperationTab[];
  activeTabId: string | null;
  addTab: () => string | null;
  removeTab: (tabId: string) => void;
  setActiveTab: (tabId: string) => void;
  updateTab: (tabId: string, updates: Partial<OperationTab>) => void;
  openOperation: (params: OpenOperationParams) => string | null;
}

const MAX_TABS = 10;

const OperationTabsContext = createContext<OperationTabsContextType | null>(
  null,
);

function generateId() {
  return Math.random().toString(36).slice(2, 10);
}

export function OperationTabsProvider({ children }: { children: ReactNode }) {
  const [tabs, setTabs] = useState<OperationTab[]>([]);
  const [activeTabId, setActiveTabId] = useState<string | null>(null);

  const addTab = useCallback(() => {
    if (tabs.length >= MAX_TABS) return null;
    const tabId = generateId();
    const newTab: OperationTab = {
      tabId,
      operacaoId: null,
      operacaoNumero: null,
      step: "config",
      fidcId: "",
      fidcNome: "",
      fidcCor: "",
    };
    setTabs((prev) => [...prev, newTab]);
    setActiveTabId(tabId);
    return tabId;
  }, [tabs.length]);

  const removeTab = useCallback(
    (tabId: string) => {
      setTabs((prev) => {
        const idx = prev.findIndex((t) => t.tabId === tabId);
        const next = prev.filter((t) => t.tabId !== tabId);

        if (activeTabId === tabId) {
          // Activate adjacent tab
          if (next.length === 0) {
            setActiveTabId(null);
          } else if (idx >= next.length) {
            setActiveTabId(next[next.length - 1].tabId);
          } else {
            setActiveTabId(next[idx].tabId);
          }
        }

        return next;
      });
    },
    [activeTabId],
  );

  const setActiveTab = useCallback((tabId: string) => {
    setActiveTabId(tabId);
  }, []);

  const updateTab = useCallback(
    (tabId: string, updates: Partial<OperationTab>) => {
      setTabs((prev) =>
        prev.map((t) => (t.tabId === tabId ? { ...t, ...updates } : t)),
      );
    },
    [],
  );

  const openOperation = useCallback(
    (params: OpenOperationParams) => {
      // If already open, just activate that tab
      const existing = tabs.find((t) => t.operacaoId === params.operacaoId);
      if (existing) {
        setActiveTabId(existing.tabId);
        return existing.tabId;
      }
      if (tabs.length >= MAX_TABS) return null;
      const tabId = generateId();
      const newTab: OperationTab = {
        tabId,
        operacaoId: params.operacaoId,
        operacaoNumero: params.operacaoNumero,
        step: "resultado",
        fidcId: params.fidcId || "",
        fidcNome: params.fidcNome || "",
        fidcCor: params.fidcCor || "",
      };
      setTabs((prev) => [...prev, newTab]);
      setActiveTabId(tabId);
      return tabId;
    },
    [tabs],
  );

  return (
    <OperationTabsContext.Provider
      value={{ tabs, activeTabId, addTab, removeTab, setActiveTab, updateTab, openOperation }}
    >
      {children}
    </OperationTabsContext.Provider>
  );
}

export function useOperationTabs() {
  const ctx = useContext(OperationTabsContext);
  if (!ctx) {
    throw new Error(
      "useOperationTabs must be used within OperationTabsProvider",
    );
  }
  return ctx;
}
