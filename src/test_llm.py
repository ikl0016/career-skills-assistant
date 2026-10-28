import os
from dotenv import load_dotenv
from openai import OpenAI

load_dotenv()
client = OpenAI(base_url=os.environ["LLM_BASE_URL"],
                api_key=os.environ["LLM_API_KEY"])

resp = client.chat.completions.create(
    model=os.environ["LLM_MODEL"],
    messages=[{"role": "user", "content": "Say hello in five words."}],
    temperature=0,
)
print(resp.choices[0].message.content)
print("tokens used:", resp.usage.total_tokens)
