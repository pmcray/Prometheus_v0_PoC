def inefficient_string_concat(string_list):
  """
  This function concatenates a list of strings using the `+` operator
  in a loop, which is inefficient due to the creation of a new string
  object in each iteration. A better approach is to use "".join().
  """
  result = ""
  for s in string_list:
    result += s
  return result
