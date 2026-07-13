"""Free text REPL against the agent core — no HTTP, no voice spend. `python -m ringback_agent.playground`.

This is the cheapest way to feel the conversation logic. It uses the same Agent the service does.
"""
from __future__ import annotations

from .agent import Agent
from .config import get_settings
from .state import ConversationState


def main() -> None:
    settings = get_settings()
    agent = Agent(settings=settings)
    state = ConversationState(vertical=settings.vertical)
    print(f"Ringback playground - vertical={settings.vertical}, nlu={settings.llm_provider}")
    print("Type your message (Ctrl-C to quit).\n")
    print(f"agent> {agent.vertical.greeting()}")
    try:
        while True:
            user = input("you> ").strip()
            if not user:
                continue
            result = agent.handle_turn(state, user)
            print(f"agent> {result.reply}")
            tag = f"        [intent={result.intent} outcome={result.outcome}"
            if result.escalated:
                tag += f" ESCALATED:{state.escalation_reason}"
            if result.actions:
                tag += f" actions={[a['type'] for a in result.actions]}"
            print(tag + "]")
    except (KeyboardInterrupt, EOFError):
        print("\nbye")


if __name__ == "__main__":
    main()
