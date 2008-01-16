from pypy.conftest import gettestobjspace
import os, sys, py

def setup_module(mod):
    if sys.platform != 'linux2':
        py.test.skip("Linux only tests by now")

class AppTestNested:
    def setup_class(cls):
        space = gettestobjspace(usemodules=('_rawffi','struct'))
        cls.space = space

    def test_inspect_structure(self):
        import _rawffi, struct
        align = max(struct.calcsize("i"), struct.calcsize("P"))
        assert align & (align-1) == 0, "not a power of 2??"
        def round_up(x):
            return (x+align-1) & -align

        S = _rawffi.Structure([('a', 'i'), ('b', 'P'), ('c', 'c')])
        assert S.size == round_up(struct.calcsize("iPc"))
        assert S.alignment == align
        assert S.fieldoffset('a') == 0
        assert S.fieldoffset('b') == align
        assert S.fieldoffset('c') == round_up(struct.calcsize("iP"))
        assert S.gettypecode() == (S.size, S.alignment)

    def test_nested_structures(self):
        import _rawffi
        S1 = _rawffi.Structure([('a', 'i'), ('b', 'P'), ('c', 'c')])
        S = _rawffi.Structure([('x', 'c'), ('s1', S1.gettypecode())])
        assert S.size == S1.alignment + S1.size
        assert S.alignment == S1.alignment
        assert S.fieldoffset('x') == 0
        assert S.fieldoffset('s1') == S1.alignment
        s = S()
        s.x = 'G'
        raises(TypeError, 's.s1')
        assert s.fieldaddress('s1') == s.buffer + S.fieldoffset('s1')
        s1 = S1.fromaddress(s.fieldaddress('s1'))
        s1.c = 'H'
        rawbuf = _rawffi.Array('c').fromaddress(s.buffer, S.size)
        assert rawbuf[0] == 'G'
        assert rawbuf[S1.alignment + S1.fieldoffset('c')] == 'H'
        s.free()

    def test_array_of_structures(self):
        import _rawffi
        S = _rawffi.Structure([('a', 'i'), ('b', 'P'), ('c', 'c')])
        A = _rawffi.Array(S.gettypecode())
        a = A(3)
        raises(TypeError, "a[0]")
        s0 = S.fromaddress(a.buffer)
        s0.c = 'B'
        assert a.itemaddress(1) == a.buffer + S.size
        s1 = S.fromaddress(a.itemaddress(1))
        s1.c = 'A'
        s2 = S.fromaddress(a.itemaddress(2))
        s2.c = 'Z'
        rawbuf = _rawffi.Array('c').fromaddress(a.buffer, S.size * len(a))
        ofs = S.fieldoffset('c')
        assert rawbuf[0*S.size+ofs] == 'B'
        assert rawbuf[1*S.size+ofs] == 'A'
        assert rawbuf[2*S.size+ofs] == 'Z'
        a.free()

    def test_array_of_array(self):
        import _rawffi, struct
        B = _rawffi.Array('i')
        sizeofint = struct.calcsize("i")
        assert B.gettypecode(100) == (sizeofint * 100, sizeofint)
        A = _rawffi.Array(B.gettypecode(4))
        a = A(2)
        b0 = B.fromaddress(a.itemaddress(0), 4)
        b0[0] = 3
        b0[3] = 7
        b1 = B.fromaddress(a.itemaddress(1), 4)
        b1[0] = 13
        b1[3] = 17
        rawbuf = _rawffi.Array('i').fromaddress(a.buffer, 2 * 4)
        assert rawbuf[0] == 3
        assert rawbuf[3] == 7
        assert rawbuf[4] == 13
        assert rawbuf[7] == 17
        a.free()
