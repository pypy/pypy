#!/usr/bin/env python
# -*- coding: utf-8 -*-

from __future__ import absolute_import
from __future__ import division
from __future__ import print_function
from __future__ import unicode_literals

import collections
import decimal
from itertools import permutations
import singledispatch as functools
from singledispatch_helpers import Support
try:
    from collections import ChainMap
except ImportError:
    from singledispatch_helpers import ChainMap
    collections.ChainMap = ChainMap
try:
    from collections import OrderedDict
except ImportError:
    from singledispatch_helpers import OrderedDict
    collections.OrderedDict = OrderedDict
try:
    import unittest2 as unittest
except ImportError:
    import unittest


support = Support()
for _prefix in ('collections.abc', '_abcoll'):
    if _prefix in repr(collections.Container):
        abcoll_prefix = _prefix
        break
else:
    abcoll_prefix = '?'
del _prefix


class TestSingleDispatch(unittest.TestCase):
    def test_simple_overloads(self):
        @functools.singledispatch
        def g(obj):
            return "base"
        def g_int(i):
            return "integer"
        g.register(int, g_int)
        self.assertEqual(g("str"), "base")
        self.assertEqual(g(1), "integer")
        self.assertEqual(g([1,2,3]), "base")

    def test_mro(self):
        @functools.singledispatch
        def g(obj):
            return "base"
        class A(object):
            pass
        class C(A):
            pass
        class B(A):
            pass
        class D(C, B):
            pass
        def g_A(a):
            return "A"
        def g_B(b):
            return "B"
        g.register(A, g_A)
        g.register(B, g_B)
        self.assertEqual(g(A()), "A")
        self.assertEqual(g(B()), "B")
        self.assertEqual(g(C()), "A")
        self.assertEqual(g(D()), "B")

    def test_register_decorator(self):
        @functools.singledispatch
        def g(obj):
            return "base"
        @g.register(int)
        def g_int(i):
            return "int %s" % (i,)
        self.assertEqual(g(""), "base")
        self.assertEqual(g(12), "int 12")
        self.assertIs(g.dispatch(int), g_int)
        self.assertIs(g.dispatch(object), g.dispatch(str))
        # Note: in the assert above this is not g.
        # @singledispatch returns the wrapper.

    def test_wrapping_attributes(self):
        @functools.singledispatch
        def g(obj):
            "Simple test"
            return "Test"
        self.assertEqual(g.__name__, "g")
        self.assertEqual(g.__doc__, "Simple test")

    @unittest.skipUnless(decimal, 'requires _decimal')
    @support.cpython_only
    def test_c_classes(self):
        @functools.singledispatch
        def g(obj):
            return "base"
        @g.register(decimal.DecimalException)
        def _(obj):
            return obj.args
        subn = decimal.Subnormal("Exponent < Emin")
        rnd = decimal.Rounded("Number got rounded")
        self.assertEqual(g(subn), ("Exponent < Emin",))
        self.assertEqual(g(rnd), ("Number got rounded",))
        @g.register(decimal.Subnormal)
        def _(obj):
            return "Too small to care."
        self.assertEqual(g(subn), "Too small to care.")
        self.assertEqual(g(rnd), ("Number got rounded",))

    def test_compose_mro(self):
        # None of the examples in this test depend on haystack ordering.
        c = collections
        mro = functools._compose_mro
        bases = [c.Sequence, c.MutableMapping, c.Mapping, c.Set]
        for haystack in permutations(bases):
            m = mro(dict, haystack)
            self.assertEqual(m, [dict, c.MutableMapping, c.Mapping, c.Sized,
                                 c.Iterable, c.Container, object])
        bases = [c.Container, c.Mapping, c.MutableMapping, c.OrderedDict]
        for haystack in permutations(bases):
            m = mro(c.ChainMap, haystack)
            self.assertEqual(m, [c.ChainMap, c.MutableMapping, c.Mapping,
                                 c.Sized, c.Iterable, c.Container, object])

        # If there's a generic function with implementations registered for
        # both Sized and Container, passing a defaultdict to it results in an
        # ambiguous dispatch which will cause a RuntimeError (see
        # test_mro_conflicts).
        bases = [c.Container, c.Sized, str]
        for haystack in permutations(bases):
            m = mro(c.defaultdict, [c.Sized, c.Container, str])
            self.assertEqual(m, [c.defaultdict, dict, c.Sized, c.Container,
                                 object])

        # MutableSequence below is registered directly on D. In other words, it
        # preceeds MutableMapping which means single dispatch will always
        # choose MutableSequence here.
        class D(c.defaultdict):
            pass
        c.MutableSequence.register(D)
        bases = [c.MutableSequence, c.MutableMapping]
        for haystack in permutations(bases):
            m = mro(D, bases)
            self.assertEqual(m, [D, c.MutableSequence, c.Sequence,
                                 c.defaultdict, dict, c.MutableMapping,
                                 c.Mapping, c.Sized, c.Iterable, c.Container,
                                 object])

        # Container and Callable are registered on different base classes and
        # a generic function supporting both should always pick the Callable
        # implementation if a C instance is passed.
        class C(c.defaultdict):
            def __call__(self):
                pass
        bases = [c.Sized, c.Callable, c.Container, c.Mapping]
        for haystack in permutations(bases):
            m = mro(C, haystack)
            self.assertEqual(m, [C, c.Callable, c.defaultdict, dict, c.Mapping,
                                 c.Sized, c.Iterable, c.Container, object])

    def test_register_abc(self):
        c = collections
        d = {"a": "b"}
        l = [1, 2, 3]
        s = set([object(), None])
        f = frozenset(s)
        t = (1, 2, 3)
        @functools.singledispatch
        def g(obj):
            return "base"
        self.assertEqual(g(d), "base")
        self.assertEqual(g(l), "base")
        self.assertEqual(g(s), "base")
        self.assertEqual(g(f), "base")
        self.assertEqual(g(t), "base")
        g.register(c.Sized, lambda obj: "sized")
        self.assertEqual(g(d), "sized")
        self.assertEqual(g(l), "sized")
        self.assertEqual(g(s), "sized")
        self.assertEqual(g(f), "sized")
        self.assertEqual(g(t), "sized")
        g.register(c.MutableMapping, lambda obj: "mutablemapping")
        self.assertEqual(g(d), "mutablemapping")
        self.assertEqual(g(l), "sized")
        self.assertEqual(g(s), "sized")
        self.assertEqual(g(f), "sized")
        self.assertEqual(g(t), "sized")
        g.register(c.ChainMap, lambda obj: "chainmap")
        self.assertEqual(g(d), "mutablemapping")  # irrelevant ABCs registered
        self.assertEqual(g(l), "sized")
        self.assertEqual(g(s), "sized")
        self.assertEqual(g(f), "sized")
        self.assertEqual(g(t), "sized")
        g.register(c.MutableSequence, lambda obj: "mutablesequence")
        self.assertEqual(g(d), "mutablemapping")
        self.assertEqual(g(l), "mutablesequence")
        self.assertEqual(g(s), "sized")
        self.assertEqual(g(f), "sized")
        self.assertEqual(g(t), "sized")
        g.register(c.MutableSet, lambda obj: "mutableset")
        self.assertEqual(g(d), "mutablemapping")
        self.assertEqual(g(l), "mutablesequence")
        self.assertEqual(g(s), "mutableset")
        self.assertEqual(g(f), "sized")
        self.assertEqual(g(t), "sized")
        g.register(c.Mapping, lambda obj: "mapping")
        self.assertEqual(g(d), "mutablemapping")  # not specific enough
        self.assertEqual(g(l), "mutablesequence")
        self.assertEqual(g(s), "mutableset")
        self.assertEqual(g(f), "sized")
        self.assertEqual(g(t), "sized")
        g.register(c.Sequence, lambda obj: "sequence")
        self.assertEqual(g(d), "mutablemapping")
        self.assertEqual(g(l), "mutablesequence")
        self.assertEqual(g(s), "mutableset")
        self.assertEqual(g(f), "sized")
        self.assertEqual(g(t), "sequence")
        g.register(c.Set, lambda obj: "set")
        self.assertEqual(g(d), "mutablemapping")
        self.assertEqual(g(l), "mutablesequence")
        self.assertEqual(g(s), "mutableset")
        self.assertEqual(g(f), "set")
        self.assertEqual(g(t), "sequence")
        g.register(dict, lambda obj: "dict")
        self.assertEqual(g(d), "dict")
        self.assertEqual(g(l), "mutablesequence")
        self.assertEqual(g(s), "mutableset")
        self.assertEqual(g(f), "set")
        self.assertEqual(g(t), "sequence")
        g.register(list, lambda obj: "list")
        self.assertEqual(g(d), "dict")
        self.assertEqual(g(l), "list")
        self.assertEqual(g(s), "mutableset")
        self.assertEqual(g(f), "set")
        self.assertEqual(g(t), "sequence")
        g.register(set, lambda obj: "concrete-set")
        self.assertEqual(g(d), "dict")
        self.assertEqual(g(l), "list")
        self.assertEqual(g(s), "concrete-set")
        self.assertEqual(g(f), "set")
        self.assertEqual(g(t), "sequence")
        g.register(frozenset, lambda obj: "frozen-set")
        self.assertEqual(g(d), "dict")
        self.assertEqual(g(l), "list")
        self.assertEqual(g(s), "concrete-set")
        self.assertEqual(g(f), "frozen-set")
        self.assertEqual(g(t), "sequence")
        g.register(tuple, lambda obj: "tuple")
        self.assertEqual(g(d), "dict")
        self.assertEqual(g(l), "list")
        self.assertEqual(g(s), "concrete-set")
        self.assertEqual(g(f), "frozen-set")
        self.assertEqual(g(t), "tuple")

    def test_c3_abc(self):
        c = collections
        mro = functools._c3_mro
        class A(object):
            pass
        class B(A):
            def __len__(self):
                return 0   # implies Sized
        #@c.Container.register
        class C(object):
            pass
        c.Container.register(C)
        class D(object):
            pass   # unrelated
        class X(D, C, B):
            def __call__(self):
                pass   # implies Callable
        expected = [X, c.Callable, D, C, c.Container, B, c.Sized, A, object]
        for abcs in permutations([c.Sized, c.Callable, c.Container]):
            self.assertEqual(mro(X, abcs=abcs), expected)
        # unrelated ABCs don't appear in the resulting MRO
        many_abcs = [c.Mapping, c.Sized, c.Callable, c.Container, c.Iterable]
        self.assertEqual(mro(X, abcs=many_abcs), expected)

    def test_mro_conflicts(self):
        c = collections
        @functools.singledispatch
        def g(arg):
            return "base"
        class O(c.Sized):
            def __len__(self):
                return 0
        o = O()
        self.assertEqual(g(o), "base")
        g.register(c.Iterable, lambda arg: "iterable")
        g.register(c.Container, lambda arg: "container")
        g.register(c.Sized, lambda arg: "sized")
        g.register(c.Set, lambda arg: "set")
        self.assertEqual(g(o), "sized")
        c.Iterable.register(O)
        self.assertEqual(g(o), "sized")   # because it's explicitly in __mro__
        c.Container.register(O)
        self.assertEqual(g(o), "sized")   # see above: Sized is in __mro__
        c.Set.register(O)
        self.assertEqual(g(o), "set")     # because c.Set is a subclass of
                                          # c.Sized and c.Container
        class P(object):
            pass
        p = P()
        self.assertEqual(g(p), "base")
        c.Iterable.register(P)
        self.assertEqual(g(p), "iterable")
        c.Container.register(P)
        with self.assertRaises(RuntimeError) as re_one:
            g(p)
        self.assertIn(
            str(re_one.exception),
            (("Ambiguous dispatch: <class '{prefix}.Container'> "
              "or <class '{prefix}.Iterable'>").format(prefix=abcoll_prefix),
             ("Ambiguous dispatch: <class '{prefix}.Iterable'> "
              "or <class '{prefix}.Container'>").format(prefix=abcoll_prefix)),
        )
        class Q(c.Sized):
            def __len__(self):
                return 0
        q = Q()
        self.assertEqual(g(q), "sized")
        c.Iterable.register(Q)
        self.assertEqual(g(q), "sized")   # because it's explicitly in __mro__
        c.Set.register(Q)
        self.assertEqual(g(q), "set")     # because c.Set is a subclass of
                                          # c.Sized and c.Iterable
        @functools.singledispatch
        def h(arg):
            return "base"
        @h.register(c.Sized)
        def _(arg):
            return "sized"
        @h.register(c.Container)
        def _(arg):
            return "container"
        # Even though Sized and Container are explicit bases of MutableMapping,
        # this ABC is implicitly registered on defaultdict which makes all of
        # MutableMapping's bases implicit as well from defaultdict's
        # perspective.
        with self.assertRaises(RuntimeError) as re_two:
            h(c.defaultdict(lambda: 0))
        self.assertIn(
            str(re_two.exception),
            (("Ambiguous dispatch: <class '{prefix}.Container'> "
              "or <class '{prefix}.Sized'>").format(prefix=abcoll_prefix),
             ("Ambiguous dispatch: <class '{prefix}.Sized'> "
              "or <class '{prefix}.Container'>").format(prefix=abcoll_prefix)),
        )
        class R(c.defaultdict):
            pass
        c.MutableSequence.register(R)
        @functools.singledispatch
        def i(arg):
            return "base"
        @i.register(c.MutableMapping)
        def _(arg):
            return "mapping"
        @i.register(c.MutableSequence)
        def _(arg):
            return "sequence"
        r = R()
        self.assertEqual(i(r), "sequence")
        class S(object):
            pass
        class T(S, c.Sized):
            def __len__(self):
                return 0
        t = T()
        self.assertEqual(h(t), "sized")
        c.Container.register(T)
        self.assertEqual(h(t), "sized")   # because it's explicitly in the MRO
        class U(object):
            def __len__(self):
                return 0
        u = U()
        self.assertEqual(h(u), "sized")   # implicit Sized subclass inferred
                                          # from the existence of __len__()
        c.Container.register(U)
        # There is no preference for registered versus inferred ABCs.
        with self.assertRaises(RuntimeError) as re_three:
            h(u)
        self.assertIn(
            str(re_three.exception),
            (("Ambiguous dispatch: <class '{prefix}.Container'> "
              "or <class '{prefix}.Sized'>").format(prefix=abcoll_prefix),
             ("Ambiguous dispatch: <class '{prefix}.Sized'> "
              "or <class '{prefix}.Container'>").format(prefix=abcoll_prefix)),
        )
        class V(c.Sized, S):
            def __len__(self):
                return 0
        @functools.singledispatch
        def j(arg):
            return "base"
        @j.register(S)
        def _(arg):
            return "s"
        @j.register(c.Container)
        def _(arg):
            return "container"
        v = V()
        self.assertEqual(j(v), "s")
        c.Container.register(V)
        self.assertEqual(j(v), "container")   # because it ends up right after
                                              # Sized in the MRO

    def test_cache_invalidation(self):
        try:
            from collections import UserDict
        except ImportError:
            from UserDict import UserDict
        class TracingDict(UserDict):
            def __init__(self, *args, **kwargs):
                UserDict.__init__(self, *args, **kwargs)
                self.set_ops = []
                self.get_ops = []
            def __getitem__(self, key):
                result = self.data[key]
                self.get_ops.append(key)
                return result
            def __setitem__(self, key, value):
                self.set_ops.append(key)
                self.data[key] = value
            def clear(self):
                self.data.clear()
        _orig_wkd = functools.WeakKeyDictionary
        td = TracingDict()
        functools.WeakKeyDictionary = lambda: td
        c = collections
        @functools.singledispatch
        def g(arg):
            return "base"
        d = {}
        l = []
        self.assertEqual(len(td), 0)
        self.assertEqual(g(d), "base")
        self.assertEqual(len(td), 1)
        self.assertEqual(td.get_ops, [])
        self.assertEqual(td.set_ops, [dict])
        self.assertEqual(td.data[dict], g.registry[object])
        self.assertEqual(g(l), "base")
        self.assertEqual(len(td), 2)
        self.assertEqual(td.get_ops, [])
        self.assertEqual(td.set_ops, [dict, list])
        self.assertEqual(td.data[dict], g.registry[object])
        self.assertEqual(td.data[list], g.registry[object])
        self.assertEqual(td.data[dict], td.data[list])
        self.assertEqual(g(l), "base")
        self.assertEqual(g(d), "base")
        self.assertEqual(td.get_ops, [list, dict])
        self.assertEqual(td.set_ops, [dict, list])
        g.register(list, lambda arg: "list")
        self.assertEqual(td.get_ops, [list, dict])
        self.assertEqual(len(td), 0)
        self.assertEqual(g(d), "base")
        self.assertEqual(len(td), 1)
        self.assertEqual(td.get_ops, [list, dict])
        self.assertEqual(td.set_ops, [dict, list, dict])
        self.assertEqual(td.data[dict],
                         functools._find_impl(dict, g.registry))
        self.assertEqual(g(l), "list")
        self.assertEqual(len(td), 2)
        self.assertEqual(td.get_ops, [list, dict])
        self.assertEqual(td.set_ops, [dict, list, dict, list])
        self.assertEqual(td.data[list],
                         functools._find_impl(list, g.registry))
        class X(object):
            pass
        c.MutableMapping.register(X)   # Will not invalidate the cache,
                                       # not using ABCs yet.
        self.assertEqual(g(d), "base")
        self.assertEqual(g(l), "list")
        self.assertEqual(td.get_ops, [list, dict, dict, list])
        self.assertEqual(td.set_ops, [dict, list, dict, list])
        g.register(c.Sized, lambda arg: "sized")
        self.assertEqual(len(td), 0)
        self.assertEqual(g(d), "sized")
        self.assertEqual(len(td), 1)
        self.assertEqual(td.get_ops, [list, dict, dict, list])
        self.assertEqual(td.set_ops, [dict, list, dict, list, dict])
        self.assertEqual(g(l), "list")
        self.assertEqual(len(td), 2)
        self.assertEqual(td.get_ops, [list, dict, dict, list])
        self.assertEqual(td.set_ops, [dict, list, dict, list, dict, list])
        self.assertEqual(g(l), "list")
        self.assertEqual(g(d), "sized")
        self.assertEqual(td.get_ops, [list, dict, dict, list, list, dict])
        self.assertEqual(td.set_ops, [dict, list, dict, list, dict, list])
        g.dispatch(list)
        g.dispatch(dict)
        self.assertEqual(td.get_ops, [list, dict, dict, list, list, dict,
                                      list, dict])
        self.assertEqual(td.set_ops, [dict, list, dict, list, dict, list])
        c.MutableSet.register(X)       # Will invalidate the cache.
        self.assertEqual(len(td), 2)   # Stale cache.
        self.assertEqual(g(l), "list")
        self.assertEqual(len(td), 1)
        g.register(c.MutableMapping, lambda arg: "mutablemapping")
        self.assertEqual(len(td), 0)
        self.assertEqual(g(d), "mutablemapping")
        self.assertEqual(len(td), 1)
        self.assertEqual(g(l), "list")
        self.assertEqual(len(td), 2)
        g.register(dict, lambda arg: "dict")
        self.assertEqual(g(d), "dict")
        self.assertEqual(g(l), "list")
        g._clear_cache()
        self.assertEqual(len(td), 0)
        functools.WeakKeyDictionary = _orig_wkd


if __name__ == '__main__':
    unittest.main()
