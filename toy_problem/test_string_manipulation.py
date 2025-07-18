import pytest

def string_manipulation(input_string, operation, value=""):
    """
    Performs simple string manipulations.

    Args:
      input_string: The input string.
      operation: The operation to perform ('uppercase', 'lowercase', 'prefix', 'suffix', 'reverse').
      value:  The value to use for prefix/suffix operations.

    Returns:
      The manipulated string or the original string if the operation is invalid.  Returns an error message if there's a problem with the input.

    """
    if not isinstance(input_string, str):
        return "Error: Input string must be a string."
    
    if operation == 'uppercase':
        return input_string.upper()
    elif operation == 'lowercase':
        return input_string.lower()
    elif operation == 'prefix':
        return value + input_string
    elif operation == 'suffix':
        return input_string + value
    elif operation == 'reverse':
        return input_string[::-1]
    else:
        return input_string

def test_uppercase():
    assert string_manipulation("hello", "uppercase") == "HELLO"

def test_lowercase():
    assert string_manipulation("HeLlO", "lowercase") == "hello"

def test_prefix():
    assert string_manipulation("world", "prefix", "Hello ") == "Hello world"

def test_suffix():
    assert string_manipulation("world", "suffix", "!") == "world!"

def test_reverse():
    assert string_manipulation("hello", "reverse") == "olleh"

def test_invalid_operation():
    assert string_manipulation("test", "invalid") == "test"

def test_non_string_input():
    assert string_manipulation(123, "uppercase") == "Error: Input string must be a string."

def test_empty_string():
    assert string_manipulation("", "uppercase") == ""

def test_prefix_empty_value():
    assert string_manipulation("test", "prefix") == "test"

def test_suffix_empty_value():
    assert string_manipulation("test", "suffix") == "test"

def test_reverse_empty_string():
    assert string_manipulation("", "reverse") == ""
