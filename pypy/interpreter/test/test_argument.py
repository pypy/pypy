# -*- coding: utf-8 -*-
import py
from pypy.interpreter.argument import (Arguments, ArgumentsForTranslation,
    ArgErr, ArgErrUnknownKwds, ArgErrMultipleValues, ArgErrCount, rawshape,
    Signature)
from pypy.interpreter.error import OperationError


class TestSignature(object):
    def test_helpers(self):
        sig = Signature(["a", "b", "c"], None, None)
        assert sig.num_argnames() == 3
        assert not sig.has_vararg()
        assert not sig.has_kwarg()
        assert sig.scope_length() == 3
        assert sig.getallvarnames() == ["a", "b", "c"]
        sig = Signature(["a", "b", "c"], "c", None)
        assert sig.num_argnames() == 3
        assert sig.has_vararg()
        assert not sig.has_kwarg()
        assert sig.scope_length() == 4
        assert sig.getallvarnames() == ["a", "b", "c", "c"]
        sig = Signature(["a", "b", "c"], None, "c")
        assert sig.num_argnames() == 3
        assert not sig.has_vararg()
        assert sig.has_kwarg()
        assert sig.scope_length() == 4
        assert sig.getallvarnames() == ["a", "b", "c", "c"]
        sig = Signature(["a", "b", "c"], "d", "c")
        assert sig.num_argnames() == 3
        assert sig.has_vararg()
        assert sig.has_kwarg()
        assert sig.scope_length() == 5
        assert sig.getallvarnames() == ["a", "b", "c", "d", "c"]

    def test_eq(self):
        sig1 = Signature(["a", "b", "c"], "d", "c")
        sig2 = Signature(["a", "b", "c"], "d", "c")
        assert sig1 == sig2


    def test_find_argname(self):
        sig = Signature(["a", "b", "c"], None, None)
        assert sig.find_argname("a") == 0
        assert sig.find_argname("b") == 1
        assert sig.find_argname("c") == 2
        assert sig.find_argname("d") == -1

    def test_tuply(self):
        sig = Signature(["a", "b", "c"], "d", "e")
        x, y, z = sig
        assert x == ["a", "b", "c"]
        assert y == "d"
        assert z == "e"

class dummy_wrapped_dict(dict):
    def __nonzero__(self):
        raise NotImplementedError

class DummySpace(object):
    def newtuple(self, items):
        return tuple(items)

    def is_true(self, obj):
        if isinstance(obj, dummy_wrapped_dict):
            return bool(dict(obj))
        return bool(obj)

    def fixedview(self, it):
        return list(it)

    def listview(self, it):
        return list(it)

    def unpackiterable(self, it):
        return list(it)

    def newdict(self):
        return {}

    def newlist(self, l=[]):
        return l

    def setitem(self, obj, key, value):
        obj[key] = value

    def getitem(self, obj, key):
        return obj[key]

    def wrap(self, obj):
        return obj

    def str_w(self, s):
        return str(s)

    def len(self, x):
        return len(x)

    def int_w(self, x):
        return x

    def eq_w(self, x, y):
        return x == y

    def isinstance(self, obj, cls):
        return isinstance(obj, cls)
    isinstance_w = isinstance

    def exception_match(self, w_type1, w_type2):
        return issubclass(w_type1, w_type2)

    def call_method(self, obj, name, *args):
        try:
            method = getattr(obj, name)
        except AttributeError:
            raise OperationError(AttributeError, name)
        return method(*args)

    def type(self, obj):
        class Type:
            def getname(self, space, default='?'):
                return type(obj).__name__
        return Type()


    w_TypeError = TypeError
    w_AttributeError = AttributeError
    w_UnicodeEncodeError = UnicodeEncodeError
    w_dict = dict
    w_str = str

