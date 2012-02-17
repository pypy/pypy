import py, os, sys
from pypy.conftest import gettestobjspace


currpath = py.path.local(__file__).dirpath()
test_dct = str(currpath.join("stltypesDict.so"))

space = gettestobjspace(usemodules=['cppyy'])

def setup_module(mod):
    if sys.platform == 'win32':
        py.test.skip("win32 not supported so far")
    err = os.system("cd '%s' && make stltypesDict.so" % currpath)
    if err:
        raise OSError("'make' failed (see stderr)")

class AppTestSTLVECTOR:
    def setup_class(cls):
        cls.space = space
        env = os.environ
        cls.w_N = space.wrap(13)
        cls.w_test_dct  = space.wrap(test_dct)
        cls.w_stlvector = cls.space.appexec([], """():
            import cppyy
            return cppyy.load_reflection_info(%r)""" % (test_dct, ))

    def test01_builtin_type_vector_type(self):
        """Test access to an std::vector<int>"""

        import cppyy

        assert cppyy.gbl.std        is cppyy.gbl.std
        assert cppyy.gbl.std.vector is cppyy.gbl.std.vector

        assert callable(cppyy.gbl.std.vector)

        tv1 = getattr(cppyy.gbl.std, 'vector<int>')
        tv2 = cppyy.gbl.std.vector('int')

        assert tv1 is tv2

        #-----
        v = tv1(self.N)
        for i in range(self.N):
          #  v[i] = i
          #  assert v[i] == i
          #  assert v.at(i) == i
            pass

        assert v.size() == self.N
        assert len(v) == self.N
        v.destruct()

        #-----
        v = tv1()
        for i in range(self.N):
            v.push_back(i)
            assert v.size() == i+1
            assert v.at(i) == i
            assert v[i] == i

        assert v.size() == self.N
        assert len(v) == self.N
        v.destruct()

    def test02_user_type_vector_type(self):
        """Test access to an std::vector<just_a_class>"""

        import cppyy

        assert cppyy.gbl.std        is cppyy.gbl.std
        assert cppyy.gbl.std.vector is cppyy.gbl.std.vector

        assert callable(cppyy.gbl.std.vector)

        tv1 = getattr(cppyy.gbl.std, 'vector<just_a_class>')
        tv2 = cppyy.gbl.std.vector('just_a_class')
        tv3 = cppyy.gbl.std.vector(cppyy.gbl.just_a_class)

        assert tv1 is tv2
        assert tv2 is tv3

        v = tv3()
        assert hasattr(v, 'size' )
        assert hasattr(v, 'push_back' )
        assert hasattr(v, '__getitem__' )
        assert hasattr(v, 'begin' )
        assert hasattr(v, 'end' )

        for i in range(self.N):
             v.push_back(cppyy.gbl.just_a_class())
             v[i].m_i = i
             assert v[i].m_i == i

        assert len(v) == self.N
        v.destruct()

    def test03_empty_vector_type(self):
        """Test behavior of empty std::vector<int>"""

        import cppyy

        v = cppyy.gbl.std.vector(int)()
        for arg in v:
            pass
        v.destruct()

    def test04_vector_iteration(self):
        """Test iteration over an std::vector<int>"""

        import cppyy

        v = cppyy.gbl.std.vector(int)()

        for i in range(self.N):
            v.push_back(i)
            assert v.size() == i+1
            assert v.at(i) == i
            assert v[i] == i

        assert v.size() == self.N
        assert len(v) == self.N

        i = 0
        for arg in v:
            assert arg == i
            i += 1

        assert list(v) == [i for i in range(self.N)]

        v.destruct()


class AppTestSTLSTRING:
    def setup_class(cls):
        cls.space = space
        env = os.environ
        cls.w_test_dct  = space.wrap(test_dct)
        cls.w_stlstring = cls.space.appexec([], """():
            import cppyy
            return cppyy.load_reflection_info(%r)""" % (test_dct, ))

    def test01_string_argument_passing(self):
        """Test mapping of python strings and std::string"""

        import cppyy
        std = cppyy.gbl.std
        stringy_class = cppyy.gbl.stringy_class

        c, s = stringy_class(""), std.string("test1")

        # pass through const std::string&
        c.set_string1(s)
        assert c.get_string1() == s

        return

        c.set_string1("test2")
        assert c.get_string1() == "test2"

        # pass through std::string (by value)
        s = std.string("test3")
        c.set_string2(s)
        assert c.get_string1() == s

        c.set_string2("test4")
        assert c.get_string1() == "test4"

        # getting through std::string&
        s2 = std.string()
        c.get_string2(s2)
        assert s2 == "test4"

        raises(TypeError, c.get_string2, "temp string")

    def test02_string_data_ccess(self):
        """Test access to std::string object data members"""

        import cppyy
        std = cppyy.gbl.std
        stringy_class = cppyy.gbl.stringy_class

        return

        c, s = stringy_class(""), std.string("test string")

        c.m_string = s
        assert c.m_string == s
        assert c.get_string1() == s

        c.m_string = "another test"
        assert c.m_string == "another test"
        assert c.get_string1() == "another test"

    def test03_string_with_null_character(self):
        """Test that strings with NULL do not get truncated"""

        import cppyy
        std = cppyy.gbl.std
        stringy_class = cppyy.gbl.stringy_class

        return

        t0 = "aap\0noot"
        self.assertEqual(t0, "aap\0noot")

        c, s = stringy_class(""), std.string(t0, len(t0))

        c.set_string1(s)
        assert t0 == c.get_string1()
        assert s == c.get_string1()
