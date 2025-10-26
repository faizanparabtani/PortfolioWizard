from huggingface_hub import InferenceClient, login
import json
from dotenv import load_dotenv
import os

load_dotenv()

client = InferenceClient(
    provider="nebius",
    api_key=os.getenv("HUGGING_FACE_API")
)

completion = client.chat.completions.create(
    model="deepseek-ai/DeepSeek-R1-0528",
    messages=[
        {
            "role": "user",
            "content": "What is the capital of France?"
        }
    ],
)

print(completion.choices[0].message)


