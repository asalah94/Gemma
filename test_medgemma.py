

from medgemma import medgemma_get_text_response

if __name__ == "__main__":

    # Sample chat messages
    messages = [
        {"role": "system", "content": "You are a helpful medical assistant."},
        {"role": "user", "content": "What are the symptoms of diabetes?"}
    ]

    try:
        response = medgemma_get_text_response(
            messages=messages,
            temperature=0.1,
            max_tokens=512
        )

        print("\n=== MedGemma Response ===\n")
        print(response)

    except Exception as e:
        print(f"Test failed: {e}")

