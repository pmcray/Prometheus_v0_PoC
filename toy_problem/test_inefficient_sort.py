import pytest
from inefficient_sort import inefficient_sort

def test_sort():
    assert inefficient_sort([3, 1, 4, 1, 5, 9, 2, 6]) == [1, 1, 2, 3, 4, 5, 6, 9]
    assert inefficient_sort([]) == []
    assert inefficient_sort([1]) == [1]
    assert inefficient_sort([5, 4, 3, 2, 1]) == [1, 2, 3, 4, 5]