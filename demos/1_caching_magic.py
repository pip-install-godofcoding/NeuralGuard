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
    prompt_1 = "Summarize the Q3 2023 revenue impact of the 'Project Zephyr' supply chain overhaul implemented by Maersk. Please provide the exact percentage of cost reduction and the dollar amount saved as cited in their November 2023 investor briefing."
    print(f"[Request 1] Asking: '{prompt_1}'")
    start = time.time()
    
    response = client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        messages=[{"role": "user", "content": prompt_1}]
    )
    
    time_1 = round(time.time() - start, 2)
    print(f"-> Response: {response.choices[0].message.content.strip()}")
    print(f"-> Time Taken: {time_1} seconds\n")
    
    time.sleep(1) # Give you a second to read

    # 2. Second Request (Semantically Similar -> Cache Hit)
    prompt_2 = "Can you give me a summary of Maersk's Project Zephyr supply chain overhaul and its effect on Q3 2023 revenue? I need the specific dollar savings and cost reduction percentage from the Nov 2023 investor brief."
    print(f"\n[Request 2] Asking: '{prompt_2}' (Semantically similar to Request 1!)")
    start = time.time()
    
    response2 = client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        messages=[{"role": "user", "content": prompt_2}]
    )
    
    time_2 = round(time.time() - start, 2)
    print(f"-> Response: {response2.choices[0].message.content.strip()}")
    print(f"-> Time Taken: {time_2} seconds")
    
    if time_2 < 1.5:
        print("\nCACHE HIT SUCCESS! Notice how the second response was returned practically instantly!")
    else:
        print("\nDidn't hit cache? Make sure Redis is running!")

if __name__ == "__main__":
    run()
