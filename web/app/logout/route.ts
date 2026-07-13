import { NextResponse } from "next/server";
import { clearSession } from "@/lib/session";
import { APP_URL } from "@/lib/env";

function bye() {
  clearSession();
  return NextResponse.redirect(new URL("/login", APP_URL));
}

export async function POST() {
  return bye();
}

export async function GET() {
  return bye();
}
