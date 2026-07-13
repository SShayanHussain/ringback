import { cookies } from "next/headers";

const ACCESS = "rb_access";
const REFRESH = "rb_refresh";

const base = {
  httpOnly: true as const,
  sameSite: "lax" as const,
  secure: process.env.NODE_ENV === "production",
  path: "/",
};

export function setSession(access: string, refresh: string) {
  const c = cookies();
  c.set(ACCESS, access, { ...base, maxAge: 60 * 15 });
  c.set(REFRESH, refresh, { ...base, maxAge: 60 * 60 * 24 * 14 });
}

export function clearSession() {
  const c = cookies();
  c.delete(ACCESS);
  c.delete(REFRESH);
}

export function getAccessToken(): string | undefined {
  return cookies().get(ACCESS)?.value;
}

export function getRefreshToken(): string | undefined {
  return cookies().get(REFRESH)?.value;
}

export function isAuthed(): boolean {
  return Boolean(getAccessToken());
}
