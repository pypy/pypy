import autopath
from pypy.tool.algo.sparsemat import *


def test_sparsemat1():
    import py
    M = SparseMatrix(4)
    M[0,0] = M[1,1] = M[2,2] = M[3,3] = 1
    M[0,1] = -1.0
    M[1,2] = M[1,3] = -0.5
    M[2,1] = -1.0
    res = M.solve([4, 5, 4, 1])
    assert res == [19, 15, 19, 1]

def test_sparsemat2():
    import py
    M = SparseMatrix(4)
    M[0,0] = M[1,1] = M[2,2] = M[3,3] = 1
    M[0,1] = -1.0
    M[1,2] = M[1,3] = -0.5
    M[2,1] = M[2,3] = -0.5
    res = M.solve([6, 3, 6, 0])
    assert res == [14, 8, 10, 0]
