import { useState } from "react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { BrowserRouter, Routes, Route, Link } from "react-router-dom";
import {
  Plus,
  Trash2,
  Search,
  LogOut,
  ShieldCheck,
  ChevronDown,
} from "lucide-react";
import {
  useAuthStatus,
  useCurrentUser,
  useItems,
  useSearchItems,
  useItemCount,
  useCreateItem,
  useDeleteItem,
  useLogin,
  useLogout,
  useSignup,
  type CreateItemInput,
} from "@/services/api";

const queryClient = new QueryClient();

type AuthMode = "signup" | "login";

function AuthControl() {
  const [mode, setMode] = useState<AuthMode>("signup");
  const [open, setOpen] = useState(false);
  const [form, setForm] = useState({ email: "", password: "" });
  const { data: authStatus, isLoading: isStatusLoading } = useAuthStatus();
  const authEnabled = authStatus?.enabled ?? false;
  const { data: authSession, isLoading: isSessionLoading } = useCurrentUser(
    authEnabled,
  );
  const signup = useSignup();
  const login = useLogin();
  const logout = useLogout();
  const activeMutation = mode === "signup" ? signup : login;

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    activeMutation.mutate(form, {
      onSuccess: () => {
        setForm({ email: "", password: "" });
        setOpen(false);
      },
    });
  };

  const triggerLabel = isStatusLoading
    ? "Auth"
    : authSession
      ? authSession.user.email
      : authEnabled
        ? "Account"
        : "Auth offline";

  return (
    <div className="relative">
      <button
        onClick={() => setOpen((current) => !current)}
        className="inline-flex items-center gap-2 rounded-full border border-gray-200 bg-white px-3 py-2 text-sm font-medium text-gray-700 shadow-sm transition hover:border-amber-300 hover:text-gray-900"
      >
        <ShieldCheck
          size={16}
          className={authEnabled ? "text-amber-600" : "text-gray-400"}
        />
        <span className="max-w-36 truncate">{triggerLabel}</span>
        <ChevronDown
          size={16}
          className={`text-gray-400 transition ${open ? "rotate-180" : ""}`}
        />
      </button>

      {open && (
        <div className="absolute right-0 top-full z-20 mt-3 w-[min(24rem,calc(100vw-3rem))] rounded-2xl border border-gray-200 bg-white p-4 shadow-xl">
          <div className="mb-4 flex items-start justify-between gap-3">
            <div>
              <p className="text-xs font-semibold uppercase tracking-[0.22em] text-amber-700">
                Account
              </p>
            </div>
            {authSession && (
              <button
                onClick={() => logout.mutate()}
                disabled={logout.isPending}
                className="inline-flex items-center gap-2 rounded-full border border-gray-200 px-3 py-1.5 text-xs font-medium text-gray-600 transition hover:border-red-300 hover:text-red-600 disabled:opacity-50"
              >
                <LogOut size={14} />
                {logout.isPending ? "Signing out..." : "Log out"}
              </button>
            )}
          </div>

          {isStatusLoading ? (
            <p className="text-sm text-gray-500">
              Checking whether Postgres auth is configured...
            </p>
          ) : !authEnabled ? (
            <div className="rounded-xl border border-dashed border-gray-200 bg-gray-50 p-4 text-sm text-gray-600">
              Postgres auth is disabled for this run. Set
              <code className="mx-1 rounded bg-gray-200 px-1.5 py-0.5 text-xs">
                DATABASE_URL
              </code>
              or the split
              <code className="mx-1 rounded bg-gray-200 px-1.5 py-0.5 text-xs">
                DATABASE_*
              </code>
              variables and restart the server.
            </div>
          ) : isSessionLoading ? (
            <p className="text-sm text-gray-500">
              Checking for an existing session...
            </p>
          ) : authSession ? (
            <div className="space-y-3 rounded-xl bg-amber-50 p-4 text-sm text-gray-700">
              <div>
                <p className="font-medium text-gray-900">Signed in as</p>
                <p className="mt-1 break-all">{authSession.user.email}</p>
              </div>
              <div className="grid gap-3 text-xs text-gray-600 sm:grid-cols-2">
                <div>
                  <p className="font-medium text-gray-900">Account created</p>
                  <p>{new Date(authSession.user.created_at).toLocaleString()}</p>
                </div>
                <div>
                  <p className="font-medium text-gray-900">Session expires</p>
                  <p>{new Date(authSession.expires_at).toLocaleString()}</p>
                </div>
              </div>
            </div>
          ) : (
            <div>
              <div className="mb-4 inline-flex rounded-full bg-gray-100 p-1 text-sm">
                <button
                  onClick={() => setMode("signup")}
                  className={`rounded-full px-3 py-1.5 transition ${
                    mode === "signup"
                      ? "bg-white text-gray-900 shadow-sm"
                      : "text-gray-500"
                  }`}
                >
                  Sign up
                </button>
                <button
                  onClick={() => setMode("login")}
                  className={`rounded-full px-3 py-1.5 transition ${
                    mode === "login"
                      ? "bg-white text-gray-900 shadow-sm"
                      : "text-gray-500"
                  }`}
                >
                  Log in
                </button>
              </div>

              <form onSubmit={handleSubmit} className="space-y-3">
                <input
                  type="email"
                  placeholder="you@example.com"
                  value={form.email}
                  onChange={(e) => setForm({ ...form, email: e.target.value })}
                  className="w-full rounded-xl border border-gray-300 px-3 py-2.5"
                  required
                />
                <input
                  type="password"
                  placeholder="At least 8 characters"
                  value={form.password}
                  onChange={(e) => setForm({ ...form, password: e.target.value })}
                  className="w-full rounded-xl border border-gray-300 px-3 py-2.5"
                  required
                  minLength={8}
                />
                <button
                  type="submit"
                  disabled={activeMutation.isPending}
                  className="w-full rounded-xl bg-amber-500 px-4 py-2.5 text-sm font-medium text-white transition hover:bg-amber-600 disabled:opacity-50"
                >
                  {activeMutation.isPending
                    ? mode === "signup"
                      ? "Creating..."
                      : "Signing in..."
                    : mode === "signup"
                      ? "Create account"
                      : "Log in"}
                </button>
              </form>

              {activeMutation.error instanceof Error && (
                <p className="mt-3 text-sm text-red-600">
                  {activeMutation.error.message}
                </p>
              )}
            </div>
          )}
        </div>
      )}
    </div>
  );
}

