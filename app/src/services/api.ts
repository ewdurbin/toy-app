import {
  useQuery,
  useMutation,
  useQueryClient,
} from "@tanstack/react-query";

const API_URL = import.meta.env.VITE_API_URL ?? "http://localhost:8000";

export interface Item {
  id: string;
  name: string;
  description: string | null;
  created_at: string;
  updated_at: string;
}

export interface CreateItemInput {
  name: string;
  description?: string;
}

export interface UpdateItemInput {
  name?: string;
  description?: string;
}

async function fetchJson<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(`${API_URL}${path}`, {
    headers: { "Content-Type": "application/json" },
    ...init,
  });
  if (!res.ok) {
    throw new Error(`${res.status} ${res.statusText}`);
  }
  if (res.status === 204) return undefined as T;
  return res.json();
}

export function useItemCount() {
  return useQuery<{ count: number }>({
    queryKey: ["items", "count"],
    queryFn: () => fetchJson("/v1/items/count"),
  });
}

export function useItems() {
  return useQuery<Item[]>({
    queryKey: ["items"],
    queryFn: () => fetchJson("/v1/items"),
  });
}

export function useSearchItems(query: string) {
  return useQuery<Item[]>({
    queryKey: ["items", "search", query],
    queryFn: () => fetchJson(`/v1/items/search?q=${encodeURIComponent(query)}`),
    enabled: query.length > 0,
  });
}

export function useItem(id: string) {
  return useQuery<Item>({
    queryKey: ["items", id],
    queryFn: () => fetchJson(`/v1/items/${id}`),
  });
}

export function useCreateItem() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (input: CreateItemInput) =>
      fetchJson<Item>("/v1/items", {
        method: "POST",
        body: JSON.stringify(input),
      }),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["items"] }),
  });
}

export function useUpdateItem(id: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (input: UpdateItemInput) =>
      fetchJson<Item>(`/v1/items/${id}`, {
        method: "PATCH",
        body: JSON.stringify(input),
      }),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["items"] }),
  });
}

export function useDeleteItem() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (id: string) =>
      fetchJson<void>(`/v1/items/${id}`, { method: "DELETE" }),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["items"] }),
  });
}
