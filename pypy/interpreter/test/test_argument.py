# -*- coding: utf-8 -*-
import py
from pypy.interpreter.argument import (Arguments, ArgErr, ArgErrUnknownKwds,
        ArgErrMultipleValues, ArgErrMissing, ArgErrTooMany)
from pypy.interpreter.signature import Signature
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
        sig = Signature(["a", "b", "c"], "d", "c", ["kwonly"])
        assert sig.num_argnames() == 3
        assert sig.has_vararg()
        assert sig.has_kwarg()
        assert sig.scope_length() == 5
        assert sig.getallvarnames() == ["a", "b", "c", "d", "kwonly", "c"]

    def test_eq(self):
        sig1 = Signature(["a", "b", "c"], "d", "c")
        sig2 = Signature(["a", "b", "c"], "d", "c")
        assert sig1 == sig2


    def test_find_argname(self):
        sig = Signature(["a", "b", "c"], None, None, ["kwonly"])
        assert sig.find_argname("a") == 0
        assert sig.find_argname("b") == 1
        assert sig.find_argname("c") == 2
        assert sig.find_argname("d") == -1
        assert sig.find_argname("kwonly") == 3

class dummy_wrapped_dict(dict):
    def __nonzero__(self):
        raise NotImplementedError

class kwargsdict(dict):
    pass

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

    def view_as_kwargs(self, x):
        if len(x) == 0:
            return [], []
        return None, None

    def newdict(self, kwargs=False):
        if kwargs:
            return kwargsdict()
        return {}

    def newlist(self, l=[]):
        return l

    def setitem(self, obj, key, value):
        obj[key] = value
    setitem_str = setitem

    def getitem(self, obj, key):
        return obj[key]

    def wrap(self, obj):
        return obj

    def str_w(self, s):
        return str(s)

    def unicode_w(self, s):
        return unicode(s)

    def identifier_w(self, s):
        return self.unicode_w(s).encode('utf-8')

    def len(self, x):
        return len(x)

    def int_w(self, x, allow_conversion=True):
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
            def getname(self, space):
                return unicode(type(obj).__name__)
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

    def test_match_kwds_creates_kwdict(self):
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
            assert isinstance(l[-1], kwargsdict)

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
        def unicode_w(w):
            if w is None:
                raise OperationError(TypeError, None)
            if w is valuedummy:
                raise OperationError(ValueError, None)
            return str(w)
        space.unicode_w = unicode_w
        excinfo = py.test.raises(OperationError, Arguments, space, [],
                                 ["a"], [1], w_starstararg={None: 1})
        assert excinfo.value.w_type is TypeError
        assert excinfo.value._w_value is None
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
                             defaults_w=None, w_kw_defs=None, blindargs=0):
            defaults_w = [] if defaults_w is None else defaults_w
            calls.append((w_firstarg, scope_w, signature.argnames, signature.has_vararg(),
                          signature.has_kwarg(), defaults_w, w_kw_defs, blindargs))
        args._match_signature = _match_signature

        scope_w = args.parse_obj(None, "foo", Signature(["a", "b"], None, None))
        assert len(calls) == 1
        assert calls[0] == (None, [None, None], ["a", "b"], False, False,
                            [], None, 0)
        assert calls[0][1] is scope_w
        calls = []

        scope_w = args.parse_obj(None, "foo", Signature(["a", "b"], "args", None),
                                 blindargs=1)
        assert len(calls) == 1
        assert calls[0] == (None, [None, None, None], ["a", "b"], True, False,
                            [], None, 1)
        calls = []

        scope_w = args.parse_obj(None, "foo", Signature(["a", "b"], "args", "kw"),
                             defaults_w=['x', 'y'])
        assert len(calls) == 1
        assert calls[0] == (None, [None, None, None, None], ["a", "b"],
                            True, True,
                            ["x", "y"], None, 0)
        calls = []

        scope_w = args.parse_obj("obj", "foo", Signature(["a", "b"], "args", "kw"),
                             defaults_w=['x', 'y'], blindargs=1)
        assert len(calls) == 1
        assert calls[0] == ("obj", [None, None, None, None], ["a", "b"],
                            True, True,
                            ["x", "y"], None, 1)

        class FakeArgErr(ArgErr):

            def getmsg(self):
                return "msg"

        def _match_signature(*args):
            raise FakeArgErr()
        args._match_signature = _match_signature


        excinfo = py.test.raises(OperationError, args.parse_obj, "obj", "foo",
                       Signature(["a", "b"], None, None))
        assert excinfo.value.w_type is TypeError
        assert excinfo.value.get_w_value(space) == "foo() msg"


    def test_args_parsing_into_scope(self):
        space = DummySpace()
        args = Arguments(space, [])

        calls = []

        def _match_signature(w_firstarg, scope_w, signature,
                             defaults_w=None, w_kw_defs=None, blindargs=0):
            defaults_w = [] if defaults_w is None else defaults_w
            calls.append((w_firstarg, scope_w, signature.argnames, signature.has_vararg(),
                          signature.has_kwarg(), defaults_w, w_kw_defs, blindargs))
        args._match_signature = _match_signature

        scope_w = [None, None]
        args.parse_into_scope(None, scope_w, "foo", Signature(["a", "b"], None, None))
        assert len(calls) == 1
        assert calls[0] == (None, scope_w, ["a", "b"], False, False,
                            [], None, 0)
        assert calls[0][1] is scope_w
        calls = []

        scope_w = [None, None, None, None]
        args.parse_into_scope(None, scope_w, "foo", Signature(["a", "b"], "args", "kw"),
                              defaults_w=['x', 'y'])
        assert len(calls) == 1
        assert calls[0] == (None, scope_w, ["a", "b"],
                            True, True,
                            ["x", "y"], None, 0)
        calls = []

        scope_w = [None, None, None, None]
        args.parse_into_scope("obj", scope_w, "foo", Signature(["a", "b"],
                                                      "args", "kw"),
                              defaults_w=['x', 'y'])
        assert len(calls) == 1
        assert calls[0] == ("obj", scope_w, ["a", "b"],
                            True, True,
                            ["x", "y"], None, 0)

        class FakeArgErr(ArgErr):

            def getmsg(self):
                return "msg"

        def _match_signature(*args):
            raise FakeArgErr()
        args._match_signature = _match_signature


        excinfo = py.test.raises(OperationError, args.parse_into_scope,
                                 "obj", [None, None], "foo",
                                 Signature(["a", "b"], None, None))
        assert excinfo.value.w_type is TypeError
        assert excinfo.value.get_w_value(space) == "foo() msg"

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

    def test_starstarargs_special(self):
        class kwargs(object):
            def __init__(self, k, v):
                self.k = k
                self.v = v
        class MyDummySpace(DummySpace):
            def view_as_kwargs(self, kw):
                if isinstance(kw, kwargs):
                    return kw.k, kw.v
                return None, None
        space = MyDummySpace()
        for i in range(3):
            kwds = [("c", 3)]
            kwds_w = dict(kwds[:i])
            keywords = kwds_w.keys()
            keywords_w = kwds_w.values()
            rest = dict(kwds[i:])
            w_kwds = kwargs(rest.keys(), rest.values())
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
        excinfo = py.test.raises(OperationError, Arguments, space, [], ["a"],
                                 [1], w_starstararg=kwargs(["a"], [2]))
        assert excinfo.value.w_type is TypeError



