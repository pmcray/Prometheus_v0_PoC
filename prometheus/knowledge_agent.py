
import google.generativeai as genai
import os
import re
import json
from .performance_logger import PerformanceLogger
from .tools import PDFTool

class KnowledgeAgent:
    def __init__(self, api_key, performance_logger: PerformanceLogger, pdf_tool: PDFTool):
        genai.configure(api_key=api_key)
        self.model = genai.GenerativeModel('gemini-1.5-flash')
        self.performance_logger = performance_logger
        self.pdf_tool = pdf_tool
        self.structured_knowledge = {}

    def ingest_rules(self, file_path):
        print(f"KnowledgeAgent: Ingesting rules from {file_path}")
        text = self.pdf_tool.use(file_path)
        if not text:
            return False
        prompt = f"Summarize the rules described in this text in one sentence: {text}"
        response = self.model.generate_content(prompt)
        self.structured_knowledge["rules"] = response.text.strip()
        print("KnowledgeAgent: Successfully ingested rules.")
        return True

    def get_rules(self):
        return self.structured_knowledge.get("rules", "No rules have been ingested.")
