import torch
from ray import serve
from starlette.requests import Request
from transformers import AutoModelForCausalLM, AutoTokenizer

MODEL_NAME = ("Qwen/Qwen2.5-0.5B-Instruct")

@serve.deployment
class QwenChat:
    def __init__(self):
        self.tokenizer = AutoTokenizer.from_pretrained(MODEL_NAME)
        self.model = AutoModelForCausalLM.from_pretrained(MODEL_NAME, torch_dtype=torch.float16).to("cuda")
        self.model.eval()

    async def __call__(self, request: Request) -> dict:
        payload = await request.json()
        prompt = payload.get("prompt", "")
        max_new_tokens = payload.get("max_new_tokens", 128)

        messages = [{"role": "user", "content": prompt}]
        chat_text = self.tokenizer.apply_chat_template(
            messages, tokenize=False, add_generation_prompt=True
        )
        inputs = self.tokenizer(chat_text, return_tensors="pt").to("cuda")

        with torch.no_grad():
            output_ids = self.model.generate(
                **inputs,
                max_new_tokens=max_new_tokens,
                do_sample=False,
                pad_token_id=self.tokenizer.eos_token_id,
            )

        generated_ids = output_ids[0][inputs["input_ids"].shape[-1]:]
        response = self.tokenizer.decode(generated_ids, skip_special_tokens=True)
        return {"response": response}


app = QwenChat.bind()