class TestErrorHandling(object):
    def test_missing_args(self):
        err = ArgErrMissing(['a'], True)
        s = err.getmsg()
        assert s == "missing 1 required positional argument: 'a'"

        err = ArgErrMissing(['a', 'b'], True)
        s = err.getmsg()
        assert s == "missing 2 required positional arguments: 'a' and 'b'"

        err = ArgErrMissing(['a', 'b', 'c'], True)
        s = err.getmsg()
        assert s == "missing 3 required positional arguments: 'a', 'b', and 'c'"

        err = ArgErrMissing(['a'], False)
        s = err.getmsg()
        assert s == "missing 1 required keyword-only argument: 'a'"

    def test_too_many(self):
        err = ArgErrTooMany(0, 0, 1, 0)
        s = err.getmsg()
        assert s == "takes 0 positional arguments but 1 was given"

        err = ArgErrTooMany(0, 0, 2, 0)
        s = err.getmsg()
        assert s == "takes 0 positional arguments but 2 were given"

        err = ArgErrTooMany(1, 0, 2, 0)
        s = err.getmsg()
        assert s == "takes 1 positional argument but 2 were given"

        err = ArgErrTooMany(2, 0, 3, 0)
        s = err.getmsg()
        assert s == "takes 2 positional arguments but 3 were given"

        err = ArgErrTooMany(2, 1, 3, 0)
        s = err.getmsg()
        assert s == "takes from 1 to 2 positional arguments but 3 were given"

        err = ArgErrTooMany(0, 0, 1, 1)
        s = err.getmsg()
        assert s == "takes 0 positional arguments but 1 positional argument (and 1 keyword-only argument) were given"

        err = ArgErrTooMany(0, 0, 2, 1)
        s = err.getmsg()
        assert s == "takes 0 positional arguments but 2 positional arguments (and 1 keyword-only argument) were given"

        err = ArgErrTooMany(0, 0, 1, 2)
        s = err.getmsg()
        assert s == "takes 0 positional arguments but 1 positional argument (and 2 keyword-only arguments) were given"

    def test_bad_type_for_star(self):
        space = self.space
        try:
            Arguments(space, [], w_stararg=space.wrap(42))
        except OperationError as e:
            msg = space.str_w(space.str(e.get_w_value(space)))
            assert msg == "argument after * must be a sequence, not int"
        else:
            assert 0, "did not raise"
        try:
            Arguments(space, [], w_starstararg=space.wrap(42))
        except OperationError as e:
            msg = space.str_w(space.str(e.get_w_value(space)))
            assert msg == "argument after ** must be a mapping, not int"
        else:
            assert 0, "did not raise"

    def test_unknown_keywords(self):
        space = DummySpace()
        err = ArgErrUnknownKwds(space, 1, ['a', 'b'], [0], None)
        s = err.getmsg()
        assert s == "got an unexpected keyword argument 'b'"
        err = ArgErrUnknownKwds(space, 1, ['a', 'b'], [1], None)
        s = err.getmsg()
        assert s == "got an unexpected keyword argument 'a'"
        err = ArgErrUnknownKwds(space, 2, ['a', 'b', 'c'],
                                [0], None)
        s = err.getmsg()
        assert s == "got 2 unexpected keyword arguments"

    def test_unknown_unicode_keyword(self):
        class DummySpaceUnicode(DummySpace):
            class sys:
                defaultencoding = 'utf-8'
        space = DummySpaceUnicode()
        err = ArgErrUnknownKwds(space, 1, ['a', None, 'b', 'c'],
                                [0, 3, 2],
                                [unichr(0x1234), u'b', u'c'])
        s = err.getmsg()
        assert s == "got an unexpected keyword argument '%s'" % unichr(0x1234).encode('utf-8')

    def test_multiple_values(self):
        err = ArgErrMultipleValues('bla')
        s = err.getmsg()
        assert s == "got multiple values for argument 'bla'"

