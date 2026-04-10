import time
from openai import OpenAI

# Setup pointing to NeuralGuard Proxy
client = OpenAI(
    api_key="ng-d5718a394f0df5ea14fb7aa9d259de0dbc8f87cd",  
    base_url="http://localhost:8000/v1"
)

def run():
    print("\n--- DEMO 1: SEMANTIC CACHING MAGIC ---\n")
    
    # 1. First Request (Cache Miss)
    prompt_1 = "Can you make a short 2-line rhyme about coding in Python?"
    print(f"[Request 1] Asking: '{prompt_1}'")
    start = time.time()
    
    response = client.chat.completions.create(
        model="gemini-2.5-pro",
        messages=[{"role": "user", "content": prompt_1}]
    )
    
    time_1 = round(time.time() - start, 2)
    print(f"-> Response: {response.choices[0].message.content.strip()}")
    print(f"-> Time Taken: {time_1} seconds\n")
    
    time.sleep(1) # Give you a second to read

    # 2. Second Request (Semantically Similar -> Cache Hit)
    prompt_2 = "Please write me a quick two line rhyming poem about Python programming."
    print(f"[Request 2] Asking: '{prompt_2}' (Semantically identical to Request 1!)")
    start = time.time()
    
    response2 = client.chat.completions.create(
        model="gemini-2.5-pro",
        messages=[{"role": "user", "content": prompt_2}]
    )
    
    time_2 = round(time.time() - start, 2)
    print(f"-> Response: {response2.choices[0].message.content.strip()}")
    print(f"-> Time Taken: {time_2} seconds")
    
    if time_2 < 1.5:
        print("\n🎉 CACHE HIT SUCCESS! Notice how the second response was returned practically instantly!")
    else:
        print("\nDidn't hit cache? Make sure Redis is running!")

if __name__ == "__main__":
    run()