class TestArgumentsNormal(object):

    def test_create(self):
        space = DummySpace()
        args_w = []
        args = Arguments(space, args_w)
        assert args.arguments_w is args_w
        assert args.keywords is None
        assert args.keywords_w is None

        assert args.firstarg() is None

        args = Arguments(space, args_w, w_stararg=["*"],
                         w_starstararg={"k": 1})
        assert args.arguments_w == ["*"]
        assert args.keywords == ["k"]
        assert args.keywords_w == [1]

        assert args.firstarg() == "*"

    def test_prepend(self):
        space = DummySpace()
        args = Arguments(space, ["0"])
        args1 = args.prepend("thingy")
        assert args1 is not args
        assert args1.arguments_w == ["thingy", "0"]
        assert args1.keywords is args.keywords
        assert args1.keywords_w is args.keywords_w

    def test_fixedunpacked(self):
        space = DummySpace()

        args = Arguments(space, [], ["k"], [1])
        py.test.raises(ValueError, args.fixedunpack, 1)

        args = Arguments(space, ["a", "b"])
        py.test.raises(ValueError, args.fixedunpack, 0)
        py.test.raises(ValueError, args.fixedunpack, 1)
        py.test.raises(ValueError, args.fixedunpack, 3)
        py.test.raises(ValueError, args.fixedunpack, 4)

        assert args.fixedunpack(2) == ['a', 'b']

    def test_match0(self):
        space = DummySpace()
        args = Arguments(space, [])
        l = []
        args._match_signature(None, l, Signature([]))
        assert len(l) == 0
        l = [None, None]
        args = Arguments(space, [])
        py.test.raises(ArgErr, args._match_signature, None, l, Signature(["a"]))
        args = Arguments(space, [])
        py.test.raises(ArgErr, args._match_signature, None, l, Signature(["a"], "*"))
        args = Arguments(space, [])
        l = [None]
        args._match_signature(None, l, Signature(["a"]), defaults_w=[1])
        assert l == [1]
        args = Arguments(space, [])
        l = [None]
        args._match_signature(None, l, Signature([], "*"))
        assert l == [()]
        args = Arguments(space, [])
        l = [None]
        args._match_signature(None, l, Signature([], None, "**"))
        assert l == [{}]
        args = Arguments(space, [])
        l = [None, None]
        py.test.raises(ArgErr, args._match_signature, 41, l, Signature([]))
        args = Arguments(space, [])
        l = [None]
        args._match_signature(1, l, Signature(["a"]))
        assert l == [1]
        args = Arguments(space, [])
        l = [None]
        args._match_signature(1, l, Signature([], "*"))
        assert l == [(1,)]

    def test_match4(self):
        space = DummySpace()
        values = [4, 5, 6, 7]
        for havefirstarg in [0, 1]:
            for i in range(len(values)-havefirstarg):
                arglist = values[havefirstarg:i+havefirstarg]
                starargs = tuple(values[i+havefirstarg:])
                if havefirstarg:
                    firstarg = values[0]
                else:
                    firstarg = None
                args = Arguments(space, arglist, w_stararg=starargs)
                l = [None, None, None, None]
                args._match_signature(firstarg, l, Signature(["a", "b", "c", "d"]))
                assert l == [4, 5, 6, 7]
                args = Arguments(space, arglist, w_stararg=starargs)
                l = [None, None, None, None, None, None]
                py.test.raises(ArgErr, args._match_signature, firstarg, l, Signature(["a"]))
                args = Arguments(space, arglist, w_stararg=starargs)
                l = [None, None, None, None, None, None]
                py.test.raises(ArgErr, args._match_signature, firstarg, l, Signature(["a", "b", "c", "d", "e"]))
                args = Arguments(space, arglist, w_stararg=starargs)
                l = [None, None, None, None, None, None]
                py.test.raises(ArgErr, args._match_signature, firstarg, l, Signature(["a", "b", "c", "d", "e"], "*"))
                l = [None, None, None, None, None]
                args = Arguments(space, arglist, w_stararg=starargs)
                args._match_signature(firstarg, l, Signature(["a", "b", "c", "d", "e"]), defaults_w=[1])
                assert l == [4, 5, 6, 7, 1]
                for j in range(len(values)):
                    l = [None] * (j + 1)
                    args = Arguments(space, arglist, w_stararg=starargs)
                    args._match_signature(firstarg, l, Signature(["a", "b", "c", "d", "e"][:j], "*"))
                    assert l == values[:j] + [tuple(values[j:])]
                l = [None, None, None, None, None]
                args = Arguments(space, arglist, w_stararg=starargs)
                args._match_signature(firstarg, l, Signature(["a", "b", "c", "d"], None, "**"))
                assert l == [4, 5, 6, 7, {}]

    def test_match_kwds(self):
        space = DummySpace()
        for i in range(3):
            kwds = [("c", 3)]
            kwds_w = dict(kwds[:i])
            keywords = kwds_w.keys()
            keywords_w = kwds_w.values()
            w_kwds = dummy_wrapped_dict(kwds[i:])
            if i == 2:
                w_kwds = None
            assert len(keywords) == len(keywords_w)
            args = Arguments(space, [1, 2], keywords[:], keywords_w[:], w_starstararg=w_kwds)
            l = [None, None, None]
            args._match_signature(None, l, Signature(["a", "b", "c"]), defaults_w=[4])
            assert l == [1, 2, 3]
            args = Arguments(space, [1, 2], keywords[:], keywords_w[:], w_starstararg=w_kwds)
            l = [None, None, None, None]
            args._match_signature(None, l, Signature(["a", "b", "b1", "c"]), defaults_w=[4, 5])
            assert l == [1, 2, 4, 3]
            args = Arguments(space, [1, 2], keywords[:], keywords_w[:], w_starstararg=w_kwds)
            l = [None, None, None, None]
            args._match_signature(None, l, Signature(["a", "b", "c", "d"]), defaults_w=[4, 5])
            assert l == [1, 2, 3, 5]
            args = Arguments(space, [1, 2], keywords[:], keywords_w[:], w_starstararg=w_kwds)
            l = [None, None, None, None]
            py.test.raises(ArgErr, args._match_signature, None, l,
                           Signature(["c", "b", "a", "d"]), defaults_w=[4, 5])
            args = Arguments(space, [1, 2], keywords[:], keywords_w[:], w_starstararg=w_kwds)
            l = [None, None, None, None]
            py.test.raises(ArgErr, args._match_signature, None, l,
                           Signature(["a", "b", "c1", "d"]), defaults_w=[4, 5])
            args = Arguments(space, [1, 2], keywords[:], keywords_w[:], w_starstararg=w_kwds)
            l = [None, None, None]
            args._match_signature(None, l, Signature(["a", "b"], None, "**"))
            assert l == [1, 2, {'c': 3}]

    def test_match_kwds2(self):
        space = DummySpace()
        kwds = [("c", 3), ('d', 4)]
        for i in range(4):
            kwds_w = dict(kwds[:i])
            keywords = kwds_w.keys()
            keywords_w = kwds_w.values()
            w_kwds = dummy_wrapped_dict(kwds[i:])
            if i == 3:
                w_kwds = None
            args = Arguments(space, [1, 2], keywords, keywords_w, w_starstararg=w_kwds)
            l = [None, None, None, None]
            args._match_signature(None, l, Signature(["a", "b", "c"], None, "**"))
            assert l == [1, 2, 3, {'d': 4}]

    def test_duplicate_kwds(self):
        space = DummySpace()
        excinfo = py.test.raises(OperationError, Arguments, space, [], ["a"],
                                 [1], w_starstararg={"a": 2})
        assert excinfo.value.w_type is TypeError

    def test_starstararg_wrong_type(self):
        space = DummySpace()
        excinfo = py.test.raises(OperationError, Arguments, space, [], ["a"],
                                 [1], w_starstararg="hello")
        assert excinfo.value.w_type is TypeError

    def test_unwrap_error(self):
        space = DummySpace()
        valuedummy = object()
        def str_w(w):
            if w is None:
                raise OperationError(TypeError, None)
            if w is valuedummy:
                raise OperationError(ValueError, None)
            return str(w)
        space.str_w = str_w
        excinfo = py.test.raises(OperationError, Arguments, space, [],
                                 ["a"], [1], w_starstararg={None: 1})
        assert excinfo.value.w_type is TypeError
        assert excinfo.value._w_value is not None
        excinfo = py.test.raises(OperationError, Arguments, space, [],
                                 ["a"], [1], w_starstararg={valuedummy: 1})
        assert excinfo.value.w_type is ValueError
        assert excinfo.value._w_value is None


    def test_blindargs(self):
        space = DummySpace()
        kwds = [("a", 3), ('b', 4)]
        for i in range(4):
            kwds_w = dict(kwds[:i])
            keywords = kwds_w.keys()
            keywords_w = kwds_w.values()
            w_kwds = dict(kwds[i:])
            if i == 3:
                w_kwds = None
            args = Arguments(space, [1, 2], keywords[:], keywords_w[:],
                             w_starstararg=w_kwds)
            l = [None, None, None]
            args._match_signature(None, l, Signature(["a", "b"], None, "**"), blindargs=2)
            assert l == [1, 2, {'a':3, 'b': 4}]
            args = Arguments(space, [1, 2], keywords[:], keywords_w[:],
                             w_starstararg=w_kwds)
            l = [None, None, None]
            py.test.raises(ArgErrUnknownKwds, args._match_signature, None, l,
                           Signature(["a", "b"]), blindargs=2)

    def test_args_parsing(self):
        space = DummySpace()
        args = Arguments(space, [])

        calls = []

        def _match_signature(w_firstarg, scope_w, signature,
                             defaults_w=None, blindargs=0):
            defaults_w = [] if defaults_w is None else defaults_w
            calls.append((w_firstarg, scope_w, signature.argnames, signature.has_vararg(),
                          signature.has_kwarg(), defaults_w, blindargs))
        args._match_signature = _match_signature

        scope_w = args.parse_obj(None, "foo", Signature(["a", "b"], None, None))
        assert len(calls) == 1
        assert calls[0] == (None, [None, None], ["a", "b"], False, False,
                            [], 0)
        assert calls[0][1] is scope_w
        calls = []

        scope_w = args.parse_obj(None, "foo", Signature(["a", "b"], "args", None),
                                 blindargs=1)
        assert len(calls) == 1
        assert calls[0] == (None, [None, None, None], ["a", "b"], True, False,
                            [], 1)
        calls = []

        scope_w = args.parse_obj(None, "foo", Signature(["a", "b"], "args", "kw"),
                             defaults_w=['x', 'y'])
        assert len(calls) == 1
        assert calls[0] == (None, [None, None, None, None], ["a", "b"],
                            True, True,
                            ["x", "y"], 0)
        calls = []

        scope_w = args.parse_obj("obj", "foo", Signature(["a", "b"], "args", "kw"),
                             defaults_w=['x', 'y'], blindargs=1)
        assert len(calls) == 1
        assert calls[0] == ("obj", [None, None, None, None], ["a", "b"],
                            True, True,
                            ["x", "y"], 1)

        class FakeArgErr(ArgErr):

            def getmsg(self, fname):
                return "msg "+fname

        def _match_signature(*args):
            raise FakeArgErr()
        args._match_signature = _match_signature


        excinfo = py.test.raises(OperationError, args.parse_obj, "obj", "foo",
                       Signature(["a", "b"], None, None))
        assert excinfo.value.w_type is TypeError
        assert excinfo.value._w_value == "msg foo"


    def test_args_parsing_into_scope(self):
        space = DummySpace()
        args = Arguments(space, [])

        calls = []

        def _match_signature(w_firstarg, scope_w, signature,
                             defaults_w=None, blindargs=0):
            defaults_w = [] if defaults_w is None else defaults_w
            calls.append((w_firstarg, scope_w, signature.argnames, signature.has_vararg(),
                          signature.has_kwarg(), defaults_w, blindargs))
        args._match_signature = _match_signature

        scope_w = [None, None]
        args.parse_into_scope(None, scope_w, "foo", Signature(["a", "b"], None, None))
        assert len(calls) == 1
        assert calls[0] == (None, scope_w, ["a", "b"], False, False,
                            [], 0)
        assert calls[0][1] is scope_w
        calls = []

        scope_w = [None, None, None, None]
        args.parse_into_scope(None, scope_w, "foo", Signature(["a", "b"], "args", "kw"),
                              defaults_w=['x', 'y'])
        assert len(calls) == 1
        assert calls[0] == (None, scope_w, ["a", "b"],
                            True, True,
                            ["x", "y"], 0)
        calls = []

        scope_w = [None, None, None, None]
        args.parse_into_scope("obj", scope_w, "foo", Signature(["a", "b"],
                                                      "args", "kw"),
                              defaults_w=['x', 'y'])
        assert len(calls) == 1
        assert calls[0] == ("obj", scope_w, ["a", "b"],
                            True, True,
                            ["x", "y"], 0)

        class FakeArgErr(ArgErr):

            def getmsg(self, fname):
                return "msg "+fname

        def _match_signature(*args):
            raise FakeArgErr()
        args._match_signature = _match_signature


        excinfo = py.test.raises(OperationError, args.parse_into_scope,
                                 "obj", [None, None], "foo",
                                 Signature(["a", "b"], None, None))
        assert excinfo.value.w_type is TypeError
        assert excinfo.value._w_value == "msg foo"

    def test_topacked_frompacked(self):
        space = DummySpace()
        args = Arguments(space, [1], ['a', 'b'], [2, 3])
        w_args, w_kwds = args.topacked()
        assert w_args == (1,)
        assert w_kwds == {'a': 2, 'b': 3}
        args1 = Arguments.frompacked(space, w_args, w_kwds)
        assert args.arguments_w == [1]
        assert set(args.keywords) == set(['a', 'b'])
        assert args.keywords_w[args.keywords.index('a')] == 2
        assert args.keywords_w[args.keywords.index('b')] == 3

        args = Arguments(space, [1])
        w_args, w_kwds = args.topacked()
        assert w_args == (1, )
        assert not w_kwds

    def test_argument_unicode(self):
        space = DummySpace()
        w_starstar = space.wrap({u'abc': 5})
        args = Arguments(space, [], w_starstararg=w_starstar)
        l = [None]
        args._match_signature(None, l, Signature(['abc']))
        assert len(l) == 1
        assert l[0] == space.wrap(5)