class AppTestArgument:
    def test_error_message(self):
        exc = raises(TypeError, (lambda a, b=2: 0), b=3)
        assert str(exc.value) == "<lambda>() missing 1 required positional argument: 'a'"
        exc = raises(TypeError, (lambda: 0), b=3)
        assert str(exc.value) == "<lambda>() got an unexpected keyword argument 'b'"
        exc = raises(TypeError, (lambda a, b: 0), 1, 2, 3, a=1)
        assert str(exc.value) == "<lambda>() got multiple values for argument 'a'"
        exc = raises(TypeError, (lambda a, b=1: 0), 1, 2, 3, a=1)
        assert str(exc.value) == "<lambda>() got multiple values for argument 'a'"
        exc = raises(TypeError, (lambda a, **kw: 0), 1, 2, 3)
        assert str(exc.value) == "<lambda>() takes 1 positional argument but 3 were given"
        exc = raises(TypeError, (lambda a, b=1, **kw: 0), 1, 2, 3)
        assert str(exc.value) == "<lambda>() takes from 1 to 2 positional arguments but 3 were given"
        exc = raises(TypeError, (lambda a, b, c=3, **kw: 0), 1)
        assert str(exc.value) == "<lambda>() missing 1 required positional argument: 'b'"
        exc = raises(TypeError, (lambda a, b, **kw: 0), 1)
        assert str(exc.value) == "<lambda>() missing 1 required positional argument: 'b'"
        exc = raises(TypeError, (lambda a, b, c=3, **kw: 0), a=1)
        assert str(exc.value) == "<lambda>() missing 1 required positional argument: 'b'"
        exc = raises(TypeError, (lambda a, b, **kw: 0), a=1)
        assert str(exc.value) == "<lambda>() missing 1 required positional argument: 'b'"
        exc = raises(TypeError, '(lambda *, a: 0)()')
        assert str(exc.value) == "<lambda>() missing 1 required keyword-only argument: 'a'"
        exc = raises(TypeError, '(lambda *, a=1, b: 0)(a=1)')
        assert str(exc.value) == "<lambda>() missing 1 required keyword-only argument: 'b'"
        exc = raises(TypeError, '(lambda *, kw: 0)(1, kw=3)')
        assert str(exc.value) == "<lambda>() takes 0 positional arguments but 1 positional argument (and 1 keyword-only argument) were given"

    def test_unicode_keywords(self):
        """
        def f(**kwargs):
            assert kwargs["美"] == 42
        f(**{"美" : 42})
        #
        def f(x): pass
        e = raises(TypeError, "f(**{'ü' : 19})")
        assert e.value.args[0] == "f() got an unexpected keyword argument 'ü'"
        """

    def test_starstarargs_dict_subclass(self):
        def f(**kwargs):
            return kwargs
        class DictSubclass(dict):
            def __iter__(self):
                yield 'x'
        # CPython, as an optimization, looks directly into dict internals when
        # passing one via **kwargs.
        x =DictSubclass()
        assert f(**x) == {}
        x['a'] = 1
        assert f(**x) == {'a': 1}

    def test_starstarargs_module_dict(self):
        def f(**kwargs):
            return kwargs
        assert f(**globals()) == globals()
