import { NextResponse } from "next/server";
import type { NextRequest } from "next/server";

// Light shared-secret admin gate (Next.js 16 renamed middleware.ts -> proxy.ts,
// same runtime/API - see node_modules/next/dist/docs/.../proxy.md). Not a
// real auth system: one password, configured via ADMIN_PASSWORD, checked
// against the cookie the /login flow sets. Deliberately a no-op when
// ADMIN_PASSWORD isn't set (local dev has no login prompt by design - see
// backend/app/config.py's identical no-op-when-unset rule).
const COOKIE_NAME = "ap_admin_token";

export function proxy(request: NextRequest) {
  const expected = process.env.ADMIN_PASSWORD;
  if (!expected) return NextResponse.next();

  const token = request.cookies.get(COOKIE_NAME)?.value;
  if (token === expected) return NextResponse.next();

  const loginUrl = new URL("/login", request.url);
  loginUrl.searchParams.set("from", request.nextUrl.pathname);
  return NextResponse.redirect(loginUrl);
}

export const config = {
  // Everything except the login page itself, the login/logout API routes
  // (must stay reachable to log in/out at all), Next's own static/image
  // assets, and the favicon.
  matcher: ["/((?!login|api/login|api/logout|_next/static|_next/image|favicon.ico).*)"],
};
