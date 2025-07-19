
import spacy
from typing import List, Tuple, Dict

class ConceptFormationAgent:
    """
    Extracts key concepts from a document using spaCy's named entity recognition and noun chunk extraction.  Handles potential errors gracefully.
    """

    def __init__(self, nlp_model="en_core_web_sm"):
        """
        Initializes the agent with a specified spaCy model. Defaults to 'en_core_web_sm'.  
        Raises OSError if the model is not found.
        """
        try:
            self.nlp = spacy.load(nlp_model)
        except OSError as e:
            raise OSError(f"Error loading spaCy model '{nlp_model}': {e}. Please ensure it's installed: python -m spacy download {nlp_model}")


    def run(self, text: str) -> Tuple[List[str], List[str]]:
        """
        Extracts key concepts from the input text.

        Args:
            text: The input text document.

        Returns:
            A tuple containing two lists:
                - A list of named entities (e.g., persons, organizations, locations).
                - A list of noun chunks representing key concepts.

            Returns ([], []) if the input is invalid or empty after cleaning.
        """
        if not isinstance(text, str) or not text.strip():
            return [], []

        try:
            doc = self.nlp(text)
            named_entities = [ent.text for ent in doc.ents]
            noun_chunks = [chunk.text for chunk in doc.noun_chunks]
            return named_entities, noun_chunks
        except Exception as e: #Catch any unexpected spaCy errors.
            print(f"An error occurred during concept extraction: {e}")
            return [], []


#Example Usage
agent = ConceptFormationAgent()
text = "Apple is looking at buying U.K. startup for $1 billion"
named_entities, noun_chunks = agent.run(text)
print("Named Entities:", named_entities)
print("Noun Chunks:", noun_chunks)


text2 = "" #test empty string
named_entities, noun_chunks = agent.run(text2)
print("Named Entities:", named_entities)
print("Noun Chunks:", noun_chunks)

text3 = 123 # test invalid input
named_entities, noun_chunks = agent.run(text3)
print("Named Entities:", named_entities)
print("Noun Chunks:", noun_chunks)


# Example demonstrating error handling for missing model
try:
    agent_missing_model = ConceptFormationAgent(nlp_model="en_core_web_nonexistent")
except OSError as e:
    print(f"Caught expected error: {e}")

