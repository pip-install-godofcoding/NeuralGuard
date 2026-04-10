from openai import OpenAI

# Setup pointing to NeuralGuard Proxy
client = OpenAI(
    api_key="ng-d5718a394f0df5ea14fb7aa9d259de0dbc8f87cd",  
    base_url="http://localhost:8000/v1"
)

def run():
    print("\n--- DEMO 2: HEURISTIC COST SHIELD ---\n")
    print("In this demo, we intentionally ask for the very expensive 'gemini-2.5-pro' model both times.")
    print("Watch the Dashboard to see what the proxy actually uses behind the scenes based on complexity!\n")

    # 1. Simple request -> Should be downgraded
    print("[Test A] Simple Translation Task")
    print("Prompt: 'Translate \"Good morning everyone\" to French.'")
    response_simple = client.chat.completions.create(
        model="gemini-2.5-pro", # Requesting expensive build!
        messages=[{"role": "user", "content": "Translate \"Good morning everyone\" to French."}]
    )
    print(f"-> Result: {response_simple.choices[0].message.content.strip()}\n")

    # 2. Complex request -> Should stay on Pro
    print("[Test B] Complex Reasoning Task")
    print("Prompt: 'Write a comprehensive multi-threaded python script using asyncio that manages a generic connection pool...'")
    response_complex = client.chat.completions.create(
        model="gemini-2.5-pro", # Requesting expensive build!
        messages=[{"role": "user", "content": "Write a comprehensive multi-threaded python script using asyncio that manages a generic connection pool for 5 databases simultaneously, with exponential backoff for disconnects. Make it print out verbose logs."}]
    )
    print(f"-> Result: [A long complex python script was generated successfully.]\n")

    print("🎉 DEMO COMPLETE! Now go look at the 'Recent Queries' table in your Dashboard!")
    print("Notice how Test A was downgraded to 'gemini-2.5-flash', saving you money, while Test B was allowed to use the expensive 'gemini-2.5-pro' model because it was complex!")

if __name__ == "__main__":
    run()