class TestErrorHandling(object):
    def test_missing_args(self):
        # got_nargs, nkwds, expected_nargs, has_vararg, has_kwarg,
        # defaults_w, missing_args
        err = ArgErrCount(1, 0, 0, False, False, None, 0)
        s = err.getmsg('foo')
        assert s == "foo() takes no arguments (1 given)"
        err = ArgErrCount(0, 0, 1, False, False, [], 1)
        s = err.getmsg('foo')
        assert s == "foo() takes exactly 1 argument (0 given)"
        err = ArgErrCount(3, 0, 2, False, False, [], 0)
        s = err.getmsg('foo')
        assert s == "foo() takes exactly 2 arguments (3 given)"
        err = ArgErrCount(3, 0, 2, False, False, ['a'], 0)
        s = err.getmsg('foo')
        assert s == "foo() takes at most 2 arguments (3 given)"
        err = ArgErrCount(1, 0, 2, True, False, [], 1)
        s = err.getmsg('foo')
        assert s == "foo() takes at least 2 arguments (1 given)"
        err = ArgErrCount(0, 1, 2, True, False, ['a'], 1)
        s = err.getmsg('foo')
        assert s == "foo() takes at least 1 non-keyword argument (0 given)"
        err = ArgErrCount(2, 1, 1, False, True, [], 0)
        s = err.getmsg('foo')
        assert s == "foo() takes exactly 1 non-keyword argument (2 given)"
        err = ArgErrCount(0, 1, 1, False, True, [], 1)
        s = err.getmsg('foo')
        assert s == "foo() takes exactly 1 non-keyword argument (0 given)"
        err = ArgErrCount(0, 1, 1, True, True, [], 1)
        s = err.getmsg('foo')
        assert s == "foo() takes at least 1 non-keyword argument (0 given)"
        err = ArgErrCount(2, 1, 1, False, True, ['a'], 0)
        s = err.getmsg('foo')
        assert s == "foo() takes at most 1 non-keyword argument (2 given)"

    def test_bad_type_for_star(self):
        space = self.space
        try:
            Arguments(space, [], w_stararg=space.wrap(42))
        except OperationError, e:
            msg = space.str_w(space.str(e.get_w_value(space)))
            assert msg == "argument after * must be a sequence, not int"
        else:
            assert 0, "did not raise"
        try:
            Arguments(space, [], w_starstararg=space.wrap(42))
        except OperationError, e:
            msg = space.str_w(space.str(e.get_w_value(space)))
            assert msg == "argument after ** must be a mapping, not int"
        else:
            assert 0, "did not raise"

    def test_unknown_keywords(self):
        space = DummySpace()
        err = ArgErrUnknownKwds(space, 1, ['a', 'b'], [True, False], None)
        s = err.getmsg('foo')
        assert s == "foo() got an unexpected keyword argument 'b'"
        err = ArgErrUnknownKwds(space, 2, ['a', 'b', 'c'],
                                [True, False, False], None)
        s = err.getmsg('foo')
        assert s == "foo() got 2 unexpected keyword arguments"

    def test_unknown_unicode_keyword(self):
        class DummySpaceUnicode(DummySpace):
            class sys:
                defaultencoding = 'utf-8'
        space = DummySpaceUnicode()
        err = ArgErrUnknownKwds(space, 1, ['a', None, 'b', 'c'],
                                [True, False, True, True],
                                [unichr(0x1234), u'b', u'c'])
        s = err.getmsg('foo')
        assert s == "foo() got an unexpected keyword argument '\xe1\x88\xb4'"

    def test_multiple_values(self):
        err = ArgErrMultipleValues('bla')
        s = err.getmsg('foo')
        assert s == "foo() got multiple values for keyword argument 'bla'"

