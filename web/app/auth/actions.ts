"use server";

import { redirect } from "next/navigation";
import { apiPost } from "@/lib/api";
import { setSession } from "@/lib/session";

type AuthResp = { access_token: string; refresh_token: string; user: Record<string, unknown> };

export async function loginAction(formData: FormData) {
  const email = String(formData.get("email") || "");
  const password = String(formData.get("password") || "");
  let error = "";
  try {
    const data = await apiPost<AuthResp>("/auth/login", { email, password });
    setSession(data.access_token, data.refresh_token);
  } catch (e) {
    error = e instanceof Error ? e.message : "Login failed";
  }
  // redirect() throws NEXT_REDIRECT — must live OUTSIDE the try/catch.
  if (error) redirect(`/login?error=${encodeURIComponent(error)}`);
  redirect("/dashboard");
}

export async function signupAction(formData: FormData) {
  const email = String(formData.get("email") || "");
  const password = String(formData.get("password") || "");
  const workspace_name = String(formData.get("workspace_name") || "") || undefined;
  let error = "";
  try {
    const data = await apiPost<AuthResp>("/auth/signup", { email, password, workspace_name });
    setSession(data.access_token, data.refresh_token);
  } catch (e) {
    error = e instanceof Error ? e.message : "Signup failed";
  }
  if (error) redirect(`/signup?error=${encodeURIComponent(error)}`);
  redirect("/dashboard");
}
