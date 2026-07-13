import { redirect } from "next/navigation";
import { Logo } from "@ringback/ui";
import { isAuthed } from "@/lib/session";
import { Nav } from "@/components/Nav";
import { LogoutButton } from "@/components/LogoutButton";

export default function AppLayout({ children }: { children: React.ReactNode }) {
  if (!isAuthed()) redirect("/login");
  return (
    <div className="rb-shell">
      <aside className="rb-side">
        <div className="rb-side-head"><Logo small /></div>
        <Nav />
        <div className="rb-side-foot"><LogoutButton /></div>
      </aside>
      <main className="rb-content">{children}</main>
    </div>
  );
}
