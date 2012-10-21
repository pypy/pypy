# -*- coding: utf-8 -*-
import py
from pypy.objspace.flow.argument import (ArgumentsForTranslation, rawshape,
    Signature)


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
        method = getattr(obj, name)
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

    def test_fixedunpacked(self):
        space = DummySpace()

        args = ArgumentsForTranslation(space, [], ["k"], [1])
        py.test.raises(ValueError, args.fixedunpack, 1)

        args = ArgumentsForTranslation(space, ["a", "b"])
        py.test.raises(ValueError, args.fixedunpack, 0)
        py.test.raises(ValueError, args.fixedunpack, 1)
        py.test.raises(ValueError, args.fixedunpack, 3)
        py.test.raises(ValueError, args.fixedunpack, 4)

        assert args.fixedunpack(2) == ['a', 'b']

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

