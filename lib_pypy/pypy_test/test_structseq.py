from __future__ import absolute_import
import py
from lib_pypy._structseq import structseqfield, structseqtype


class mydata:
    __metaclass__ = structseqtype

    st_mode  = structseqfield(0, "protection bits")
    st_ino   = structseqfield(1)
    st_dev   = structseqfield(2)
    st_nlink = structseqfield(3)
    st_uid   = structseqfield(4)
    st_gid   = structseqfield(5)
    st_size  = structseqfield(6)
    _st_atime_as_int = structseqfield(7)
    _st_mtime_as_int = structseqfield(8)
    _st_ctime_as_int = structseqfield(9)
    # skip to higher numbers for fields not part of the sequence.
    # the numbers are only used to ordering
    st_rdev  = structseqfield(50, "device type (if inode device)")
    st_atime = structseqfield(57, default=lambda self: self._st_atime_as_int)
    st_mtime = structseqfield(58, default=lambda self: self._st_mtime_as_int)
    st_ctime = structseqfield(59, default=lambda self: self._st_ctime_as_int)


def test_class():
    assert mydata.st_mode.__doc__ == "protection bits"
    assert mydata.n_fields == 14
    assert mydata.n_sequence_fields == 10
    assert mydata.n_unnamed_fields == 0

def test_mydata():
    x = mydata(range(100, 111))
    assert x.n_sequence_fields == type(x).n_sequence_fields == 10
    assert x.n_fields == type(x).n_fields == 14
    assert x.st_mode  == 100
    assert x.st_size  == 106
    assert x.st_ctime == 109    # copied by the default=lambda...
    assert x.st_rdev  == 110
    assert len(x)     == 10
    assert list(x)    == range(100, 110)
    assert x + (5,)   == tuple(range(100, 110)) + (5,)
    assert x[4:12:2]  == (104, 106, 108)
    assert 104 in x
    assert 110 not in x

def test_default_None():
    x = mydata(range(100, 110))
    assert x.st_rdev is None

def test_constructor():
    x = mydata(range(100, 111), {'st_mtime': 12.25})
    assert x[8] == 108
    assert x.st_mtime == 12.25

def test_compare_like_tuple():
    x = mydata(range(100, 111))
    y = mydata(range(100, 110) + [555])
    assert x == tuple(range(100, 110))
    assert x == y    # blame CPython
    assert hash(x) == hash(y) == hash(tuple(range(100, 110)))

def test_pickle():
    import pickle
    x = mydata(range(100, 111))
    s = pickle.dumps(x)
    y = pickle.loads(s)
    assert x == y
    assert x.st_rdev == y.st_rdev == 110

def test_readonly():
    x = mydata(range(100, 113))
    py.test.raises((TypeError, AttributeError), "x.st_mode = 1")
    py.test.raises((TypeError, AttributeError), "x.st_mtime = 1")
    py.test.raises((TypeError, AttributeError), "x.st_rdev = 1")

def test_no_extra_assignments():
    x = mydata(range(100, 113))
    py.test.raises((TypeError, AttributeError), "x.some_random_attribute = 1")
