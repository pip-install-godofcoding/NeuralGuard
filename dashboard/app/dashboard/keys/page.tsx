import { createClient } from "@/lib/supabase-server";
import ApiKeyManager from "@/components/ApiKeyManager";

export default async function KeysPage() {
  const supabase = await createClient();
  const {
    data: { user },
  } = await supabase.auth.getUser();

  const { data: keys } = await supabase
    .from("api_keys")
    .select("id, label, is_active, created_at, revoked_at")
    .eq("user_id", user!.id)
    .order("created_at", { ascending: false });

  return (
    <div className="space-y-8 max-w-3xl">
      <div>
        <h1 className="text-2xl font-bold text-white">API Keys</h1>
        <p className="text-white/40 text-sm mt-1">
          Manage your NeuralGuard API keys. Use these as a drop-in replacement for your OpenAI key.
        </p>
      </div>
      <ApiKeyManager userId={user!.id} initialKeys={keys ?? []} />
    </div>
  );
}
