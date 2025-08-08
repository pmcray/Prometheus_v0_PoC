import pytest
from sort_list_of_tuples import sort_list_of_tuples

def test_sort_tuples():
    assert sort_list_of_tuples([(1, 2), (3, 1), (5, 4)]) == [(3, 1), (1, 2), (5, 4)]