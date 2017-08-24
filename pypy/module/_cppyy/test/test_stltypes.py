import py, os, sys


currpath = py.path.local(__file__).dirpath()
test_dct = str(currpath.join("stltypesDict.so"))

def setup_module(mod):
    if sys.platform == 'win32':
        py.test.skip("win32 not supported so far")
    err = os.system("cd '%s' && make stltypesDict.so" % currpath)
    if err:
        raise OSError("'make' failed (see stderr)")

class AppTestSTLVECTOR:
    spaceconfig = dict(usemodules=['_cppyy', '_rawffi', 'itertools'])

    def setup_class(cls):
        cls.w_N = cls.space.newint(13)
        cls.w_test_dct  = cls.space.newtext(test_dct)
        cls.w_stlvector = cls.space.appexec([], """():
            import _cppyy
            return _cppyy.load_reflection_info(%r)""" % (test_dct, ))

    def test01_builtin_type_vector_types(self):
        """Test access to std::vector<int>/std::vector<double>"""

        import _cppyy

        assert _cppyy.gbl.std        is _cppyy.gbl.std
        assert _cppyy.gbl.std.vector is _cppyy.gbl.std.vector

        assert callable(_cppyy.gbl.std.vector)

        type_info = (
            ("int",     int),
            ("float",   "float"),
            ("double",  "double"),
        )

        for c_type, p_type in type_info:
            tv1 = getattr(_cppyy.gbl.std, 'vector<%s>' % c_type)
            tv2 = _cppyy.gbl.std.vector(p_type)
            assert tv1 is tv2
            assert tv1.iterator is _cppyy.gbl.std.vector(p_type).iterator

            #----- 
            v = tv1(); v += range(self.N)    # default args from Reflex are useless :/
            if p_type == int:                # only type with == and != reflected in .xml
                assert v.begin().__eq__(v.begin())
                assert v.begin() == v.begin()
                assert v.end() == v.end()
                assert v.begin() != v.end()
                assert v.end() != v.begin()

            #-----
            for i in range(self.N):
                v[i] = i
                assert v[i] == i
                assert v.at(i) == i

            assert v.size() == self.N
            assert len(v) == self.N

            #-----
            v = tv1()
            for i in range(self.N):
                v.push_back(i)
                assert v.size() == i+1
                assert v.at(i) == i
                assert v[i] == i

            assert v.size() == self.N
            assert len(v) == self.N

    def test02_user_type_vector_type(self):
        """Test access to an std::vector<just_a_class>"""

        import _cppyy

        assert _cppyy.gbl.std        is _cppyy.gbl.std
        assert _cppyy.gbl.std.vector is _cppyy.gbl.std.vector

        assert callable(_cppyy.gbl.std.vector)

        tv1 = getattr(_cppyy.gbl.std, 'vector<just_a_class>')
        tv2 = _cppyy.gbl.std.vector('just_a_class')
        tv3 = _cppyy.gbl.std.vector(_cppyy.gbl.just_a_class)

        assert tv1 is tv2
        assert tv2 is tv3

        v = tv3()
        assert hasattr(v, 'size' )
        assert hasattr(v, 'push_back' )
        assert hasattr(v, '__getitem__' )
        assert hasattr(v, 'begin' )
        assert hasattr(v, 'end' )

        for i in range(self.N):
            v.push_back(_cppyy.gbl.just_a_class())
            v[i].m_i = i
            assert v[i].m_i == i

        assert len(v) == self.N
        v.destruct()

    def test03_empty_vector_type(self):
        """Test behavior of empty std::vector<int>"""

        import _cppyy

        v = _cppyy.gbl.std.vector(int)()
        for arg in v:
            pass
        v.destruct()

    def test04_vector_iteration(self):
        """Test iteration over an std::vector<int>"""

        import _cppyy

        v = _cppyy.gbl.std.vector(int)()

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

    def test05_push_back_iterables_with_iadd(self):
        """Test usage of += of iterable on push_back-able container"""

        import _cppyy

        v = _cppyy.gbl.std.vector(int)()

        v += [1, 2, 3]
        assert len(v) == 3
        assert v[0] == 1
        assert v[1] == 2
        assert v[2] == 3

        v += (4, 5, 6)
        assert len(v) == 6
        assert v[3] == 4
        assert v[4] == 5
        assert v[5] == 6

        raises(TypeError, v.__iadd__, (7, '8'))  # string shouldn't pass
        assert len(v) == 7   # TODO: decide whether this should roll-back

        v2 = _cppyy.gbl.std.vector(int)()
        v2 += [8, 9]
        assert len(v2) == 2
        assert v2[0] == 8
        assert v2[1] == 9

        v += v2
        assert len(v) == 9
        assert v[6] == 7
        assert v[7] == 8
        assert v[8] == 9

    def test06_vector_indexing(self):
        """Test python-style indexing to an std::vector<int>"""

        import _cppyy

        v = _cppyy.gbl.std.vector(int)()

        for i in range(self.N):
            v.push_back(i)

        raises(IndexError, 'v[self.N]')
        raises(IndexError, 'v[self.N+1]')

        assert v[-1] == self.N-1
        assert v[-2] == self.N-2

        assert len(v[0:0]) == 0
        assert v[1:2][0] == v[1]

        v2 = v[2:-1]
        assert len(v2) == self.N-3     # 2 off from start, 1 from end
        assert v2[0] == v[2]
        assert v2[-1] == v[-2]
        assert v2[self.N-4] == v[-2]


