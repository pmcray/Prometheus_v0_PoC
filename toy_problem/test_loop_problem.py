import pytest
from loop_problem import sum_of_squares

def test_sum_of_squares():
    assert sum_of_squares(4) == 14 # 0*0 + 1*1 + 2*2 + 3*3 = 0 + 1 + 4 + 9 = 14
    assert sum_of_squares(1) == 0
    assert sum_of_squares(0) == 0
