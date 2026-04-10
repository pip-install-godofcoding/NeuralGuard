import { NextRequest, NextResponse } from "next/server";
import { createServerClient } from "@supabase/ssr";
import { cookies } from "next/headers";
import { createClient as adminClient } from "@supabase/supabase-js";
import crypto from "crypto";

export async function POST(req: NextRequest) {
  // ── 1. Verify session ─────────────────────────────────────
  const cookieStore = await cookies();
  const supabase = createServerClient(
    process.env.NEXT_PUBLIC_SUPABASE_URL!,
    process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY!,
    {
      cookies: {
        getAll: () => cookieStore.getAll(),
        setAll: () => {},
      },
    }
  );

  const {
    data: { user },
  } = await supabase.auth.getUser();

  if (!user) {
    return NextResponse.json({ error: "Unauthorized" }, { status: 401 });
  }

  // ── 2. Generate key ────────────────────────────────────────
  const { label = "My Key" } = await req.json().catch(() => ({}));
  const plaintext = `ng-${crypto.randomBytes(20).toString("hex")}`;
  const keyHash = crypto.createHash("sha256").update(plaintext).digest("hex");

  // ── 3. Store hash (service role bypasses RLS) ──────────────
  const admin = adminClient(
    process.env.NEXT_PUBLIC_SUPABASE_URL!,
    process.env.SUPABASE_SERVICE_KEY!
  );

  const { data, error } = await admin
    .from("api_keys")
    .insert({ user_id: user.id, key_hash: keyHash, label })
    .select("id, label, created_at")
    .single();

  if (error) {
    return NextResponse.json({ error: error.message }, { status: 500 });
  }

  return NextResponse.json({ key: plaintext, meta: data });
}
