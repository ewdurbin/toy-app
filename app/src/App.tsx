import { useState } from "react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { BrowserRouter, Routes, Route, Link } from "react-router-dom";
import { Plus, Trash2, Search } from "lucide-react";
import {
  useItems,
  useSearchItems,
  useCreateItem,
  useDeleteItem,
  type CreateItemInput,
} from "@/services/api";

const queryClient = new QueryClient();

function ItemsList() {
  const [searchQuery, setSearchQuery] = useState("");
  const { data: items, isLoading, error } = useItems();
  const { data: searchResults } = useSearchItems(searchQuery);
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
      <div className="flex items-center justify-between mb-6">
        <h1 className="text-2xl font-bold">Items</h1>
        <button
          onClick={() => setShowForm(!showForm)}
          className="flex items-center gap-1 px-3 py-1.5 bg-purple-600 text-white rounded-md hover:bg-purple-700 text-sm"
        >
          <Plus size={16} />
          New Item
        </button>
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
            className="px-4 py-2 bg-purple-600 text-white rounded-md hover:bg-purple-700 disabled:opacity-50 text-sm"
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
