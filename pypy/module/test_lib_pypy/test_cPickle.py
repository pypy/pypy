from __future__ import absolute_import
import py

from lib_pypy import cPickle

def test_stack_underflow():
    py.test.raises(cPickle.UnpicklingError, cPickle.loads, "a string")

def test_bad_key():
    e = py.test.raises(cPickle.UnpicklingError, cPickle.loads, "v")
    assert str(e.value) == "invalid load key, 'v'."

def test_find_global():
    import time, cStringIO
    entry = time.strptime('Fri Mar 27 22:20:42 2017')
    f = cStringIO.StringIO()
    cPickle.Pickler(f).dump(entry)

    f = cStringIO.StringIO(f.getvalue())
    e = cPickle.Unpickler(f).load()
    assert e == entry

    f = cStringIO.StringIO(f.getvalue())
    up = cPickle.Unpickler(f)
    up.find_global = None
    e = py.test.raises(cPickle.UnpicklingError, up.load)
    assert str(e.value) == "Global and instance pickles are not supported."

    f = cStringIO.StringIO(f.getvalue())
    up = cPickle.Unpickler(f)
    up.find_global = lambda module, name: lambda a, b: (name, a, b)
    e = up.load()
    assert e == ('struct_time', (2017, 3, 27, 22, 20, 42, 4, 86, -1), {})
