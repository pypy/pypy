from pypy.conftest import gettestobjspace

class AppTestUserObject:
    def test_dictproxy(self):
        class NotEmpty(object):
            a = 1
        NotEmpty.a = 1
        NotEmpty.a = 1
        NotEmpty.a = 1
        NotEmpty.a = 1
        assert 'a' in NotEmpty.__dict__
        assert 'a' in NotEmpty.__dict__.keys()
        assert 'b' not in NotEmpty.__dict__
        NotEmpty.__dict__['b'] = 4
        assert NotEmpty.b == 4
        del NotEmpty.__dict__['b']
        assert NotEmpty.__dict__.get("b") is None
        raises(TypeError, 'NotEmpty.__dict__[15] = "y"')
        raises(KeyError, 'del NotEmpty.__dict__[15]')
        assert NotEmpty.__dict__.setdefault("string", 1) == 1
        assert NotEmpty.__dict__.setdefault("string", 2) == 1
        assert NotEmpty.string == 1
        raises(TypeError, 'NotEmpty.__dict__.setdefault(15, 1)')

        key, value = NotEmpty.__dict__.popitem()
        assert (key == 'a' and value == 1) or (key == 'b' and value == 4)

    def test_dictproxy_getitem(self):
        class NotEmpty(object):
            a = 1
        assert 'a' in NotEmpty.__dict__
        class substr(str): pass
        assert substr('a') in NotEmpty.__dict__
        assert u'a' in NotEmpty.__dict__
        assert NotEmpty.__dict__[u'a'] == 1
        assert u'\xe9' not in NotEmpty.__dict__

    def test_dictproxyeq(self):
        class a(object):
            pass
        class b(a):
            stuff = 42
        class c(a):
            stuff = 42
        assert a.__dict__ == a.__dict__
        assert a.__dict__ != b.__dict__
        assert a.__dict__ != {'123': '456'}
        assert {'123': '456'} != a.__dict__
        assert b.__dict__ == c.__dict__

    def test_str_repr(self):
        class a(object):
            pass
        s1 = repr(a.__dict__)
        s2 = str(a.__dict__)
        assert s1 == s2
        assert s1.startswith('{') and s1.endswith('}')

    def test_immutable_dict_on_builtin_type(self):
        raises(TypeError, "int.__dict__['a'] = 1")
        raises(TypeError, int.__dict__.popitem)
        raises(TypeError, int.__dict__.clear)

class AppTestUserObjectMethodCache(AppTestUserObject):
    def setup_class(cls):
        cls.space = gettestobjspace(
            **{"objspace.std.withmethodcachecounter": True})

