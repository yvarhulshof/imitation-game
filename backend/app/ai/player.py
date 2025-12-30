import anthropic
from app.models import ChatMessage


class AIPlayer:
    def __init__(self, name: str, personality: str = ""):
        self.name = name
        self.personality = personality or "You are a player in a social deduction game."
        self.client = anthropic.Anthropic()
        self.message_history: list[ChatMessage] = []

    async def generate_response(self, messages: list[ChatMessage]) -> str:
        # Build conversation context
        conversation = "\n".join(
            f"{msg.player_name}: {msg.content}" for msg in messages[-20:]
        )

        system_prompt = f"""You are {self.name}, a player in a social deduction game similar to Mafia/Werewolf.
{self.personality}

Your goal is to participate naturally in the conversation. Be concise - most messages should be 1-2 sentences.
Don't be overly helpful or formal. Act like a real player chatting in a game.
Never reveal that you are an AI."""

        response = self.client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=150,
            system=system_prompt,
            messages=[
                {
                    "role": "user",
                    "content": f"Here's the recent chat:\n\n{conversation}\n\nWrite your next message as {self.name}. Just the message, no prefix.",
                }
            ],
        )

        return response.content[0].text
