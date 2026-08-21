import { cookies } from "next/headers";

const COOKIE_NAME = "ap_admin_token";
const THIRTY_DAYS = 60 * 60 * 24 * 30;

export async function POST(request: Request) {
  const expected = process.env.ADMIN_PASSWORD;
  if (!expected) {
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
