
import os
import glob

class SystemState:
    def __init__(self, src_directory="src"):
        self.src_directory = src_directory
        self.source_code = self._load_source_code()

    def _load_source_code(self):
        """
        Loads all Python files from the source directory into a dictionary.
        """
        source_files = {}
        for filepath in glob.glob(os.path.join(self.src_directory, "*.py")):
            with open(filepath, 'r') as f:
                source_files[filepath] = f.read()
        return source_files

    def get_source_code(self):
        return self.source_code

    def __str__(self):
        return str(self.source_code)
