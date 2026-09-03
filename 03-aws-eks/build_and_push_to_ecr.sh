echo "*** Building ***"
docker build --platform linux/amd64 -t 722323574575.dkr.ecr.us-east-1.amazonaws.com/multinode-llm-serving/ray-qwen-gpu:latest .

echo "*** Pushing ***"
docker push 722323574575.dkr.ecr.us-east-1.amazonaws.com/multinode-llm-serving/ray-qwen-gpu:latest