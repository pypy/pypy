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

        import sys, math
        t = self.example01

        res = t.invoke(t.get_overload("staticAddOneToInt"), 1)
        assert res == 2
        res = t.invoke(t.get_overload("staticAddOneToInt"), 1L)
        assert res == 2
        res = t.invoke(t.get_overload("staticAddOneToInt"), 1, 2)
        assert res == 4
        res = t.invoke(t.get_overload("staticAddOneToInt"), -1)
        assert res == 0
        maxint32 = int(2 ** 31 - 1)
        res = t.invoke(t.get_overload("staticAddOneToInt"), maxint32-1)
        assert res == maxint32
        res = t.invoke(t.get_overload("staticAddOneToInt"), maxint32)
        assert res == -maxint32-1

        raises(TypeError, 't.invoke(t.get_overload("staticAddOneToInt"), 1, [])')
        raises(TypeError, 't.invoke(t.get_overload("staticAddOneToInt"), 1.)')
        raises(OverflowError, 't.invoke(t.get_overload("staticAddOneToInt"), maxint32+1)')


    def test_example01static_double(self):
        """Test passing of a double and returning of a double on a static function."""

        t = self.example01

        res = t.invoke(t.get_overload("staticAddToDouble"), 0.09)
        assert res == 0.09 + 0.01

    def test_example01static_constcharp(self):
        """Test passing of a C string and returning of a C string on a static
            function."""

        t = self.example01

        res = t.invoke(t.get_overload("staticAtoi"), "1")
        assert res == 1
        res = t.invoke(t.get_overload("staticStrcpy"), "aap")   # TODO: this leaks
        assert res == "aap"
        res = t.invoke(t.get_overload("staticStrcpy"), u"aap")  # TODO: this leaks
        assert res == "aap"

        raises(TypeError, 't.invoke(t.get_overload("staticStrcpy"), 1.)') # TODO: this leaks

    def test_example01method_int(self):
        """Test passing of a int, returning of a int, and memory cleanup, on
            a method."""

        t = self.example01

        assert t.invoke(t.get_overload("getCount")) == 0

        e1 = t.construct(7)
        assert t.invoke(t.get_overload("getCount")) == 1
        res = e1.invoke(t.get_overload("addDataToInt"), 4)
        assert res == 11
        res = e1.invoke(t.get_overload("addDataToInt"), -4)
        assert res == 3
        e1.destruct()
        assert t.invoke(t.get_overload("getCount")) == 0
        raises(ReferenceError, 'e1.invoke(t.get_overload("addDataToInt"), 4)')

        e1 = t.construct(7)
        e2 = t.construct(8)
        assert t.invoke(t.get_overload("getCount")) == 2
        e1.destruct()
        assert t.invoke(t.get_overload("getCount")) == 1
        e2.destruct()
        assert t.invoke(t.get_overload("getCount")) == 0

        e2.destruct()
        assert t.invoke(t.get_overload("getCount")) == 0

    def test_example01memory(self):
        """Test memory destruction and integrity."""

        import gc

        t = self.example01

        assert t.invoke(t.get_overload("getCount")) == 0

        e1 = t.construct(7)
        assert t.invoke(t.get_overload("getCount")) == 1
        res = e1.invoke(t.get_overload("addDataToInt"), 4)
        assert res == 11
        res = e1.invoke(t.get_overload("addDataToInt"), -4)
        assert res == 3
        e1 = None
        gc.collect()
        assert t.invoke(t.get_overload("getCount")) == 0

        e1 = t.construct(7)
        e2 = t.construct(8)
        assert t.invoke(t.get_overload("getCount")) == 2
        e1 = None
        gc.collect()
        assert t.invoke(t.get_overload("getCount")) == 1
	e2.destruct()
        assert t.invoke(t.get_overload("getCount")) == 0
        e2 = None
        gc.collect()
        assert t.invoke(t.get_overload("getCount")) == 0

    def test_example01method_double(self):
        """Test passing of a double and returning of double on a method"""

        t = self.example01

        e = t.construct(13)
        res = e.invoke(t.get_overload("addDataToDouble"), 16)
        assert round(res-29, 8) == 0.
        e.destruct()

        e = t.construct(-13)
        res = e.invoke(t.get_overload("addDataToDouble"), 16)
        assert round(res-3, 8) == 0.
        e.destruct()
        assert t.invoke(t.get_overload("getCount")) == 0

    def test_example01method_constcharp(self):
        """Test passing of a C string and returning of a C string on a
            method."""

        t = self.example01

        e = t.construct(42)
        res = e.invoke(t.get_overload("addDataToAtoi"), "13")
        assert res == 55
        res = e.invoke(t.get_overload("addToStringValue"), "12")     # TODO: this leaks
        assert res == "54"
        res = e.invoke(t.get_overload("addToStringValue"), "-12")    # TODO: this leaks
        assert res == "30"
        e.destruct()
        assert t.invoke(t.get_overload("getCount")) == 0

    def testPassingOfAnObjectByPointer(self):
        """Test passing of an instance as an argument."""

        t1 = self.example01
        t2 = self.payload

        pl = t2.construct(3.14)
        assert round(pl.invoke(t2.get_overload("getData"))-3.14, 8) == 0
        t1.invoke(t1.get_overload("staticSetPayload"), pl, 41.)  # now pl is a CPPInstance
        assert pl.invoke(t2.get_overload("getData")) == 41.

        e = t1.construct(50)
        e.invoke(t1.get_overload("setPayload"), pl);
        assert round(pl.invoke(t2.get_overload("getData"))-50., 8) == 0

        e.destruct()
        pl.destruct() 
        assert t1.invoke(t1.get_overload("getCount")) == 0

    def testReturningOfAnObjectByPointer(self):
        """Test returning of an instance as an argument."""

        t1 = self.example01
        t2 = self.payload

        pl1 = t2.construct(3.14)
        assert round(pl1.invoke(t2.get_overload("getData"))-3.14, 8) == 0
        pl2 = t1.invoke(t1.get_overload("staticCyclePayload"), pl1, 38.)
        assert pl2.invoke(t2.get_overload("getData")) == 38.

        e = t1.construct(50)
        pl2 = e.invoke(t1.get_overload("cyclePayload"), pl1);
        assert round(pl2.invoke(t2.get_overload("getData"))-50., 8) == 0

        e.destruct()
        pl1.destruct() 
        assert t1.invoke(t1.get_overload("getCount")) == 0
