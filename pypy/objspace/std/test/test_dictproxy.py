

class AppTestUserObject:
    def test_dictproxy(self):
        class NotEmpty(object):
            a = 1
        #assert isinstance(NotEmpty.__dict__, dict) == False
        assert 'a' in NotEmpty.__dict__
        assert 'a' in NotEmpty.__dict__.keys()
        assert 'b' not in NotEmpty.__dict__
        #assert isinstance(NotEmpty.__dict__.copy(), dict)
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
        s = repr(a.__dict__)
        #assert s.startswith('<dictproxy') and s.endswith('>')
        s = str(a.__dict__)
        assert s.startswith('{') and s.endswith('}')