class AppTestArgument:
    def test_error_message(self):
        exc = raises(TypeError, (lambda a, b=2: 0), b=3)
        assert exc.value.message == "<lambda>() takes at least 1 non-keyword argument (0 given)"
        exc = raises(TypeError, (lambda: 0), b=3)
        assert exc.value.message == "<lambda>() takes no arguments (1 given)"
        exc = raises(TypeError, (lambda a, b: 0), 1, 2, 3, a=1)
        assert exc.value.message == "<lambda>() takes exactly 2 arguments (4 given)"
        exc = raises(TypeError, (lambda a, b=1: 0), 1, 2, 3, a=1)
        assert exc.value.message == "<lambda>() takes at most 2 non-keyword arguments (3 given)"
        exc = raises(TypeError, (lambda a, b=1, **kw: 0), 1, 2, 3)
        assert exc.value.message == "<lambda>() takes at most 2 non-keyword arguments (3 given)"
        exc = raises(TypeError, (lambda a, b, c=3, **kw: 0), 1)
        assert exc.value.message == "<lambda>() takes at least 2 arguments (1 given)"
        exc = raises(TypeError, (lambda a, b, **kw: 0), 1)
        assert exc.value.message == "<lambda>() takes exactly 2 non-keyword arguments (1 given)"
        exc = raises(TypeError, (lambda a, b, c=3, **kw: 0), a=1)
        assert exc.value.message == "<lambda>() takes at least 2 non-keyword arguments (0 given)"
        exc = raises(TypeError, (lambda a, b, **kw: 0), a=1)
        assert exc.value.message == "<lambda>() takes exactly 2 non-keyword arguments (0 given)"

    def test_unicode_keywords(self):
        def f(**kwargs):
            assert kwargs[u"美"] == 42
        f(**{u"美" : 42})
        def f(x): pass
        e = raises(TypeError, "f(**{u'ü' : 19})")
        assert "?" in str(e.value)

