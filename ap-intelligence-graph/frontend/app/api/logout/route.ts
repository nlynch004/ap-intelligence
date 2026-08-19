import { cookies } from "next/headers";

const COOKIE_NAME = "ap_admin_token";

export async function POST() {
  const store = await cookies();
  store.delete(COOKIE_NAME);
  return Response.json({ ok: true });
}
