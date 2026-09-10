FROM rayproject/ray:2.44.0-gpu

RUN pip install --no-cache-dir "ray[llm]==2.44.0"

RUN python -c "from huggingface_hub import snapshot_download; snapshot_download('Qwen/Qwen2.5-0.5B-Instruct')"

COPY llm_app/serve_vllm.py /home/ray/serve_vllm.py