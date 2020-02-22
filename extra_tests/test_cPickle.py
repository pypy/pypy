import pytest
import cPickle

def test_stack_underflow():
    with pytest.raises(cPickle.UnpicklingError):
        cPickle.loads("a string")

def test_bad_key():
    with pytest.raises(cPickle.UnpicklingError) as excinfo:
        cPickle.loads("v")
    assert str(excinfo.value) == "invalid load key, 'v'."

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
    with pytest.raises(cPickle.UnpicklingError) as e:
        up.load()
    assert str(e.value) == "Global and instance pickles are not supported."

    f = cStringIO.StringIO(f.getvalue())
    up = cPickle.Unpickler(f)
    up.find_global = lambda module, name: lambda a, b: (name, a, b)
    e = up.load()
    assert e == ('struct_time', (2017, 3, 27, 22, 20, 42, 4, 86, -1), {})
