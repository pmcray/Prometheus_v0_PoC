def inefficient_sum(numbers):
  """
  This function sums a list of numbers using a loop, which is less
  efficient than the built-in sum() function in Python.
  """
  total = 0
  for number in numbers:
    total += number
  return total
