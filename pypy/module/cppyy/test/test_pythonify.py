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

class AppTestPYTHONIFY:
    def setup_class(cls):
        cls.space = space
        env = os.environ
        cls.w_test_dct  = space.wrap(test_dct)
        cls.w_example01 = cls.space.appexec([], """():
            import cppyy
            return cppyy.load_reflection_info(%r)""" % (test_dct, ))

    def test01_load_dicionary_cache(self):
        """Test whether loading a dictionary twice results in the same object."""
        import cppyy
        lib2 = cppyy.load_reflection_info(self.test_dct)
        assert self.example01 is lib2

    def test02_finding_classes(self):
        """Test the lookup of a class, and its caching."""
        import cppyy
        example01_class = cppyy.gbl.example01
        cl2 = cppyy.gbl.example01
        assert example01_class is cl2

        raises(AttributeError, "cppyy.gbl.nonexistingclass")

    def test03_calling_static_functions(self):
        """Test calling of static methods."""
        import cppyy, sys, math
        example01_class = cppyy.gbl.example01
        res = example01_class.staticAddOneToInt(1)
        assert res == 2

        res = example01_class.staticAddOneToInt(1L)
        assert res == 2
        res = example01_class.staticAddOneToInt(1, 2)
        assert res == 4
        res = example01_class.staticAddOneToInt(-1)
        assert res == 0
        maxint32 = int(2 ** 31 - 1)
        res = example01_class.staticAddOneToInt(maxint32-1)
        assert res == maxint32
        res = example01_class.staticAddOneToInt(maxint32)
        assert res == -maxint32-1

        raises(TypeError, 'example01_class.staticAddOneToInt(1, [])')
        raises(TypeError, 'example01_class.staticAddOneToInt(1.)')
        raises(OverflowError, 'example01_class.staticAddOneToInt(maxint32+1)')
        res = example01_class.staticAddToDouble(0.09)
        assert res == 0.09 + 0.01

        res = example01_class.staticAtoi("1")
        assert res == 1

        res = example01_class.staticStrcpy("aap")     # TODO: this leaks
        assert res == "aap"

        res = example01_class.staticStrcpy(u"aap")    # TODO: this leaks
        assert res == "aap"

        raises(TypeError, 'example01_class.staticStrcpy(1.)')   # TODO: this leaks

    def test04_constructing_and_calling(self):
        """Test object and method calls."""
        import cppyy
        example01_class = cppyy.gbl.example01
        assert example01_class.getCount() == 0
        instance = example01_class(7)
        assert example01_class.getCount() == 1
        res = instance.addDataToInt(4)
        assert res == 11
        res = instance.addDataToInt(-4)
        assert res == 3
        instance.destruct()
        assert example01_class.getCount() == 0
        raises(ReferenceError, 'instance.addDataToInt(4)')
        return

        instance = example01_class(7)
        instance2 = example01_class(8)
        assert example01_class.getCount() == 2
        instance.destruct()
        assert example01_class.getCount() == 1
        instance2.destruct()
        assert example01_class.getCount() == 0

        t = self.example01
        instance = example01_class(13)
        res = instance.addDataToDouble(16)
        assert round(res-29, 8) == 0.
        instance.destruct()
        instance = example01_class(-13)
        res = instance.addDataToDouble(16)
        assert round(res-3, 8) == 0.


        t = self.example01
        instance = example01_class(42)

        res = instance.addDataToAtoi("13")
        assert res == 55

        res = instance.addToStringValue("12")    # TODO: this leaks
        assert res == "54"
        res = instance.addToStringValue("-12")   # TODO: this leaks
        assert res == "30"

        res = instance.staticAddOneToInt(1L)
        assert res == 2

        instance.destruct()
        assert example01_class.getCount() == 0

    def test05_passing_object_by_pointer(self):
        import cppyy
        example01_class = cppyy.gbl.example01
        payload_class = cppyy.gbl.payload

        e = example01_class(14)
        pl = payload_class(3.14)
        assert round(pl.getData()-3.14, 8) == 0

        example01_class.staticSetPayload(pl, 41.)
        assert pl.getData() == 41.
        example01_class.staticSetPayload(pl, 43.)
        assert pl.getData() == 43.
        e.staticSetPayload(pl, 45.)
        assert pl.getData() == 45.

        e.setPayload(pl)
        assert round(pl.getData()-14., 8) == 0

        pl.destruct()
        e.destruct()
        assert example01_class.getCount() == 0

    def test06_returning_object_by_pointer(self):
        import cppyy
        example01_class = cppyy.gbl.example01
        payload_class = cppyy.gbl.payload

        pl = payload_class(3.14)
        assert round(pl.getData()-3.14, 8) == 0

        pl2 = example01_class.staticCyclePayload(pl, 38.)
        assert pl2.getData() == 38.

        e = example01_class(14)

        pl2 = e.cyclePayload(pl)
        assert round(pl2.getData()-14., 8) == 0

        pl.destruct()
        e.destruct()
        assert example01_class.getCount() == 0

    def test07_returning_object_by_value(self):
        import cppyy
        example01_class = cppyy.gbl.example01
        payload_class = cppyy.gbl.payload

        pl = payload_class(3.14)
        assert round(pl.getData()-3.14, 8) == 0

        pl2 = example01_class.staticCopyCyclePayload(pl, 38.)
        assert pl2.getData() == 38.
        pl2.destruct()

        e = example01_class(14)

        pl2 = e.copyCyclePayload(pl)
        assert round(pl2.getData()-14., 8) == 0
        pl2.destruct()

        pl.destruct()
        e.destruct()
        assert example01_class.getCount() == 0

    def test08_global_functions(self):
        import cppyy

        assert cppyy.gbl.globalAddOneToInt(3) == 4     # creation lookup
        assert cppyy.gbl.globalAddOneToInt(3) == 4     # cached lookup

        assert cppyy.gbl.ns_example01.globalAddOneToInt(4) == 5
        assert cppyy.gbl.ns_example01.globalAddOneToInt(4) == 5

    def test09_memory(self):
        """Test proper C++ destruction by the garbage collector"""

        import cppyy, gc
        example01_class = cppyy.gbl.example01
        payload_class = cppyy.gbl.payload

        pl = payload_class(3.14)
        assert payload_class.count == 1
        assert round(pl.getData()-3.14, 8) == 0

        pl2 = example01_class.staticCopyCyclePayload(pl, 38.)
        assert payload_class.count == 2
        assert pl2.getData() == 38.
        pl2 = None
        gc.collect()
        assert payload_class.count == 1

        e = example01_class(14)

        pl2 = e.copyCyclePayload(pl)
        assert payload_class.count == 2
        assert round(pl2.getData()-14., 8) == 0
        pl2 = None
        gc.collect()
        assert payload_class.count == 1

        pl = None
        e = None
        gc.collect()
        assert payload_class.count == 0
        assert example01_class.getCount() == 0

        pl = payload_class(3.14)
        pl_a = example01_class.staticCyclePayload(pl, 66.)
        pl_a.getData() == 66.
        assert payload_class.count == 1
        pl_a = None
        pl = None
        gc.collect()
        assert payload_class.count == 0

        # TODO: need ReferenceError on touching pl_a

    def test10_underscore_in_class_name(self):
        """Test recognition of '_' as part of a valid class name"""

        import cppyy

        assert cppyy.gbl.z_ == cppyy.gbl.z_

        z = cppyy.gbl.z_()

        assert hasattr(z, 'myint')
        assert z.gime_z_(z)

