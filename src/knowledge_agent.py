import google.generativeai as genai
import os
import re
import json
from src.performance_logger import PerformanceLogger
from src.tools import PDFTool

class KnowledgeAgent:
    def __init__(self, api_key, performance_logger: PerformanceLogger, pdf_tool: PDFTool):
        genai.configure(api_key=api_key)
        self.model = genai.GenerativeModel('gemini-1.5-flash')
        self.performance_logger = performance_logger
        self.pdf_tool = pdf_tool
        self.structured_knowledge = {}

    def ingest_paper(self, file_path):
        """
        Ingests a scientific paper from a PDF, extracts the text, and structures it.
        """
        print(f"KnowledgeAgent: Ingesting paper from {file_path}")
        text = self.pdf_tool.use(file_path)
        if not text:
            return False
        
        prompt = f"""
        You are a research assistant. Your task is to read the following text from a scientific paper
        and structure its key findings into a JSON object.
        
        The JSON object should have the following fields:
        - "title": The title of the paper.
        - "hypothesis": A one-sentence summary of the paper's main hypothesis.
        - "method": A one-sentence summary of the methodology used.
        - "results": A one-sentence summary of the key results.
        
        Text:
        {text}
        
        Please provide only the JSON object.
        """
        
        response = self.model.generate_content(prompt)
        try:
            # Clean the response to get only the JSON
            json_str = re.search(r"\{.*\}", response.text, re.DOTALL).group(0)
            self.structured_knowledge[file_path] = json.loads(json_str)
            print("KnowledgeAgent: Successfully structured knowledge from paper.")
            return True
        except (AttributeError, json.JSONDecodeError) as e:
            print(f"KnowledgeAgent: Error structuring knowledge: {e}")
            return False

    def query_knowledge(self, file_path, query):
        """
        Queries the structured knowledge for a given paper.
        """
        if file_path not in self.structured_knowledge:
            return "I have not yet ingested that paper."
        
        knowledge = self.structured_knowledge[file_path]
        
        # For the PoC, we'll just use the LLM to answer the query based on the JSON.
        prompt = f"""
        You are a research assistant. Answer the following query based on the provided structured knowledge.
        
        Knowledge:
        {json.dumps(knowledge, indent=4)}
        
        Query: {query}
        """
        response = self.model.generate_content(prompt)
        return response.text.strip()

    # ... (rest of the class is unchanged)
    def read_proof(self, file_path):
        pass
    def _clean_code(self, code):
        pass
    def generate_benchmark(self):
        pass
    def generate_theorem(self):
        pass