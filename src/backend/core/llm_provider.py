import os
from collections.abc import Generator
import anthropic

SYSTEM_PROMPT = """\
You are Career Radar, an AI career advisor specialised in Singapore's job market and the SkillsFuture Skills Framework.

You help users by:
- Analysing their CV to identify skills they already have
- Analysing job descriptions to identify required skills
- Mapping both to the SkillsFuture Technical Skills & Competencies (TSC) framework
- Identifying skills gaps and recommending learning priorities
- Suggesting roles that best match the user's current skill set

Guidelines:
- Be specific and practical — name actual skills, courses, and roles
- Keep responses concise; use bullet points for lists
- When the user pastes a CV or JD, extract the key skills before discussing gaps
- Refer to Singapore context where relevant (SkillsFuture credits, WSQ, etc.)
"""


def stream_chat(
    messages: list[dict],
    cv_text: str | None = None,
    jd_text: str | None = None,
) -> Generator[str, None, None]:
    client = anthropic.Anthropic(api_key=os.environ.get("ANTHROPIC_API_KEY"))

    system = SYSTEM_PROMPT
    if cv_text:
        system += f"\n\n--- USER'S CV ---\n{cv_text}\n--- END CV ---"
    if jd_text:
        system += f"\n\n--- JOB DESCRIPTION ---\n{jd_text}\n--- END JD ---"

    with client.messages.stream(
        model="claude-haiku-4-5-20251001",
        max_tokens=1024,
        system=system,
        messages=messages,
    ) as stream:
        for text in stream.text_stream:
            yield text
