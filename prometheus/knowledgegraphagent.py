
from typing import List, Dict, Tuple, Union
from rdflib import Graph, URIRef, Literal

class KnowledgeGraphAgent:
    """
    Builds a knowledge graph from a list of concepts.  Handles potential errors robustly.
    """

    def run(self, concepts: List[Dict[str, Union[str, List[str]]]]) -> Tuple[Graph, List[str]]:
        """
        Builds a knowledge graph from a list of concepts.

        Args:
            concepts: A list of dictionaries. Each dictionary represents a concept 
                      with at least a 'uri' key (string URI) and a 'attributes' key (list of strings or dictionary).
                      The attributes can be simple strings or a dictionary with attribute name and value.

        Returns:
            A tuple containing:
                - An rdflib Graph object representing the knowledge graph.  Returns an empty graph if input is invalid or processing fails.
                - A list of error messages encountered during processing.  Returns an empty list if no errors occurred.

        Raises:
            TypeError: if input is not a list of dictionaries.
            ValueError: if a concept dictionary is missing required keys or has incorrectly formatted data.

        """
        if not isinstance(concepts, list):
            raise TypeError("Input must be a list of dictionaries.")

        graph = Graph()
        errors = []

        for concept in concepts:
            try:
                if not isinstance(concept, dict):
                    raise ValueError("Each concept must be a dictionary.")
                if 'uri' not in concept or not isinstance(concept['uri'], str):
                    raise ValueError("Each concept must have a 'uri' key with a string value.")
                if 'attributes' not in concept:
                    raise ValueError("Each concept must have an 'attributes' key.")

                uri = URIRef(concept['uri'])
                attributes = concept['attributes']

                if isinstance(attributes, list): #Simple string attributes
                    for attr in attributes:
                        if isinstance(attr, str):
                            graph.add((uri, URIRef("http://example.org/hasAttribute"), Literal(attr))) #Use a placeholder predicate
                        else:
                            raise ValueError("Attributes must be strings or dictionaries.")


                elif isinstance(attributes, dict): #Attributes with name-value pairs
                    for attr_name, attr_value in attributes.items():
                        if isinstance(attr_value, (str,int,float,bool)): #Handle various data types
                            graph.add((uri, URIRef(f"http://example.org/{attr_name}"), Literal(attr_value)))
                        else:
                            raise ValueError(f"Attribute value for '{attr_name}' must be a string, int, float or bool.")

                else:
                    raise ValueError("Attributes must be a list of strings or a dictionary.")

            except (ValueError, Exception) as e:
                errors.append(f"Error processing concept {concept}: {e}")


        return graph, errors


