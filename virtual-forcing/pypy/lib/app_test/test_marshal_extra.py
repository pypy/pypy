import py
import sys
import marshal as cpy_marshal
from pypy.lib import _marshal as marshal

from pypy.tool.udir import udir 

hello = "he"
hello += "llo"
def func(x):
    return lambda y: x+y
scopefunc = func(42)

TESTCASES = [
    None,
    False,
    True,
    StopIteration,
    Ellipsis,
    42,
    sys.maxint,
    -1.25,
    2+5j,
    42L,
    -1234567890123456789012345678901234567890L,
    hello,   # not interned
    "hello",
    (),
    (1, 2),
    [],
    [3, 4],
    {},
    {5: 6, 7: 8},
    func.func_code,
    scopefunc.func_code,
    u'hello',
    ]

try:
    TESTCASES += [
        set(),
        set([1, 2]),
        frozenset(),
        frozenset([3, 4]),
        ]
except NameError:
    pass    # Python < 2.4

if getattr(cpy_marshal, 'version', 0) > 1:
    cpy_dump_version = (1,)
else:
    cpy_dump_version = ()


def test_cases():
    for case in TESTCASES:
        yield dumps_and_reload, case
        yield loads_from_cpython, case
        yield dumps_to_cpython, case
        if case is not StopIteration:
            yield dumps_subclass, case
        yield load_from_cpython, case
        yield dump_to_cpython, case

def dumps_and_reload(case):
    print 'dump_and_reload', `case`
    s = marshal.dumps(case)
    obj = marshal.loads(s)
    assert obj == case

def loads_from_cpython(case):
    print 'load_from_cpython', `case`
    try:
        s = cpy_marshal.dumps(case, *cpy_dump_version)
    except ValueError:
        py.test.skip("this version of CPython doesn't support this object") 
    obj = marshal.loads(s)
    assert obj == case

def dumps_to_cpython(case):
    print 'dump_to_cpython', `case`
    try:
        cpy_marshal.dumps(case, *cpy_dump_version)
    except ValueError:
        py.test.skip("this version of CPython doesn't support this object") 
    s = marshal.dumps(case)
    obj = cpy_marshal.loads(s)
    assert obj == case

def dumps_subclass(case):
    try:
        class Subclass(type(case)):
            pass
        case = Subclass(case)
    except TypeError:
        py.test.skip("this version of CPython doesn't support this object") 
    s = marshal.dumps(case)
    obj = marshal.loads(s)
    assert obj == case

def load_from_cpython(case):
    p = str(udir.join('test.dat'))

    f1 = open(p, "w")
    try:
        try:
            s = cpy_marshal.dump(case, f1, *cpy_dump_version)
        finally:
            f1.close()
    except ValueError:
        py.test.skip("this version of CPython doesn't support this object") 

    f2 = open(p, "r")
    try:
        obj = marshal.load(f2)
    finally:
        f2.close()
    assert obj == case

def dump_to_cpython(case):

    try:
        cpy_marshal.dumps(case, *cpy_dump_version)
    except ValueError:
        py.test.skip("this version of CPython doesn't support this object") 

    p = str(udir.join('test.dat'))
    f1 = open(p, "w")
    try:
        try:
            s = marshal.dump(case, f1)
        finally:
            f1.close()
    except ValueError:
        py.test.skip("this version of CPython doesn't support this object") 

    f2 = open(p, "r")
    try:
        obj = cpy_marshal.load(f2)
    finally:
        f2.close()
    assert obj == case


