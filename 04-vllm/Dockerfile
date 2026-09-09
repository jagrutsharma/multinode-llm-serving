FROM rayproject/ray:2.44.0-gpu

RUN pip install --no-cache-dir "ray[llm]==2.44.0"

COPY llm_app/serve_vllm.py /home/ray/serve_vllm.py