def make_arguments_for_translation(space, args_w, keywords_w={},
                                   w_stararg=None, w_starstararg=None):
    return ArgumentsForTranslation(space, args_w, keywords_w.keys(),
                                   keywords_w.values(), w_stararg,
                                   w_starstararg)

class TestArgumentsForTranslation(object):

    def test_prepend(self):
        space = DummySpace()
        args = ArgumentsForTranslation(space, ["0"])
        args1 = args.prepend("thingy")
        assert args1 is not args
        assert args1.arguments_w == ["thingy", "0"]
        assert args1.keywords is args.keywords
        assert args1.keywords_w is args.keywords_w

    def test_unmatch_signature(self):
        space = DummySpace()
        args = make_arguments_for_translation(space, [1,2,3])
        sig = Signature(['a', 'b', 'c'], None, None)
        data = args.match_signature(sig, [])
        new_args = args.unmatch_signature(sig, data)
        assert args.unpack() == new_args.unpack()

        args = make_arguments_for_translation(space, [1])
        sig = Signature(['a', 'b', 'c'], None, None)
        data = args.match_signature(sig, [2, 3])
        new_args = args.unmatch_signature(sig, data)
        assert args.unpack() == new_args.unpack()

        args = make_arguments_for_translation(space, [1,2,3,4,5])
        sig = Signature(['a', 'b', 'c'], 'r', None)
        data = args.match_signature(sig, [])
        new_args = args.unmatch_signature(sig, data)
        assert args.unpack() == new_args.unpack()

        args = make_arguments_for_translation(space, [1], {'c': 3, 'b': 2})
        sig = Signature(['a', 'b', 'c'], None, None)
        data = args.match_signature(sig, [])
        new_args = args.unmatch_signature(sig, data)
        assert args.unpack() == new_args.unpack()

        args = make_arguments_for_translation(space, [1], {'c': 5})
        sig = Signature(['a', 'b', 'c'], None, None)
        data = args.match_signature(sig, [2, 3])
        new_args = args.unmatch_signature(sig, data)
        assert args.unpack() == new_args.unpack()

        args = make_arguments_for_translation(space, [1], {'c': 5, 'd': 7})
        sig = Signature(['a', 'b', 'c'], None, 'kw')
        data = args.match_signature(sig, [2, 3])
        new_args = args.unmatch_signature(sig, data)
        assert args.unpack() == new_args.unpack()

        args = make_arguments_for_translation(space, [1,2,3,4,5], {'e': 5, 'd': 7})
        sig = Signature(['a', 'b', 'c'], 'r', 'kw')
        data = args.match_signature(sig, [2, 3])
        new_args = args.unmatch_signature(sig, data)
        assert args.unpack() == new_args.unpack()

        args = make_arguments_for_translation(space, [], {},
                                       w_stararg=[1],
                                       w_starstararg={'c': 5, 'd': 7})
        sig = Signature(['a', 'b', 'c'], None, 'kw')
        data = args.match_signature(sig, [2, 3])
        new_args = args.unmatch_signature(sig, data)
        assert args.unpack() == new_args.unpack()

        args = make_arguments_for_translation(space, [1,2], {'g': 9},
                                       w_stararg=[3,4,5],
                                       w_starstararg={'e': 5, 'd': 7})
        sig = Signature(['a', 'b', 'c'], 'r', 'kw')
        data = args.match_signature(sig, [2, 3])
        new_args = args.unmatch_signature(sig, data)
        assert args.unpack() == new_args.unpack()

    def test_rawshape(self):
        space = DummySpace()
        args = make_arguments_for_translation(space, [1,2,3])
        assert rawshape(args) == (3, (), False, False)

        args = make_arguments_for_translation(space, [1])
        assert rawshape(args, 2) == (3, (), False, False)

        args = make_arguments_for_translation(space, [1,2,3,4,5])
        assert rawshape(args) == (5, (), False, False)

        args = make_arguments_for_translation(space, [1], {'c': 3, 'b': 2})
        assert rawshape(args) == (1, ('b', 'c'), False, False)

        args = make_arguments_for_translation(space, [1], {'c': 5})
        assert rawshape(args) == (1, ('c', ), False, False)

        args = make_arguments_for_translation(space, [1], {'c': 5, 'd': 7})
        assert rawshape(args) == (1, ('c', 'd'), False, False)

        args = make_arguments_for_translation(space, [1,2,3,4,5], {'e': 5, 'd': 7})
        assert rawshape(args) == (5, ('d', 'e'), False, False)

        args = make_arguments_for_translation(space, [], {},
                                       w_stararg=[1],
                                       w_starstararg={'c': 5, 'd': 7})
        assert rawshape(args) == (0, (), True, True)

        args = make_arguments_for_translation(space, [1,2], {'g': 9},
                                       w_stararg=[3,4,5],
                                       w_starstararg={'e': 5, 'd': 7})
        assert rawshape(args) == (2, ('g', ), True, True)

    def test_copy_and_shape(self):
        space = DummySpace()
        args = ArgumentsForTranslation(space, ['a'], ['x'], [1],
                                       ['w1'], {'y': 'w2'})
        args1 = args.copy()
        args.combine_if_necessary()
        assert rawshape(args1) == (1, ('x',), True, True)


    def test_flatten(self):
        space = DummySpace()
        args = make_arguments_for_translation(space, [1,2,3])
        assert args.flatten() == ((3, (), False, False), [1, 2, 3])

        args = make_arguments_for_translation(space, [1])
        assert args.flatten() == ((1, (), False, False), [1])

        args = make_arguments_for_translation(space, [1,2,3,4,5])
        assert args.flatten() == ((5, (), False, False), [1,2,3,4,5])

        args = make_arguments_for_translation(space, [1], {'c': 3, 'b': 2})
        assert args.flatten() == ((1, ('b', 'c'), False, False), [1, 2, 3])

        args = make_arguments_for_translation(space, [1], {'c': 5})
        assert args.flatten() == ((1, ('c', ), False, False), [1, 5])

        args = make_arguments_for_translation(space, [1], {'c': 5, 'd': 7})
        assert args.flatten() == ((1, ('c', 'd'), False, False), [1, 5, 7])

        args = make_arguments_for_translation(space, [1,2,3,4,5], {'e': 5, 'd': 7})
        assert args.flatten() == ((5, ('d', 'e'), False, False), [1, 2, 3, 4, 5, 7, 5])

        args = make_arguments_for_translation(space, [], {},
                                       w_stararg=[1],
                                       w_starstararg={'c': 5, 'd': 7})
        assert args.flatten() == ((0, (), True, True), [[1], {'c': 5, 'd': 7}])

        args = make_arguments_for_translation(space, [1,2], {'g': 9},
                                       w_stararg=[3,4,5],
                                       w_starstararg={'e': 5, 'd': 7})
        assert args.flatten() == ((2, ('g', ), True, True), [1, 2, 9, [3, 4, 5], {'e': 5, 'd': 7}])

    def test_stararg_flowspace_variable(self):
        space = DummySpace()
        var = object()
        shape = ((2, ('g', ), True, False), [1, 2, 9, var])
        args = make_arguments_for_translation(space, [1,2], {'g': 9},
                                       w_stararg=var)
        assert args.flatten() == shape

        args = ArgumentsForTranslation.fromshape(space, *shape)
        assert args.flatten() == shape


    def test_fromshape(self):
        space = DummySpace()
        shape = ((3, (), False, False), [1, 2, 3])
        args = ArgumentsForTranslation.fromshape(space, *shape)
        assert args.flatten() == shape

        shape = ((1, (), False, False), [1])
        args = ArgumentsForTranslation.fromshape(space, *shape)
        assert args.flatten() == shape

        shape = ((5, (), False, False), [1,2,3,4,5])
        args = ArgumentsForTranslation.fromshape(space, *shape)
        assert args.flatten() == shape

        shape = ((1, ('b', 'c'), False, False), [1, 2, 3])
        args = ArgumentsForTranslation.fromshape(space, *shape)
        assert args.flatten() == shape

        shape = ((1, ('c', ), False, False), [1, 5])
        args = ArgumentsForTranslation.fromshape(space, *shape)
        assert args.flatten() == shape

        shape = ((1, ('c', 'd'), False, False), [1, 5, 7])
        args = ArgumentsForTranslation.fromshape(space, *shape)
        assert args.flatten() == shape

        shape = ((5, ('d', 'e'), False, False), [1, 2, 3, 4, 5, 7, 5])
        args = ArgumentsForTranslation.fromshape(space, *shape)
        assert args.flatten() == shape

        shape = ((0, (), True, True), [[1], {'c': 5, 'd': 7}])
        args = ArgumentsForTranslation.fromshape(space, *shape)
        assert args.flatten() == shape

        shape = ((2, ('g', ), True, True), [1, 2, 9, [3, 4, 5], {'e': 5, 'd': 7}])
        args = ArgumentsForTranslation.fromshape(space, *shape)
        assert args.flatten() == shape

