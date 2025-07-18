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
