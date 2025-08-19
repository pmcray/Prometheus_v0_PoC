def sum_of_squares(n):
    """
    Calculates the sum of squares of numbers from 0 to n-1.
    This implementation uses an inefficient loop.
    """
    total = 0
    for i in range(n):
        total += i * i
    return total
