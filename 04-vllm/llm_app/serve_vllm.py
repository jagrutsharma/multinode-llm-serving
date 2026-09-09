# Imports
from ray.serve.llm import LLMConfig, build_openai_app

# Model loading config
llm_config = LLMConfig(
    model_loading_config={
        "model_id": "qwen-0.5b",
        "model_source": "Qwen/Qwen2.5-0.5B-Instruct",
    },
    accelerator_type="T4",
    engine_kwargs={"dtype": "float16"},
    deployment_config={
        "ray_actor_options": {
            "num_cpus": 1,
        },
        "autoscaling_config": {
            "min_replicas": 1,
            "max_replicas": 1,
        },
    },
)

app = build_openai_app({"llm_configs": [llm_config]})
