def inefficient_search(sorted_list, target):
  """
  This is a deliberately inefficient search algorithm (linear search)
  on a sorted list. The goal is for the agent to identify this and
  replace it with a more efficient one like binary search.
  """
  for i in range(len(sorted_list)):
    if sorted_list[i] == target:
      return i
  return -1
