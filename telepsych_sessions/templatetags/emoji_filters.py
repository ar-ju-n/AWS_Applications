import re
from django import template
register = template.Library()

# Simple emoji replacement dictionary (expand as needed)
EMOJI_MAP = {
    ':)': '😊',
    ':(': '😞',
    ':D': '😃',
    '<3': '❤️',
    ':P': '😛',
    ':thumbsup:': '👍',
    ':star:': '⭐',
    ':fire:': '🔥',
    ':cry:': '😢',
    ':laugh:': '😂',
}

@register.filter
def emoji_replace(value):
    # Replace text emoji codes with unicode emojis
    s = str(value)
    for code, emoji in EMOJI_MAP.items():
        s = re.sub(re.escape(code), emoji, s)
    return s
