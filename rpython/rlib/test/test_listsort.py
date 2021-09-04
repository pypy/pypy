import py
from rpython.rlib.listsort import TimSort
import random, os

from hypothesis import given, strategies as st

def makeset(lst):
    result = {}
    for a in lst:
        result.setdefault(id(a), []).append(True)
    return result

class TestTimSort(TimSort):
    def merge_compute_minrun(self, n):
        return 1 # that means we use the "timsorty" bits of the algorithm more
        # than just mostly binary insertion sort

def sorttest(lst1):
    _sorttest(TimSort, lst1)
    _sorttest(TestTimSort, lst1)

def _sorttest(cls, lst1):
    lst2 = lst1[:]
    cls(lst2).sort()
    assert len(lst1) == len(lst2)
    assert makeset(lst1) == makeset(lst2)
    position = {}
    i = 0
    for a in lst1:
        position.setdefault(id(a), []).append(i)
        i += 1
    for i in range(len(lst2)-1):
        a, b = lst2[i], lst2[i+1]
        assert a <= b, "resulting list is not sorted"
        if a == b:
            assert position[id(a)][0] < position[id(b)][-1], "not stable"


class C(int):
    pass

def test_v():
    for v in range(137):
        up = 1 + int(v * random.random() * 2.7)
        lst1 = [C(random.randrange(0, up)) for i in range(v)]
        sorttest(lst1)

@given(st.lists(st.integers(), min_size=2))
def test_hypothesis(l):
    sorttest(l)

def test_file():
    for fn in py.path.local(__file__).dirpath().listdir():
        if fn.ext == '.py': 
            lines1 = fn.readlines()
            sorttest(lines1)
