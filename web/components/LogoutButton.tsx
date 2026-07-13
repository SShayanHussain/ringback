"use client";

// Interactive bit extracted into a client component (Server→Client boundary rule, PLAYBOOK §6).
export function LogoutButton() {
  return (
    <form action="/logout" method="post">
      <button className="rb-btn rb-btn-ghost" type="submit" style={{ width: "100%" }}>
        Log out
      </button>
    </form>
  );
}