class AppTestSTLSTRING:
    spaceconfig = dict(usemodules=['_cppyy', '_rawffi', 'itertools'])

    def setup_class(cls):
        cls.w_test_dct  = cls.space.newtext(test_dct)
        cls.w_stlstring = cls.space.appexec([], """():
            import _cppyy
            return _cppyy.load_reflection_info(%r)""" % (test_dct, ))

    def test01_string_argument_passing(self):
        """Test mapping of python strings and std::string"""

        import _cppyy
        std = _cppyy.gbl.std
        stringy_class = _cppyy.gbl.stringy_class

        c, s = stringy_class(""), std.string("test1")

        # pass through const std::string&
        c.set_string1(s)
        assert c.get_string1() == s

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

    def test02_string_data_access(self):
        """Test access to std::string object data members"""

        import _cppyy
        std = _cppyy.gbl.std
        stringy_class = _cppyy.gbl.stringy_class

        c, s = stringy_class("dummy"), std.string("test string")

        c.m_string = "another test"
        assert c.m_string == "another test"
        assert str(c.m_string) == c.m_string
        assert c.get_string1() == "another test"

        c.m_string = s
        assert str(c.m_string) == s
        assert c.m_string == s
        assert c.get_string1() == s

    def test03_string_with_null_character(self):
        """Test that strings with NULL do not get truncated"""

        return # don't bother; is fixed in cling-support

        import _cppyy
        std = _cppyy.gbl.std
        stringy_class = _cppyy.gbl.stringy_class

        t0 = "aap\0noot"
        assert t0 == "aap\0noot"

        c, s = stringy_class(""), std.string(t0, len(t0))

        c.set_string1(s)
        assert t0 == c.get_string1()
        assert s == c.get_string1()


class AppTestSTLLIST:
    spaceconfig = dict(usemodules=['_cppyy', '_rawffi', 'itertools'])

    def setup_class(cls):
        cls.w_N = cls.space.newint(13)
        cls.w_test_dct  = cls.space.newtext(test_dct)
        cls.w_stlstring = cls.space.appexec([], """():
            import _cppyy
            return _cppyy.load_reflection_info(%r)""" % (test_dct, ))

    def test01_builtin_list_type(self):
        """Test access to a list<int>"""

        import _cppyy
        from _cppyy.gbl import std

        type_info = (
            ("int",     int),
            ("float",   "float"),
            ("double",  "double"),
        )

        for c_type, p_type in type_info:
            tl1 = getattr(std, 'list<%s>' % c_type)
            tl2 = _cppyy.gbl.std.list(p_type)
            assert tl1 is tl2
            assert tl1.iterator is _cppyy.gbl.std.list(p_type).iterator

            #-----
            a = tl1()
            for i in range(self.N):
                a.push_back( i )

            assert len(a) == self.N
            assert 11 < self.N
            assert 11 in a

            #-----
            ll = list(a)
            for i in range(self.N):
                assert ll[i] == i

            for val in a:
                assert ll[ll.index(val)] == val

    def test02_empty_list_type(self):
        """Test behavior of empty list<int>"""

        import _cppyy
        from _cppyy.gbl import std

        a = std.list(int)()
        for arg in a:
            pass


