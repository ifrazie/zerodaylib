import os

from aws_bedrock_token_generator import provide_token
from strands.models.openai import OpenAIModel

MODEL_ID = "google.gemma-4-31b"


def load_model():
    """
    Get a Bedrock Mantle model client. These OpenAI-compatible models (e.g. openai.gpt-5.5,
    openai.gpt-oss-120b) are served via the Bedrock Mantle endpoint, NOT the Converse API — so they
    are invoked through an OpenAI-style client authenticated with a short-lived Bedrock bearer token.
    Region is read from AWS_REGION (set by the AgentCore runtime).
    """
    region = os.environ.get("AWS_REGION", os.environ.get("AWS_DEFAULT_REGION", "us-east-1"))
    token = provide_token(region=region)
    # Open-source OpenAI models (gpt-oss-*) only work on the /v1 Mantle path.
    base_url = f"https://bedrock-mantle.{region}.api.aws/v1"
    client_args = {"api_key": token, "base_url": base_url}

    params = {}
    params["max_completion_tokens"] = 2000
    params["temperature"] = 0.10000000149011612
    params["top_p"] = 0.8999999761581421
    return OpenAIModel(client_args=client_args, model_id=MODEL_ID, params=params)
