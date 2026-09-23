"""Check that the configured Gemini model can receive a backend-only request."""

import os
from pathlib import Path

from dotenv import load_dotenv
from google import genai


MODEL_NAME = "gemini-3.6-flash"

load_dotenv(Path(__file__).resolve().parent.parent / ".env")


def main() -> None:
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        raise RuntimeError("GEMINI_API_KEY is not set in the local .env file.")

    client = genai.Client(api_key=api_key)
    response = client.models.generate_content(
        model=MODEL_NAME,
        contents="Відповідай одним реченням: Gemini API працює?",
    )
    print(response.text)


if __name__ == "__main__":
    main()
