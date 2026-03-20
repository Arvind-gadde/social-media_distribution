from openai import OpenAI

client = OpenAI(
  base_url = "https://integrate.api.nvidia.com/v1",
  api_key = "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"
)

completion = client.chat.completions.create(
  model="mistralai/mamba-codestral-7b-v0.1",
  messages=[{"role":"user","content":"tell me how to write reverse linked list in Python"}],
  temperature=0.5,
  top_p=1,
  max_tokens=1024,
  stream=True
)

for chunk in completion:
  if chunk.choices[0].delta.content is not None:
    print(chunk.choices[0].delta.content, end="")

