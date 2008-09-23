from py.test import raises

from pypy.objspace.std import multimethod
from pypy.objspace.std.multimethod import FailedToImplement


class W_Root(object):
    pass

class W_IntObject(W_Root):
    pass

class W_BoolObject(W_Root):
    pass

class W_StringObject(W_Root):
    pass

def delegate_b2i(space, w_x):
    assert isinstance(w_x, W_BoolObject)
    return W_IntObject()

def add__Int_Int(space, w_x, w_y):
    assert space == 'space'
    assert isinstance(w_x, W_IntObject)
    assert isinstance(w_y, W_IntObject)
    return 'fine'


class TestMultiMethod1:
    Installer = multimethod.InstallerVersion1

    def setup_class(cls):
        cls.prev_installer = multimethod.Installer
        multimethod.Installer = cls.Installer
        add = multimethod.MultiMethodTable(2, root_class=W_Root,
                                           argnames_before=['space'])
        add.register(add__Int_Int, W_IntObject, W_IntObject)
        typeorder = {
            W_IntObject: [(W_IntObject, None), (W_Root, None)],
            W_BoolObject: [(W_BoolObject, None), (W_IntObject, delegate_b2i),
                           (W_Root, None)],
            W_StringObject: [(W_StringObject, None), (W_Root, None)],
            }
        cls.typeorder = typeorder
        cls.add = add
        cls.add1 = staticmethod(add.install('__add', [typeorder, typeorder]))

    def teardown_class(cls):
        multimethod.Installer = cls.prev_installer

    def test_simple(self):
        space = 'space'
        w_x = W_IntObject()
        w_y = W_IntObject()
        assert self.add1(space, w_x, w_y) == 'fine'

    def test_failtoimplement(self):
        space = 'space'
        w_x = W_IntObject()
        w_s = W_StringObject()
        raises(FailedToImplement, "self.add1(space, w_x, w_s)")
        raises(FailedToImplement, "self.add1(space, w_s, w_x)")

    def test_delegate(self):
        space = 'space'
        w_x = W_IntObject()
        w_s = W_StringObject()
        w_b = W_BoolObject()
        assert self.add1(space, w_x, w_b) == 'fine'
        assert self.add1(space, w_b, w_x) == 'fine'
        assert self.add1(space, w_b, w_b) == 'fine'
        raises(FailedToImplement, "self.add1(space, w_b, w_s)")
        raises(FailedToImplement, "self.add1(space, w_s, w_b)")

    def test_not_baked(self):
        typeorder = self.typeorder
        add2 = self.add.install('__add2', [typeorder, typeorder],
                                baked_perform_call=False)
        assert add2[0] == ['space', 'arg0', 'arg1']
        if multimethod.Installer is multimethod.InstallerVersion1:
            assert add2[1] == 'arg0.__add2(space, arg1)'
        assert isinstance(add2[2], dict)
        assert not add2[3]

    def test_empty(self):
        add3_installer = multimethod.Installer(self.add, '__add3', [{},{}])
        assert add3_installer.is_empty()
        if multimethod.Installer is multimethod.InstallerVersion1:
            assert len(add3_installer.to_install) == 1
            assert add3_installer.to_install[0][0] is None

    def test_empty_direct(self):
        assert not self.add.install_if_not_empty('__add4', [{},{}])

    def test_empty_not_baked(self):
        add5_installer = multimethod.Installer(self.add, '__add5', [{},{}],
                                               baked_perform_call=False)
        assert add5_installer.is_empty()
        if multimethod.Installer is multimethod.InstallerVersion1:
            assert len(add5_installer.to_install) == 0
        add5 = add5_installer.install()
        assert add5[0] == ['space', 'arg0', 'arg1']
        assert add5[1] == 'raiseFailedToImplement()'
        assert isinstance(add5[2], dict)
        assert add5[3]

    def test_mmdispatcher(self):
        typeorder = self.typeorder
        add2 = multimethod.MMDispatcher(self.add, [typeorder, typeorder])
        space = 'space'
        w_x = W_IntObject()
        w_s = W_StringObject()
        w_b1 = W_BoolObject()
        w_b2 = W_BoolObject()
        assert add2(space, w_x, w_b1) == 'fine'
        assert add2(space, w_b2, w_x) == 'fine'
        assert add2(space, w_b1, w_b2) == 'fine'
        raises(FailedToImplement, "add2(space, w_b2, w_s)")
        raises(FailedToImplement, "add2(space, w_s, w_b1)")

    def test_forbidden_subclasses(self):
        mul = multimethod.MultiMethodTable(2, root_class=W_Root,
                                           argnames_before=['space'])
        class UserW_StringObject(W_StringObject):
            pass
        def mul__Int_String(space, w_x, w_y):
            assert space == 'space'
            assert isinstance(w_x, W_IntObject)
            assert isinstance(w_y, W_StringObject)
            return 'fine'
        mul.register(mul__Int_String, W_IntObject, W_StringObject)

        mul1 = mul.install('__mul1', [self.typeorder, self.typeorder])
        assert mul1('space', W_IntObject(), W_StringObject()) == 'fine'
        assert mul1('space', W_IntObject(), UserW_StringObject()) == 'fine'

        ext_typeorder = self.typeorder.copy()
        ext_typeorder[UserW_StringObject] = []
        mul2 = mul.install('__mul2', [ext_typeorder, ext_typeorder])
        assert mul2('space', W_IntObject(), W_StringObject()) == 'fine'
        raises(FailedToImplement,
               mul2, 'baz', W_IntObject(), UserW_StringObject())

    def test_more_forbidden_subclasses(self):
        mul = multimethod.MultiMethodTable(2, root_class=W_Root,
                                           argnames_before=['space'])
        class UserW_StringObject(W_StringObject):
            pass
        def mul__String_String(space, w_x, w_y):
            assert space == 'space'
            assert isinstance(w_x, W_StringObject)
            assert isinstance(w_y, W_StringObject)
            return 'fine'
        mul.register(mul__String_String, W_StringObject, W_StringObject)

        ext_typeorder = {W_StringObject: [(W_StringObject, None)],
                         UserW_StringObject: []}
        mul2 = mul.install('__mul2', [ext_typeorder, ext_typeorder])
        assert mul2('space', W_StringObject(), W_StringObject()) == 'fine'
        raises(FailedToImplement,
               mul2, 'baz', W_StringObject(), UserW_StringObject())
        raises(FailedToImplement,
               mul2, 'baz', UserW_StringObject(), W_StringObject())
        raises(FailedToImplement,
               mul2, 'baz', UserW_StringObject(), UserW_StringObject())

    def test_ANY(self):
        setattr = multimethod.MultiMethodTable(3, root_class=W_Root,
                                           argnames_before=['space'])
        def setattr__Int_ANY_ANY(space, w_x, w_y, w_z):
            assert space == 'space'
            assert isinstance(w_x, W_IntObject)
            assert isinstance(w_y, W_Root)
            assert isinstance(w_z, W_Root)
            return w_y.__class__.__name__ + w_z.__class__.__name__
        setattr.register(setattr__Int_ANY_ANY, W_IntObject, W_Root, W_Root)
        setattr1 = setattr.install('__setattr1', [self.typeorder]*3)
        for cls1 in self.typeorder:
            for cls2 in self.typeorder:
                assert setattr1('space', W_IntObject(), cls1(), cls2()) == (
                    cls1.__name__ + cls2.__name__)

    def test_all_cases(self):
        import random
        space = 'space'
        w_x = W_IntObject()
        w_x.expected = [W_IntObject, W_Root]
        w_s = W_StringObject()
        w_s.expected = [W_StringObject, W_Root]
        w_b = W_BoolObject()
        w_b.expected = [W_BoolObject, W_IntObject, W_Root]

        def test(indices):
            sub = multimethod.MultiMethodTable(2, root_class=W_Root,
                                               argnames_before=['space'])
            def addimpl(cls1, cls2):
                token = random.random()
                def sub__cls1_cls2(space, w_x, w_y):
                    assert space == 'space'
                    assert isinstance(w_x, cls1)
                    assert isinstance(w_y, cls2)
                    return token
                sub.register(sub__cls1_cls2, cls1, cls2)
                return token

            def check(w1, w2):
                try:
                    res = sub1(space, w1, w2)
                except FailedToImplement:
                    res = FailedToImplement
                for cls1 in w1.expected:
                    for cls2 in w2.expected:
                        if (cls1, cls2) in expected:
                            assert res == expected[cls1, cls2]
                            return
                else:
                    assert res is FailedToImplement

            random.shuffle(indices)
            expected = {}
            for index in indices:
                cls1, cls2 = choices[index]
                token = addimpl(cls1, cls2)
                expected[cls1, cls2] = token

            typeorder = self.typeorder
            sub1 = sub.install('__sub', [typeorder, typeorder])
            for w1 in [w_x, w_s, w_b]:
                for w2 in [w_x, w_s, w_b]:
                    check(w1, w2)

        classes = [W_Root, W_StringObject, W_IntObject, W_BoolObject]
        choices = [(cls1, cls2) for cls1 in classes
                                for cls2 in classes]
        # each choice is a pair of classes which can be implemented or
        # not by the multimethod 'sub'.  Test all combinations that
        # involve at most three implemented choices.
        for i in range(len(choices)):
            test([i])
            for j in range(i+1, len(choices)):
                test([i, j])
                for k in range(j+1, len(choices)):
                    test([i, j, k])
                    #for l in range(k+1, len(choices)):  -- for a 4th choice
                    #    test([i, j, k, l])              -- (takes a while)


class TestMultiMethod2(TestMultiMethod1):
    Installer = multimethod.InstallerVersion2
