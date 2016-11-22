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
        assert NotEmpty.__dict__.get("b") is None
        raises(TypeError, "NotEmpty.__dict__['b'] = 4")
        raises(TypeError, 'NotEmpty.__dict__[15] = "y"')
        raises(TypeError, 'del NotEmpty.__dict__[15]')

        raises(AttributeError, 'NotEmpty.__dict__.setdefault')

    def test_dictproxy_getitem(self):
        class NotEmpty(object):
            a = 1
        assert 'a' in NotEmpty.__dict__
        class substr(str):
            pass
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
        assert s1.startswith('dict_proxy({') and s1.endswith('})')
        s2 = str(a.__dict__)
        assert s1 == 'dict_proxy(%s)' % s2

    def test_immutable_dict_on_builtin_type(self):
        raises(TypeError, "int.__dict__['a'] = 1")
        raises((AttributeError, TypeError), "int.__dict__.popitem()")
        raises((AttributeError, TypeError), "int.__dict__.clear()")

    def test_dictproxy(self):
        dictproxy = type(int.__dict__)
        assert dictproxy is not dict
        assert dictproxy.__name__ == 'dictproxy'
        raises(TypeError, dictproxy)

        mapping = {'a': 1}
        raises(TypeError, dictproxy, mapping)

        class A(object):
            a = 1

        proxy = A.__dict__
        mapping = dict(proxy)
        assert proxy['a'] == 1
        assert 'a' in proxy
        assert 'z' not in proxy
        assert repr(proxy) == 'dict_proxy(%r)' % mapping
        assert proxy.keys() == mapping.keys()
        assert list(proxy.iterkeys()) == proxy.keys()
        assert list(proxy.itervalues()) == proxy.values()
        assert list(proxy.iteritems()) == proxy.items()
        raises(TypeError, "proxy['a'] = 4")
        raises(TypeError, "del proxy['a']")
        raises(AttributeError, "proxy.clear()")

class AppTestUserObjectMethodCache(AppTestUserObject):
    spaceconfig = {"objspace.std.withmethodcachecounter": True}
