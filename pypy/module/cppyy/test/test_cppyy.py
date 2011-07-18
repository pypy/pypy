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

    def test01_static_int(self):
        """Test passing of an int, returning of an int, and overloading on a
            differening number of arguments."""

        import sys, math
        t = self.example01

        res = t.get_overload("staticAddOneToInt").call(None, None, 1)
        assert res == 2
        res = t.get_overload("staticAddOneToInt").call(None, None, 1L)
        assert res == 2
        res = t.get_overload("staticAddOneToInt").call(None, None, 1, 2)
        assert res == 4
        res = t.get_overload("staticAddOneToInt").call(None, None, -1)
        assert res == 0
        maxint32 = int(2 ** 31 - 1)
        res = t.get_overload("staticAddOneToInt").call(None, None, maxint32-1)
        assert res == maxint32
        res = t.get_overload("staticAddOneToInt").call(None, None, maxint32)
        assert res == -maxint32-1

        raises(TypeError, 't.get_overload("staticAddOneToInt").call(None, None, 1, [])')
        raises(TypeError, 't.get_overload("staticAddOneToInt").call(None, None, 1.)')
        raises(OverflowError, 't.get_overload("staticAddOneToInt").call(None, None, maxint32+1)')

    def test02_static_double(self):
        """Test passing of a double and returning of a double on a static function."""

        t = self.example01

        res = t.get_overload("staticAddToDouble").call(None, None, 0.09)
        assert res == 0.09 + 0.01

    def test03_static_constcharp(self):
        """Test passing of a C string and returning of a C string on a static
            function."""

        t = self.example01

        res = t.get_overload("staticAtoi").call(None, None, "1")
        assert res == 1
        res = t.get_overload("staticStrcpy").call(None, None, "aap")   # TODO: this leaks
        assert res == "aap"
        res = t.get_overload("staticStrcpy").call(None, None, u"aap")  # TODO: this leaks
        assert res == "aap"

        raises(TypeError, 't.get_overload("staticStrcpy").call(None, None, 1.)') # TODO: this leaks

    def test04_method_int(self):
        """Test passing of a int, returning of a int, and memory cleanup, on
            a method."""
        import cppyy

        t = self.example01

        assert t.get_overload("getCount").call(None, None) == 0

        e1 = t.get_overload(t.type_name).call(None, cppyy.CPPInstance, 7)
        assert t.get_overload("getCount").call(None, None) == 1
        res = t.get_overload("addDataToInt").call(e1, None, 4)
        assert res == 11
        res = t.get_overload("addDataToInt").call(e1, None, -4)
        assert res == 3
        e1.destruct()
        assert t.get_overload("getCount").call(None, None) == 0
        raises(ReferenceError, 't.get_overload("addDataToInt").call(e1, None, 4)')

        e1 = t.get_overload(t.type_name).call(None, cppyy.CPPInstance, 7)
        e2 = t.get_overload(t.type_name).call(None, cppyy.CPPInstance, 8)
        assert t.get_overload("getCount").call(None, None) == 2
        e1.destruct()
        assert t.get_overload("getCount").call(None, None) == 1
        e2.destruct()
        assert t.get_overload("getCount").call(None, None) == 0

        e2.destruct()
        assert t.get_overload("getCount").call(None, None) == 0


        raises(TypeError, t.get_overload("addDataToInt").call, 41, None, 4)

    def test05_memory(self):
        """Test memory destruction and integrity."""

        import gc
        import cppyy

        t = self.example01

        assert t.get_overload("getCount").call(None, None) == 0

        e1 = t.get_overload(t.type_name).call(None, cppyy.CPPInstance, 7)
        assert t.get_overload("getCount").call(None, None) == 1
        res = t.get_overload("addDataToInt").call(e1, None, 4)
        assert res == 11
        res = t.get_overload("addDataToInt").call(e1, None, -4)
        assert res == 3
        e1 = None
        gc.collect()
        assert t.get_overload("getCount").call(None, None) == 0

        e1 = t.get_overload(t.type_name).call(None, cppyy.CPPInstance, 7)
        e2 = t.get_overload(t.type_name).call(None, cppyy.CPPInstance, 8)
        assert t.get_overload("getCount").call(None, None) == 2
        e1 = None
        gc.collect()
        assert t.get_overload("getCount").call(None, None) == 1
	e2.destruct()
        assert t.get_overload("getCount").call(None, None) == 0
        e2 = None
        gc.collect()
        assert t.get_overload("getCount").call(None, None) == 0

    def test06_method_double(self):
        """Test passing of a double and returning of double on a method"""
        import cppyy

        t = self.example01

        e = t.get_overload(t.type_name).call(None, cppyy.CPPInstance, 13)
        res = t.get_overload("addDataToDouble").call(e, None, 16)
        assert round(res-29, 8) == 0.
        e.destruct()

        e = t.get_overload(t.type_name).call(None, cppyy.CPPInstance, -13)
        res = t.get_overload("addDataToDouble").call(e, None, 16)
        assert round(res-3, 8) == 0.
        e.destruct()
        assert t.get_overload("getCount").call(None, None) == 0

    def test07_method_constcharp(self):
        """Test passing of a C string and returning of a C string on a
            method."""
        import cppyy

        t = self.example01

        e = t.get_overload(t.type_name).call(None, cppyy.CPPInstance, 42)
        res = t.get_overload("addDataToAtoi").call(e, None, "13")
        assert res == 55
        res = t.get_overload("addToStringValue").call(e, None, "12")     # TODO: this leaks
        assert res == "54"
        res = t.get_overload("addToStringValue").call(e, None, "-12")    # TODO: this leaks
        assert res == "30"
        e.destruct()
        assert t.get_overload("getCount").call(None, None) == 0

    def test08_pass_object_by_pointer(self):
        """Test passing of an instance as an argument."""
        import cppyy

        t1 = self.example01
        t2 = self.payload

        pl = t2.get_overload(t2.type_name).call(None, cppyy.CPPInstance, 3.14)
        assert round(t2.get_overload("getData").call(pl, None)-3.14, 8) == 0
        t1.get_overload("staticSetPayload").call(None, None, pl, 41.)  # now pl is a CPPInstance
        assert t2.get_overload("getData").call(pl, None) == 41.

        e = t1.get_overload(t1.type_name).call(None, cppyy.CPPInstance, 50)
        t1.get_overload("setPayload").call(e, None, pl);
        assert round(t2.get_overload("getData").call(pl, None)-50., 8) == 0

        e.destruct()
        pl.destruct() 
        assert t1.get_overload("getCount").call(None, None) == 0

    def test09_return_object_by_pointer(self):
        """Test returning of an instance as an argument."""
        import cppyy

        t1 = self.example01
        t2 = self.payload

        pl1 = t2.get_overload(t2.type_name).call(None, cppyy.CPPInstance, 3.14)
        assert round(t2.get_overload("getData").call(pl1, None)-3.14, 8) == 0
        pl2 = t1.get_overload("staticCyclePayload").call(None, cppyy.CPPInstance, pl1, 38.)
        assert t2.get_overload("getData").call(pl2, None) == 38.

        e = t1.get_overload(t1.type_name).call(None, cppyy.CPPInstance, 50)
        pl2 = t1.get_overload("cyclePayload").call(e, cppyy.CPPInstance, pl1);
        assert round(t2.get_overload("getData").call(pl2, None)-50., 8) == 0

        e.destruct()
        pl1.destruct() 
        assert t1.get_overload("getCount").call(None, None) == 0
