from pypy.module.marshal import interp_marshal
from pypy.interpreter.error import OperationError
from pypy.objspace.std.intobject import W_IntObject
import sys


def test_long_more(space):
    import marshal, struct

    class FakeM:
        # NOTE: marshal is platform independent, running this test must assume
        # that self.seen gets values from the endianess of the marshal module.
        # (which is little endian!)
        version = 2
        def __init__(self):
            self.seen = []
        def start(self, code):
            self.seen.append(code)
        def put_int(self, value):
            self.seen.append(struct.pack("<i", value))
        def put_short(self, value):
            self.seen.append(struct.pack("<h", value))

    def _marshal_check(x):
        expected = marshal.dumps(long(x))
        w_obj = space.wraplong(x)
        m = FakeM()
        interp_marshal.marshal(space, w_obj, m)
        assert ''.join(m.seen) == expected
        #
        u = interp_marshal.StringUnmarshaller(space, space.newbytes(expected))
        w_long = u.load_w_obj()
        assert space.eq_w(w_long, w_obj)

    for sign in [1L, -1L]:
        for i in range(100):
            _marshal_check(sign * ((1L << i) - 1L))
            _marshal_check(sign * (1L << i))

def test_int_roundtrip(space):
    a = 0xffffffff
    w_a = space.newint(a)
    m = interp_marshal.StringMarshaller(space, 4)
    interp_marshal.marshal(space, w_a, m)
    s = m.get_value()
    u = interp_marshal.StringUnmarshaller(space, space.newbytes(s))
    w_res = u.load_w_obj()

    assert type(w_res) is W_IntObject
    assert w_res.intval == w_a.intval == a

def test_hidden_applevel(space):
    w_s = interp_marshal.dumps(space, space.appdef('''(): pass''').code)
    w_c = interp_marshal._loads(space, w_s)
    assert w_c.hidden_applevel == False
    w_c = interp_marshal._loads(space, w_s, hidden_applevel=True)
    assert w_c.hidden_applevel == True
