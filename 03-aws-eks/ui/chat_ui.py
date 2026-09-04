import gradio as gr
import requests

# Assumes: kubectl port-forward svc/rayservice-sample-serve-svc 8000:8000
RAY_SERVE_URL = "http://localhost:8000/generate"


def chat(message, history):
    response = requests.post(RAY_SERVE_URL, json={"prompt": message, "max_new_tokens": 128})
    response.raise_for_status()
    return response.json()["response"]


gr.ChatInterface(
    chat,
    title="Qwen2.5-0.5B on Ray Serve (AWS EKS, GPU)",
    description="Each message is sent as a standalone prompt -- serve_llm.py doesn't track "
                 "conversation history server-side, so the model won't remember earlier turns.",
).launch()