function ItemsList() {
  const [searchQuery, setSearchQuery] = useState("");
  const { data: items, isLoading, error } = useItems();
  const { data: searchResults } = useSearchItems(searchQuery);
  const { data: countData } = useItemCount();
  const createItem = useCreateItem();
  const deleteItem = useDeleteItem();
  const [form, setForm] = useState<CreateItemInput>({ name: "", description: "" });
  const [showForm, setShowForm] = useState(false);
  const displayItems = searchQuery ? searchResults : items;

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!form.name.trim()) return;
    createItem.mutate(
      { name: form.name, description: form.description || undefined },
      {
        onSuccess: () => {
          setForm({ name: "", description: "" });
          setShowForm(false);
        },
      },
    );
  };

  return (
    <div className="max-w-2xl mx-auto p-6">
      <div className="mb-6 flex flex-wrap items-center justify-between gap-3">
        <h1 className="text-2xl font-bold">
          Items{countData != null && <span className="ml-2 text-base font-normal text-gray-400">({countData.count})</span>}
        </h1>
        <div className="flex items-center gap-2">
          <AuthControl />
          <button
            onClick={() => setShowForm(!showForm)}
            className="flex items-center gap-1 rounded-md bg-blue-600 px-3 py-1.5 text-sm text-white hover:bg-blue-700"
          >
            <Plus size={16} />
            New Item
          </button>
        </div>
      </div>

      <div className="relative mb-4">
        <Search size={16} className="absolute left-3 top-1/2 -translate-y-1/2 text-gray-400" />
        <input
          type="text"
          placeholder="Search items..."
          value={searchQuery}
          onChange={(e) => setSearchQuery(e.target.value)}
          className="w-full pl-9 pr-3 py-2 border rounded-md"
        />
      </div>

      {showForm && (
        <form onSubmit={handleSubmit} className="mb-6 p-4 border rounded-lg space-y-3">
          <input
            type="text"
            placeholder="Name"
            value={form.name}
            onChange={(e) => setForm({ ...form, name: e.target.value })}
            className="w-full px-3 py-2 border rounded-md"
            required
          />
          <input
            type="text"
            placeholder="Description (optional)"
            value={form.description}
            onChange={(e) => setForm({ ...form, description: e.target.value })}
            className="w-full px-3 py-2 border rounded-md"
          />
          <button
            type="submit"
            disabled={createItem.isPending}
            className="rounded-md bg-blue-600 px-4 py-2 text-sm text-white hover:bg-blue-700 disabled:opacity-50"
          >
            {createItem.isPending ? "Creating..." : "Create"}
          </button>
        </form>
      )}

      {isLoading && <p className="text-gray-500">Loading...</p>}
      {error && <p className="text-red-500">Error: {error.message}</p>}

      <ul className="space-y-2">
        {displayItems?.map((item) => (
          <li
            key={item.id}
            className="flex items-center justify-between p-3 border rounded-lg"
          >
            <div>
              <Link
                to={`/items/${item.id}`}
                className="font-medium hover:text-blue-600"
              >
                {item.name}
              </Link>
              {item.description && (
                <p className="text-sm text-gray-500">{item.description}</p>
              )}
            </div>
            <button
              onClick={() => deleteItem.mutate(item.id)}
              className="text-gray-400 hover:text-red-500"
            >
              <Trash2 size={16} />
            </button>
          </li>
        ))}
      </ul>

      {displayItems?.length === 0 && !searchQuery && (
        <p className="text-gray-400 text-center py-8">
          No items yet. Create one to get started.
        </p>
      )}
    </div>
  );
}

export default function App() {
  return (
    <QueryClientProvider client={queryClient}>
      <BrowserRouter>
        <Routes>
          <Route path="/" element={<ItemsList />} />
          <Route path="/items/:id" element={<ItemsList />} />
        </Routes>
      </BrowserRouter>
    </QueryClientProvider>
  );
}
