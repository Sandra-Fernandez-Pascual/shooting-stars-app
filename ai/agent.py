"""Send the chat history to Grok and return the text reply.

This module does not call weather or astronomy tools. Python already
calculated the results; they are included in the system message.
"""

import streamlit as st
from openai import OpenAI


def agent(messages):
    """Ask Grok to reply to the conversation.

    Args:
        messages (list): OpenAI-style dicts with role and content.
            The first message should be the system prompt plus results.

    Returns:
        str: Grok's reply, or an error sentence if the API key is missing.
    """
    try:
        api_key = st.secrets.get("XAI_API_KEY")
    except st.errors.StreamlitSecretNotFoundError:
        api_key = None
    if not api_key:
        return (
            "I cannot chat right now because XAI_API_KEY is missing. "
            "The viewing results above are still valid."
        )

    client = OpenAI(
        api_key=api_key,
        base_url="https://api.x.ai/v1",
    )
    completion = client.chat.completions.create(
        model="grok-3-mini",
        messages=messages,
    )
    return completion.choices[0].message.content
