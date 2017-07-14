import py, os, sys


currpath = py.path.local(__file__).dirpath()
test_dct = str(currpath.join("overloadsDict.so"))

def setup_module(mod):
    if sys.platform == 'win32':
        py.test.skip("win32 not supported so far")
    err = os.system("cd '%s' && make overloadsDict.so" % currpath)
    if err:
        raise OSError("'make' failed (see stderr)")

class AppTestOVERLOADS:
    spaceconfig = dict(usemodules=['cppyy', '_rawffi', 'itertools'])

    def setup_class(cls):
        env = os.environ
        cls.w_test_dct  = cls.space.newtext(test_dct)
        cls.w_overloads = cls.space.appexec([], """():
            import cppyy
            return cppyy.load_reflection_info(%r)""" % (test_dct, ))

    def test01_class_based_overloads(self):
        """Test functions overloaded on different C++ clases"""

        import cppyy
        a_overload = cppyy.gbl.a_overload
        b_overload = cppyy.gbl.b_overload
        c_overload = cppyy.gbl.c_overload
        d_overload = cppyy.gbl.d_overload

        ns_a_overload = cppyy.gbl.ns_a_overload
        ns_b_overload = cppyy.gbl.ns_b_overload

        assert c_overload().get_int(a_overload()) == 42
        assert c_overload().get_int(b_overload()) == 13
        assert d_overload().get_int(a_overload()) == 42
        assert d_overload().get_int(b_overload()) == 13

        assert c_overload().get_int(ns_a_overload.a_overload()) ==  88
        assert c_overload().get_int(ns_b_overload.a_overload()) == -33

        assert d_overload().get_int(ns_a_overload.a_overload()) ==  88
        assert d_overload().get_int(ns_b_overload.a_overload()) == -33

    def test02_class_based_overloads_explicit_resolution(self):
        """Test explicitly resolved function overloads"""

        import cppyy
        a_overload = cppyy.gbl.a_overload
        b_overload = cppyy.gbl.b_overload
        c_overload = cppyy.gbl.c_overload
        d_overload = cppyy.gbl.d_overload

        ns_a_overload = cppyy.gbl.ns_a_overload

        c = c_overload()
        raises(TypeError, c.__dispatch__, 'get_int', 12)
        raises(TypeError, c.__dispatch__, 'get_int', 'does_not_exist')
        assert c.__dispatch__('get_int', 'a_overload*')(a_overload()) == 42
        assert c.__dispatch__('get_int', 'b_overload*')(b_overload()) == 13

        assert c_overload().__dispatch__('get_int', 'a_overload*')(a_overload())  == 42
        # TODO: #assert c_overload.__dispatch__('get_int', 'b_overload*')(c, b_overload()) == 13

        d = d_overload()
        assert d.__dispatch__('get_int', 'a_overload*')(a_overload()) == 42
        assert d.__dispatch__('get_int', 'b_overload*')(b_overload()) == 13

        nb = ns_a_overload.b_overload()
        raises(TypeError, nb.f, c_overload())

    def test03_fragile_class_based_overloads(self):
        """Test functions overloaded on void* and non-existing classes"""

        # TODO: make Reflex generate unknown classes ...

        import cppyy
        more_overloads = cppyy.gbl.more_overloads
        aa_ol = cppyy.gbl.aa_ol
#        bb_ol = cppyy.gbl.bb_ol
        cc_ol = cppyy.gbl.cc_ol
#        dd_ol = cppyy.gbl.dd_ol

        assert more_overloads().call(aa_ol()) == "aa_ol"
#        assert more_overloads().call(bb_ol()) == "dd_ol"    # <- bb_ol has an unknown + void*
        assert more_overloads().call(cc_ol()) == "cc_ol"
#        assert more_overloads().call(dd_ol()) == "dd_ol"    # <- dd_ol has an unknown

    def test04_fully_fragile_overloads(self):
        """Test that unknown* is preferred over unknown&"""

        # TODO: make Reflex generate unknown classes ...
        return

        import cppyy
        more_overloads2 = cppyy.gbl.more_overloads2
        bb_ol = cppyy.gbl.bb_ol
        dd_ol = cppyy.gbl.dd_ol

        assert more_overloads2().call(bb_ol())    == "bb_olptr"
        assert more_overloads2().call(dd_ol(), 1) == "dd_olptr"

    def test05_array_overloads(self):
        """Test functions overloaded on different arrays"""

        import cppyy
        c_overload = cppyy.gbl.c_overload
        d_overload = cppyy.gbl.d_overload

        from array import array

        ai = array('i', [525252])
        assert c_overload().get_int(ai) == 525252
        assert d_overload().get_int(ai) == 525252

        ah = array('h', [25])
        assert c_overload().get_int(ah) == 25
        assert d_overload().get_int(ah) == 25

    def test06_double_int_overloads(self):
        """Test overloads on int/doubles"""

        import cppyy
        more_overloads = cppyy.gbl.more_overloads

        assert more_overloads().call(1)   == "int"
        assert more_overloads().call(1.)  == "double"
        assert more_overloads().call1(1)  == "int"
        assert more_overloads().call1(1.) == "double"

    def test07_mean_overloads(self):
        """Adapted test for array overloading"""

        import cppyy, array
        cmean = cppyy.gbl.calc_mean

        numbers = [8, 2, 4, 2, 4, 2, 4, 4, 1, 5, 6, 3, 7]
        mean, median = 4.0, 4.0

        for l in ['f', 'd', 'i', 'h', 'l']:
            a = array.array(l, numbers)
            assert round(cmean(len(a), a) - mean, 8) == 0
