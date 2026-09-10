import gradio as gr
from openai import OpenAI

# Assumes: kubectl port-forward svc/rayservice-vllm-serve-svc 8000:8000
# ray.serve.llm exposes an OpenAI-compatible API, so the OpenAI client works directly --
# api_key is unchecked by our endpoint (no auth configured) but the client requires a
# non-empty string.
client = OpenAI(base_url="http://localhost:8000/v1", api_key="not-needed")

MODEL_ID = "qwen-0.5b"  # must match model_loading_config.model_id in serve_vllm.py


def extract_content(content):
    # Gradio's "messages" format sometimes stores content as a list of content-part
    # dicts (e.g. [{"type": "text", "text": "..."}]), mirroring OpenAI's multimodal
    # content-parts shape -- but ray.serve.llm's server-side Message model only
    # accepts a plain string. Flatten back down to text.
    if isinstance(content, list):
        return "".join(part.get("text", "") for part in content if isinstance(part, dict))
    return content


def to_messages(history):
    # Gradio's ChatInterface history format varies by version: either a list of
    # [user_msg, bot_msg] pairs (older "tuples" format) or a flat list of
    # {"role": ..., "content": ...} dicts (newer "messages" format). Handle both rather
    # than assume one.
    messages = []
    for turn in history:
        if isinstance(turn, dict):
            messages.append({"role": turn["role"], "content": extract_content(turn["content"])})
        else:
            user_msg, bot_msg = turn
            messages.append({"role": "user", "content": extract_content(user_msg)})
            if bot_msg is not None:
                messages.append({"role": "assistant", "content": extract_content(bot_msg)})
    return messages


def chat(message, history):
    # The model is stateless between calls -- there's no server-side session, so the
    # entire conversation gets resent and reprocessed on every request. Role-tagged
    # turns (user/assistant) matter, not just concatenated text: Qwen was trained on
    # exactly this alternating structure via its chat template.
    messages = to_messages(history) + [{"role": "user", "content": message}]
    response = client.chat.completions.create(
        model=MODEL_ID,
        messages=messages,
        max_tokens=128,
    )
    return response.choices[0].message.content


gr.ChatInterface(
    chat,
    title="Qwen2.5-0.5B on Ray Serve + vLLM (AWS EKS, GPU)",
    description="Unlike phase 3's chat UI, this sends the full conversation history with "
                 "each request -- the OpenAI-compatible API supports multi-turn messages "
                 "natively, so the model can now recall earlier turns in the session.",
).launch()
