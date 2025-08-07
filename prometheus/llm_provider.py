import google.generativeai as genai

class LLMProvider:
    def __init__(self, api_key: str, model_name: str = 'gemini-1.5-flash'):
        genai.configure(api_key=api_key)
        self.model = genai.GenerativeModel(model_name)

    def generate_content(self, prompt: str) -> str:
        response = self.model.generate_content(prompt)
        return response.text.strip()
