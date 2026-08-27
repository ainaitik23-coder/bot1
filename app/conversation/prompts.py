"""
app/conversation/prompts.py

Reads the .txt files in prompts/ and assembles the final system prompt +
message history that gets sent to the LLM. Edit the .txt files to change
behavior -- no code changes needed.
"""

from pathlib import Path

from app.database.models import Memory, Message

PROMPTS_DIR = Path(__file__).resolve().parent.parent.parent / "prompts"


def _read(filename: str) -> str:
    path = PROMPTS_DIR / filename
    if not path.exists():
        return ""
    return path.read_text(encoding="utf-8").strip()


def build_system_prompt(username: str | None, memories: list[Memory]) -> str:
    parts = [
        _read("system_prompt.txt"),
        _read("personality.txt"),
        _read("conversation_rules.txt"),
    ]

    if username:
        parts.append(f"You are talking to Instagram user: {username}")

    if memories:
        memory_lines = "\n".join(f"- {m.key}: {m.value}" for m in memories)
        parts.append(f"Known facts about this user (use naturally, don't recite them):\n{memory_lines}")

    return "\n\n".join(p for p in parts if p)


def build_messages(
    username: str | None,
    memories: list[Memory],
    history: list[Message],
    current_message: str,
) -> list[dict]:
    """Final message list in the format app/ai providers expect."""
    messages = [{"role": "system", "content": build_system_prompt(username, memories)}]

    for msg in history:
        role = "user" if msg.direction == "in" else "assistant"
        messages.append({"role": role, "content": msg.content})

    messages.append({"role": "user", "content": current_message})
    return messages
