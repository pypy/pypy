# -*- coding: utf-8 -*-
import py
from rpython.annotator.argument import ArgumentsForTranslation, rawshape
from rpython.flowspace.argument import Signature

class MockArgs(ArgumentsForTranslation):
    def newtuple(self, items):
        return tuple(items)

    def unpackiterable(self, it):
        return list(it)


def make_arguments_for_translation(args_w, keywords_w={}, w_stararg=None,
                                   w_starstararg=None):
    return MockArgs(args_w, keywords_w.keys(), keywords_w.values(),
                    w_stararg, w_starstararg)

class TestArgumentsForTranslation(object):

    def test_prepend(self):
        args = MockArgs(["0"])
        args1 = args.prepend("thingy")
        assert args1 is not args
        assert args1.arguments_w == ["thingy", "0"]
        assert args1.keywords is args.keywords
        assert args1.keywords_w is args.keywords_w

    def test_fixedunpacked(self):
        args = MockArgs([], ["k"], [1])
        py.test.raises(ValueError, args.fixedunpack, 1)

        args = MockArgs(["a", "b"])
        py.test.raises(ValueError, args.fixedunpack, 0)
        py.test.raises(ValueError, args.fixedunpack, 1)
        py.test.raises(ValueError, args.fixedunpack, 3)
        py.test.raises(ValueError, args.fixedunpack, 4)

        assert args.fixedunpack(2) == ['a', 'b']

    def test_unmatch_signature(self):
        args = make_arguments_for_translation([1, 2, 3])
        sig = Signature(['a', 'b', 'c'], None, None)
        data = args.match_signature(sig, [])
        new_args = args.unmatch_signature(sig, data)
        assert args.unpack() == new_args.unpack()

        args = make_arguments_for_translation([1])
        sig = Signature(['a', 'b', 'c'], None, None)
        data = args.match_signature(sig, [2, 3])
        new_args = args.unmatch_signature(sig, data)
        assert args.unpack() == new_args.unpack()

        args = make_arguments_for_translation([1, 2, 3, 4, 5])
        sig = Signature(['a', 'b', 'c'], 'r', None)
        data = args.match_signature(sig, [])
        new_args = args.unmatch_signature(sig, data)
        assert args.unpack() == new_args.unpack()

        args = make_arguments_for_translation([1], {'c': 3, 'b': 2})
        sig = Signature(['a', 'b', 'c'], None, None)
        data = args.match_signature(sig, [])
        new_args = args.unmatch_signature(sig, data)
        assert args.unpack() == new_args.unpack()

        args = make_arguments_for_translation([1], {'c': 5})
        sig = Signature(['a', 'b', 'c'], None, None)
        data = args.match_signature(sig, [2, 3])
        new_args = args.unmatch_signature(sig, data)
        assert args.unpack() == new_args.unpack()

    def test_rawshape(self):
        args = make_arguments_for_translation([1, 2, 3])
        assert rawshape(args) == (3, (), False, False)

        args = make_arguments_for_translation([1])
        assert rawshape(args, 2) == (3, (), False, False)

        args = make_arguments_for_translation([1, 2, 3, 4, 5])
        assert rawshape(args) == (5, (), False, False)

        args = make_arguments_for_translation([1], {'c': 3, 'b': 2})
        assert rawshape(args) == (1, ('b', 'c'), False, False)

        args = make_arguments_for_translation([1], {'c': 5})
        assert rawshape(args) == (1, ('c', ), False, False)

        args = make_arguments_for_translation([1], {'c': 5, 'd': 7})
        assert rawshape(args) == (1, ('c', 'd'), False, False)

        args = make_arguments_for_translation([1, 2, 3, 4, 5], {'e': 5, 'd': 7})
        assert rawshape(args) == (5, ('d', 'e'), False, False)

    def test_flatten(self):
        args = make_arguments_for_translation([1, 2, 3])
        assert args.flatten() == ((3, (), False, False), [1, 2, 3])

        args = make_arguments_for_translation([1])
        assert args.flatten() == ((1, (), False, False), [1])

        args = make_arguments_for_translation([1, 2, 3, 4, 5])
        assert args.flatten() == ((5, (), False, False), [1, 2, 3, 4, 5])

        args = make_arguments_for_translation([1], {'c': 3, 'b': 2})
        assert args.flatten() == ((1, ('b', 'c'), False, False), [1, 2, 3])

        args = make_arguments_for_translation([1], {'c': 5})
        assert args.flatten() == ((1, ('c', ), False, False), [1, 5])

        args = make_arguments_for_translation([1], {'c': 5, 'd': 7})
        assert args.flatten() == ((1, ('c', 'd'), False, False), [1, 5, 7])

        args = make_arguments_for_translation([1, 2, 3, 4, 5], {'e': 5, 'd': 7})
        assert args.flatten() == ((5, ('d', 'e'), False, False), [1, 2, 3, 4, 5, 7, 5])

    def test_stararg_flowspace_variable(self):
        var = object()
        shape = ((2, ('g', ), True, False), [1, 2, 9, var])
        args = make_arguments_for_translation([1, 2], {'g': 9},
                                       w_stararg=var)
        assert args.flatten() == shape

        args = MockArgs.fromshape(*shape)
        assert args.flatten() == shape

    def test_fromshape(self):
        shape = ((3, (), False, False), [1, 2, 3])
        args = MockArgs.fromshape(*shape)
        assert args.flatten() == shape

        shape = ((1, (), False, False), [1])
        args = MockArgs.fromshape(*shape)
        assert args.flatten() == shape

        shape = ((5, (), False, False), [1, 2, 3, 4, 5])
        args = MockArgs.fromshape(*shape)
        assert args.flatten() == shape

        shape = ((1, ('b', 'c'), False, False), [1, 2, 3])
        args = MockArgs.fromshape(*shape)
        assert args.flatten() == shape

        shape = ((1, ('c', ), False, False), [1, 5])
        args = MockArgs.fromshape(*shape)
        assert args.flatten() == shape

        shape = ((1, ('c', 'd'), False, False), [1, 5, 7])
        args = MockArgs.fromshape(*shape)
        assert args.flatten() == shape

        shape = ((5, ('d', 'e'), False, False), [1, 2, 3, 4, 5, 7, 5])
        args = MockArgs.fromshape(*shape)
        assert args.flatten() == shape