class AppTestSTLMAP:
    spaceconfig = dict(usemodules=['_cppyy', '_rawffi', 'itertools'])

    def setup_class(cls):
        cls.w_N = cls.space.newint(13)
        cls.w_test_dct  = cls.space.newtext(test_dct)
        cls.w_stlstring = cls.space.appexec([], """():
            import _cppyy
            return _cppyy.load_reflection_info(%r)""" % (test_dct, ))

    def test01_builtin_map_type(self):
        """Test access to a map<int,int>"""

        import _cppyy
        std = _cppyy.gbl.std

        a = std.map(int, int)()
        for i in range(self.N):
            a[i] = i
            assert a[i] == i

        assert len(a) == self.N

        for key, value in a:
            assert key == value
        assert key   == self.N-1
        assert value == self.N-1

        # add a variation, just in case
        m = std.map(int, int)()
        for i in range(self.N):
            m[i] = i*i
            assert m[i] == i*i

        for key, value in m:
            assert key*key == value
        assert key   == self.N-1
        assert value == (self.N-1)*(self.N-1)

    def test02_keyed_maptype(self):
        """Test access to a map<std::string,int>"""

        import _cppyy
        std = _cppyy.gbl.std

        a = std.map(std.string, int)()
        for i in range(self.N):
            a[str(i)] = i
            assert a[str(i)] == i

        assert len(a) == self.N

    def test03_empty_maptype(self):
        """Test behavior of empty map<int,int>"""

        import _cppyy
        std = _cppyy.gbl.std

        m = std.map(int, int)()
        for key, value in m:
            pass

    def test04_unsignedvalue_typemap_types(self):
        """Test assignability of maps with unsigned value types"""

        import _cppyy, math, sys
        std = _cppyy.gbl.std

        mui = std.map(str, 'unsigned int')()
        mui['one'] = 1
        assert mui['one'] == 1
        raises(ValueError, mui.__setitem__, 'minus one', -1)

        # UInt_t is always 32b, sys.maxint follows system int
        maxint32 = int(math.pow(2,31)-1)
        mui['maxint'] = maxint32 + 3
        assert mui['maxint'] == maxint32 + 3

        mul = std.map(str, 'unsigned long')()
        mul['two'] = 2
        assert mul['two'] == 2
        mul['maxint'] = sys.maxint + 3
        assert mul['maxint'] == sys.maxint + 3

        raises(ValueError, mul.__setitem__, 'minus two', -2)

    def test05_STL_like_class_indexing_overloads(self):
        """Test overloading of operator[] in STL like class"""

        import _cppyy
        stl_like_class = _cppyy.gbl.stl_like_class

        a = stl_like_class(int)()
        assert a["some string" ] == 'string'
        assert a[3.1415] == 'double'

    def test06_STL_like_class_iterators(self):
        """Test the iterator protocol mapping for an STL like class"""

        import _cppyy
        stl_like_class = _cppyy.gbl.stl_like_class

        a = stl_like_class(int)()
        for i in a:
            pass

        assert i == 3


class AppTestSTLITERATOR:
    spaceconfig = dict(usemodules=['_cppyy', '_rawffi', 'itertools'])

    def setup_class(cls):
        cls.w_test_dct  = cls.space.newtext(test_dct)
        cls.w_stlstring = cls.space.appexec([], """():
            import _cppyy, sys
            return _cppyy.load_reflection_info(%r)""" % (test_dct, ))

    def test01_builtin_vector_iterators(self):
        """Test iterator comparison with operator== reflected"""

        import _cppyy
        from _cppyy.gbl import std

        v = std.vector(int)()
        v.resize(1)

        b1, e1 = v.begin(), v.end()
        b2, e2 = v.begin(), v.end()

        assert b1 == b2
        assert not b1 != b2

        assert e1 == e2
        assert not e1 != e2

        assert not b1 == e1
        assert b1 != e1

        b1.__preinc__()
        assert not b1 == b2
        assert b1 == e2
        assert b1 != b2
        assert b1 == e2


class AppTestTEMPLATE_UI:
    spaceconfig = dict(usemodules=['_cppyy', '_rawffi', 'itertools'])

    def setup_class(cls):
        cls.w_test_dct  = cls.space.newtext(test_dct)
        cls.w_stlstring = cls.space.appexec([], """():
            import _cppyy, sys
            return _cppyy.load_reflection_info(%r)""" % (test_dct, ))

    def test01_explicit_templates(self):
        """Explicit use of Template class"""

        import _cppyy

        vector = _cppyy.Template('vector', _cppyy.gbl.std)
        assert vector[int] == vector(int)

        v = vector[int]()

        N = 10
        v += range(N)
        assert len(v) == N
        for i in range(N):
            assert v[i] == i
