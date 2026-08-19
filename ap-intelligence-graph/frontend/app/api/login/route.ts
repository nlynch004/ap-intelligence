import { cookies } from "next/headers";

const COOKIE_NAME = "ap_admin_token";
const THIRTY_DAYS = 60 * 60 * 24 * 30;

export async function POST(request: Request) {
  const expected = process.env.ADMIN_PASSWORD;
  if (!expected) {
    // No password configured on this deployment - nothing to check against.
    // Fail closed rather than silently accepting anything.
    return Response.json({ ok: false, error: "Login is not configured on this deployment." }, { status: 500 });
  }

  let password: unknown;
  try {
    ({ password } = await request.json());
  } catch {
    return Response.json({ ok: false, error: "Malformed request." }, { status: 400 });
  }

  if (typeof password !== "string" || password !== expected) {
    return Response.json({ ok: false, error: "Incorrect password." }, { status: 401 });
  }

  // Deliberately readable by client JS (not httpOnly): frontend/lib/api.ts
  // reads this same cookie in the browser to attach the shared secret as an
  // X-Admin-Password header on every FastAPI call, since the backend lives
  // on a separate origin and needs its own independent check (see
  // backend/app/main.py::require_admin_password) - a caller who bypasses
  // the Vercel-hosted frontend entirely must still be turned away.
  const store = await cookies();
  store.set(COOKIE_NAME, expected, {
    httpOnly: false,
    secure: process.env.NODE_ENV === "production",
    sameSite: "lax",
    path: "/",
    maxAge: THIRTY_DAYS,
  });

  return Response.json({ ok: true });
}
