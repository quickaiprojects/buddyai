"""
Talks to the local Ollama server. Handles tool-calling: if the model wants
to call a tool, this executes it via tools.py, feeds the result back in,
and returns the final natural-language reply.
"""

from ollama import chat
import tools


def get_reply(conversation, model_name: str) -> str:
    messages = conversation.as_ollama_messages()

    response = chat(
        model=model_name,
        messages=messages,
        tools=tools.get_schemas(),
    )

    msg = response.message

    if msg.tool_calls:
        conversation.messages.append(
            {"role": "assistant", "content": msg.content or "", "tool_calls": msg.tool_calls}
        )
        for call in msg.tool_calls:
            name = call.function.name
            args = call.function.arguments or {}
            result = tools.execute(name, args)
            conversation.add_tool_result(name, result)

        follow_up = chat(
            model=model_name,
            messages=conversation.as_ollama_messages(),
        )
        final_text = follow_up.message.content
        conversation.add_assistant(final_text)
        return final_text

    final_text = msg.content
    conversation.add_assistant(final_text)
    return final_text


def stream_reply(conversation, model_name: str):
    """
    Generator version of get_reply for live UI updates. Yields tuples:
      ("thinking", text_delta)  - a piece of the model's reasoning, as it streams
      ("content", text_delta)   - a piece of the final answer, as it streams
      ("done", full_text)       - the complete final answer, once finished

    If the model calls a tool mid-stream, this finishes the tool call and
    fetches the follow-up reply as a single (non-streamed) call, since tool
    call results are usually short and don't benefit much from streaming.
    """
    messages = conversation.as_ollama_messages()
    stream = chat(
        model=model_name,
        messages=messages,
        tools=tools.get_schemas(),
        stream=True,
        think=True,
    )

    content_parts = []
    tool_calls = None

    for chunk in stream:
        msg = chunk.message
        thinking_delta = getattr(msg, "thinking", None)
        if thinking_delta:
            yield ("thinking", thinking_delta)
        if msg.content:
            content_parts.append(msg.content)
            yield ("content", msg.content)
        if msg.tool_calls:
            tool_calls = msg.tool_calls

    if tool_calls:
        conversation.messages.append(
            {"role": "assistant", "content": "".join(content_parts), "tool_calls": tool_calls}
        )
        for call in tool_calls:
            name = call.function.name
            args = call.function.arguments or {}
            result = tools.execute(name, args)
            conversation.add_tool_result(name, result)

        follow_up = chat(model=model_name, messages=conversation.as_ollama_messages())
        final_text = follow_up.message.content
        conversation.add_assistant(final_text)
        yield ("done", final_text)
        return

    final_text = "".join(content_parts)
    conversation.add_assistant(final_text)
    yield ("done", final_text)
