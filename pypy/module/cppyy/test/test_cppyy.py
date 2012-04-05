import py, os, sys
from pypy.conftest import gettestobjspace
from pypy.module.cppyy import interp_cppyy, executor


currpath = py.path.local(__file__).dirpath()
test_dct = str(currpath.join("example01Dict.so"))

space = gettestobjspace(usemodules=['cppyy'])

def setup_module(mod):
    if sys.platform == 'win32':
        py.test.skip("win32 not supported so far")
    err = os.system("cd '%s' && make example01Dict.so" % currpath)
    if err:
        raise OSError("'make' failed (see stderr)")

class TestCPPYYImplementation:
    def test01_class_query(self):
        dct = interp_cppyy.load_dictionary(space, test_dct)
        w_cppyyclass = interp_cppyy.scope_byname(space, "example01")
        w_cppyyclass2 = interp_cppyy.scope_byname(space, "example01")
        assert space.is_w(w_cppyyclass, w_cppyyclass2)
        adddouble = w_cppyyclass.methods["staticAddToDouble"]
        func, = adddouble.functions
        assert func.executor is None
        func._setup(None)     # creates executor
        assert isinstance(func.executor, executor.DoubleExecutor)
        assert func.arg_defs == [("double", "")]


class AppTestCPPYY:
    def setup_class(cls):
        cls.space = space
        env = os.environ
        cls.w_example01, cls.w_payload = cls.space.unpackiterable(cls.space.appexec([], """():
            import cppyy
            cppyy.load_reflection_info(%r)
            return cppyy._scope_byname('example01'), cppyy._scope_byname('payload')""" % (test_dct, )))

    def test01_static_int(self):
        """Test passing of an int, returning of an int, and overloading on a
            differening number of arguments."""

        import sys, math
        t = self.example01

        res = t.get_overload("staticAddOneToInt").call(None, 1)
        assert res == 2
        res = t.get_overload("staticAddOneToInt").call(None, 1L)
        assert res == 2
        res = t.get_overload("staticAddOneToInt").call(None, 1, 2)
        assert res == 4
        res = t.get_overload("staticAddOneToInt").call(None, -1)
        assert res == 0
        maxint32 = int(2 ** 31 - 1)
        res = t.get_overload("staticAddOneToInt").call(None, maxint32-1)
        assert res == maxint32
        res = t.get_overload("staticAddOneToInt").call(None, maxint32)
        assert res == -maxint32-1

        raises(TypeError, 't.get_overload("staticAddOneToInt").call(None, 1, [])')
        raises(TypeError, 't.get_overload("staticAddOneToInt").call(None, 1.)')
        raises(TypeError, 't.get_overload("staticAddOneToInt").call(None, maxint32+1)')

    def test02_static_double(self):
        """Test passing of a double and returning of a double on a static function."""

        t = self.example01

        res = t.get_overload("staticAddToDouble").call(None, 0.09)
        assert res == 0.09 + 0.01

    def test03_static_constcharp(self):
        """Test passing of a C string and returning of a C string on a static
            function."""

        t = self.example01

        res = t.get_overload("staticAtoi").call(None, "1")
        assert res == 1
        res = t.get_overload("staticStrcpy").call(None, "aap")       # TODO: this leaks
        assert res == "aap"
        res = t.get_overload("staticStrcpy").call(None, u"aap")      # TODO: this leaks
        assert res == "aap"

        raises(TypeError, 't.get_overload("staticStrcpy").call(None, 1.)')     # TODO: this leaks

    def test04_method_int(self):
        """Test passing of a int, returning of a int, and memory cleanup, on
            a method."""
        import cppyy

        t = self.example01

        assert t.get_overload("getCount").call(None) == 0

        e1 = t.get_overload(t.type_name).call(None, 7)
        assert t.get_overload("getCount").call(None) == 1
        res = t.get_overload("addDataToInt").call(e1, 4)
        assert res == 11
        res = t.get_overload("addDataToInt").call(e1, -4)
        assert res == 3
        e1.destruct()
        assert t.get_overload("getCount").call(None) == 0
        raises(ReferenceError, 't.get_overload("addDataToInt").call(e1, 4)')

        e1 = t.get_overload(t.type_name).call(None, 7)
        e2 = t.get_overload(t.type_name).call(None, 8)
        assert t.get_overload("getCount").call(None) == 2
        e1.destruct()
        assert t.get_overload("getCount").call(None) == 1
        e2.destruct()
        assert t.get_overload("getCount").call(None) == 0

        e2.destruct()
        assert t.get_overload("getCount").call(None) == 0

        raises(TypeError, t.get_overload("addDataToInt").call, 41, 4)

    def test05_memory(self):
        """Test memory destruction and integrity."""

        import gc
        import cppyy

        t = self.example01

        assert t.get_overload("getCount").call(None) == 0

        e1 = t.get_overload(t.type_name).call(None, 7)
        assert t.get_overload("getCount").call(None) == 1
        res = t.get_overload("addDataToInt").call(e1, 4)
        assert res == 11
        res = t.get_overload("addDataToInt").call(e1, -4)
        assert res == 3
        e1 = None
        gc.collect()
        assert t.get_overload("getCount").call(None) == 0

        e1 = t.get_overload(t.type_name).call(None, 7)
        e2 = t.get_overload(t.type_name).call(None, 8)
        assert t.get_overload("getCount").call(None) == 2
        e1 = None
        gc.collect()
        assert t.get_overload("getCount").call(None) == 1
	e2.destruct()
        assert t.get_overload("getCount").call(None) == 0
        e2 = None
        gc.collect()
        assert t.get_overload("getCount").call(None) == 0

    def test06_method_double(self):
        """Test passing of a double and returning of double on a method"""
        import cppyy

        t = self.example01

        e = t.get_overload(t.type_name).call(None, 13)
        res = t.get_overload("addDataToDouble").call(e, 16)
        assert round(res-29, 8) == 0.
        e.destruct()

        e = t.get_overload(t.type_name).call(None, -13)
        res = t.get_overload("addDataToDouble").call(e, 16)
        assert round(res-3, 8) == 0.
        e.destruct()
        assert t.get_overload("getCount").call(None) == 0

    def test07_method_constcharp(self):
        """Test passing of a C string and returning of a C string on a
            method."""
        import cppyy

        t = self.example01

        e = t.get_overload(t.type_name).call(None, 42)
        res = t.get_overload("addDataToAtoi").call(e, "13")
        assert res == 55
        res = t.get_overload("addToStringValue").call(e, "12")       # TODO: this leaks
        assert res == "54"
        res = t.get_overload("addToStringValue").call(e, "-12")      # TODO: this leaks
        assert res == "30"
        e.destruct()
        assert t.get_overload("getCount").call(None) == 0

    def test08_pass_object_by_pointer(self):
        """Test passing of an instance as an argument."""
        import cppyy

        t1 = self.example01
        t2 = self.payload

        pl = t2.get_overload(t2.type_name).call(None, 3.14)
        assert round(t2.get_overload("getData").call(pl)-3.14, 8) == 0
        t1.get_overload("staticSetPayload").call(None, pl, 41.)      # now pl is a CPPInstance
        assert t2.get_overload("getData").call(pl) == 41.

        e = t1.get_overload(t1.type_name).call(None, 50)
        t1.get_overload("setPayload").call(e, pl);
        assert round(t2.get_overload("getData").call(pl)-50., 8) == 0

        e.destruct()
        pl.destruct() 
        assert t1.get_overload("getCount").call(None) == 0

    def test09_return_object_by_pointer(self):
        """Test returning of an instance as an argument."""
        import cppyy

        t1 = self.example01
        t2 = self.payload

        pl1 = t2.get_overload(t2.type_name).call(None, 3.14)
        assert round(t2.get_overload("getData").call(pl1)-3.14, 8) == 0
        pl2 = t1.get_overload("staticCyclePayload").call(None, pl1, 38.)
        assert t2.get_overload("getData").call(pl2) == 38.

        e = t1.get_overload(t1.type_name).call(None, 50)
        pl2 = t1.get_overload("cyclePayload").call(e, pl1);
        assert round(t2.get_overload("getData").call(pl2)-50., 8) == 0

        e.destruct()
        pl1.destruct() 
        assert t1.get_overload("getCount").call(None) == 0
