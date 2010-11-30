import py, os, sys
from pypy.conftest import gettestobjspace
from pypy.module.cppyy import interp_cppyy, executor


currpath = py.path.local(__file__).dirpath()
shared_lib = str(currpath.join("example01Dict.so"))

space = gettestobjspace(usemodules=['cppyy'])

def setup_module(mod):
    if sys.platform == 'win32':
        py.test.skip("win32 not supported so far")
    err = os.system("cd '%s' && make example01Dict.so" % currpath)
    if err:
        raise OSError("'make' failed (see stderr)")

class TestCPPYYImplementation:
    def test_class_query(self):
        lib = interp_cppyy.load_lib(space, shared_lib)
        w_cppyyclass = interp_cppyy.type_byname(space, "example01")
        w_cppyyclass2 = interp_cppyy.type_byname(space, "example01")
        assert space.is_w(w_cppyyclass, w_cppyyclass2)
        adddouble = w_cppyyclass.methods["staticAddToDouble"]
        func, = adddouble.functions
        assert isinstance(func.executor, executor.DoubleExecutor)
        assert func.arg_types == ["double"]


class AppTestCPPYY:
    def setup_class(cls):
        cls.space = space
        env = os.environ
        cls.w_example01, cls.w_payload = cls.space.unpackiterable(cls.space.appexec([], """():
            import cppyy
            cppyy.load_lib(%r)
            return cppyy._type_byname('example01'), cppyy._type_byname('payload')""" % (shared_lib, )))

    def test_example01static_int(self):
        """Test passing of an int, returning of an int, and overloading on a
            differening number of arguments."""
        import sys
        t = self.example01
        res = t.invoke("staticAddOneToInt", 1)
        assert res == 2
        res = t.invoke("staticAddOneToInt", 1L)
        assert res == 2
        res = t.invoke("staticAddOneToInt", 1, 2)
        assert res == 4
        res = t.invoke("staticAddOneToInt", -1)
        assert res == 0
        res = t.invoke("staticAddOneToInt", sys.maxint-1)
        assert res == sys.maxint
        res = t.invoke("staticAddOneToInt", sys.maxint)
        assert res == -sys.maxint-1

        raises(TypeError, 't.invoke("staticAddOneToInt", 1, [])')
        raises(TypeError, 't.invoke("staticAddOneToInt", 1.)')
        raises(OverflowError, 't.invoke("staticAddOneToInt", sys.maxint+1)')


    def test_example01static_double(self):
        """Test passing of a double and returning of a double on a static function."""
        t = self.example01
        res = t.invoke("staticAddToDouble", 0.09)
        assert res == 0.09 + 0.01

    def test_example01static_constcharp(self):
        """Test passing of a C string and returning of a C string on a static
            function."""
        t = self.example01
        res = t.invoke("staticAtoi", "1")
        assert res == 1

        res = t.invoke("staticStrcpy", "aap")
        assert res == "aap"

        res = t.invoke("staticStrcpy", u"aap")
        assert res == "aap"

        raises(TypeError, 't.invoke("staticStrcpy", 1.)')

    def test_example01method_int(self):
        """Test passing of a int, returning of a int, and memory cleanup, on
            a method."""
        t = self.example01
        assert t.invoke("getCount") == 0
        instance = t.construct(7)
        assert t.invoke("getCount") == 1
        res = instance.invoke("addDataToInt", 4)
        assert res == 11
        res = instance.invoke("addDataToInt", -4)
        assert res == 3
        instance.destruct()
        assert t.invoke("getCount") == 0
        raises(ReferenceError, 'instance.invoke("addDataToInt", 4)')

        instance = t.construct(7)
        instance2 = t.construct(8)
        assert t.invoke("getCount") == 2
        instance.destruct()
        assert t.invoke("getCount") == 1
        instance2.destruct()
        assert t.invoke("getCount") == 0

    def test_example01method_double(self):
        """Test passing of a double and returning of double on a method"""
        t = self.example01
        instance = t.construct(13)
        res = instance.invoke("addDataToDouble", 16)
        assert round(res-29, 8) == 0.
        instance.destruct()
        instance = t.construct(-13)
        res = instance.invoke("addDataToDouble", 16)
        assert round(res-3, 8) == 0.
        instance.destruct()
        assert t.invoke("getCount") == 0

    def test_example01method_constcharp(self):
        """Test passing of a C string and returning of a C string on a
            method."""

        t = self.example01
        instance = t.construct(42)

        res = instance.invoke("addDataToAtoi", "13")
        assert res == 55

        res = instance.invoke("addToStringValue", "12")
        assert res == "54"
        res = instance.invoke("addToStringValue", "-12")
        assert res == "30"
        instance.destruct()
        assert t.invoke("getCount") == 0

    def testPassingOfAnObjectByPointer(self):
        """Test passing of an instance as an argument."""

        t = self.example01

        pl = self.payload.construct(3.14)
        assert round(pl.invoke("getData")-3.14, 8) == 0
        
        t.invoke("staticSetPayload", pl, 41.)    # now pl is a CPPInstance
        assert pl.invoke("getData") == 41.

        e = t.construct(50)
        e.invoke("setPayload", pl);
        assert round(pl.invoke("getData")-50., 8) == 0

        e.destruct()
        pl.destruct() 
        assert t.invoke("getCount") == 0

    def testReturningOfAnObjectByPointer(self):
        """Test returning of an instance as an argument."""

        t = self.example01
        
        pl = self.payload.construct(3.14)
        assert round(pl.invoke("getData")-3.14, 8) == 0

        pl2 = t.invoke("staticCyclePayload", pl, 38.)
        assert pl2.invoke("getData") == 38.

        e = t.construct(50)

        pl2 = e.invoke("cyclePayload", pl);
        assert round(pl2.invoke("getData")-50., 8) == 0

        e.destruct()
        pl.destruct() 
        assert t.invoke("getCount") == 0

