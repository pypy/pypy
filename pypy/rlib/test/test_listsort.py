import py
from pypy.rlib.listsort import TimSort
import random, os

def makeset(lst):
    result = {}
    for a in lst:
        result.setdefault(id(a), []).append(True)
    return result

def sorttest(lst1):
    lst2 = lst1[:]
    TimSort(lst2).sort()
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

def test_file():
    for fn in py.magic.autopath().dirpath().listdir():
        if fn.ext == '.py': 
            lines1 = fn.readlines()
            sorttest(lines1)
