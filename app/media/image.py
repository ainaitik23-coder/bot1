"""
app/media/image.py

STUB -- built out in Phase 19.

Will handle: downloading an image the user sent via Instagram DM,
passing it to a vision-capable model (Gemini supports vision natively),
and storing a media reference in the messages table (not the raw image,
per the "avoid storing unnecessary sensitive media" rule from the spec).
"""


async def handle_incoming_image(media_url: str) -> str:
    """Placeholder -- returns a message so the bot doesn't silently ignore images."""
    return "Abhi main sirf text samajh sakta hoon, image support jaldi aa raha hai!"
