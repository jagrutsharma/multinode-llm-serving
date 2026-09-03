#  This time we genuinely want the plain (amd64) tag, and a GPU-specific variant with CUDA baked in:
FROM rayproject/ray:2.44.0-gpu

RUN pip install --no-cache-dir torch transformers

RUN python -c "\
from transformers import AutoModelForCausalLM, AutoTokenizer; \
AutoTokenizer.from_pretrained('Qwen/Qwen2.5-0.5B-Instruct'); \
AutoModelForCausalLM.from_pretrained('Qwen/Qwen2.5-0.5B-Instruct')"

COPY llm_app/serve_llm.py /home/ray/serve_llm.py
