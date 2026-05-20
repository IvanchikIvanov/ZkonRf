import asyncio

from bot.handlers.text_handler import handle_help


class FakeMessage:
    def __init__(self):
        self.replies = []

    async def reply_text(self, text, **kwargs):
        self.replies.append(text)


class FakeUpdate:
    def __init__(self):
        self.message = FakeMessage()


def test_help_lists_only_registered_commands():
    update = FakeUpdate()

    asyncio.run(handle_help(update, object()))

    help_text = update.message.replies[0]
    assert "/templates" in help_text
    assert "/cancel_doc" in help_text
    assert "/country" not in help_text
    assert "/countries" not in help_text

