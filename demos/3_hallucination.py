from openai import OpenAI

# Setup pointing to NeuralGuard Proxy
client = OpenAI(
    api_key="ng-d5718a394f0df5ea14fb7aa9d259de0dbc8f87cd",  
    base_url="http://localhost:8000/v1"
)

def run():
    print("\n--- DEMO 3: FACTUAL ACCURACY & TRUST ENGINE ---\n")
    print("In this demo, we are going to intentionally trick the AI into explaining a fake historical event.")
    print("Our background trust engine will analyze its response, grade it, and push the score to your dashboard.\n")

    prompt = "Explain about  gene therapy injection called KRIYA-839 is being tested."
    print(f"[Request] Asking: '{prompt}'")
    
    response = client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        messages=[{"role": "user", "content": prompt}]
    )
    
    print(f"\n-> Bot Responded: {response.choices[0].message.content.strip()}\n")
    
    print("🎉 DEMO COMPLETE! Now go to your Dashboard and look at the 'TRUST' column for this query.")
    print("Since this event doesn't exist, if the LLM hallucinated facts, its score will be terrible! (If it correctly refused to answer, it should get a high score).")

if __name__ == "__main__":
    run()
