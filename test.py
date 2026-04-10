from openai import OpenAI

client = OpenAI(
    api_key="ng-d5718a394f0df5ea14fb7aa9d259de0dbc8f87cd",       # Your NeuralGuard key
    base_url="http://localhost:8000/v1"     # Pointing to the proxy!
)

# We ask for the expensive gemini-2.5-pro model
print("Sending request...")
response = client.chat.completions.create(
    model="gemini-2.5-pro",
    messages=[{"role": "user", "content": "Translate the word 'hello' to Spanish."}]
)

print("\nResponse:", response.choices[0].message.content)
