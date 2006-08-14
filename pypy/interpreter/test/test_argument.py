from pypy.interpreter.argument import Arguments


class DummySpace(object):
    def newtuple(self, items):
        return tuple(items)

    def is_true(self, obj):
        return bool(obj)

    def unpackiterable(self, it):
        return list(it)

    def newdict(self):
        return {}

    def setitem(self, obj, key, value):
        obj[key] = value

    def getitem(self, obj, key):
        return obj[key]

    def wrap(self, obj):
        return obj

    def str_w(self, s):
        return str(s)

    def isinstance(self, obj, cls):
        return isinstance(obj, cls)

    w_dict = dict

class TestArguments(object):


    def test_unmatch_signature(self):
        space = DummySpace()
        args = Arguments(space, [1,2,3])
        sig = (['a', 'b', 'c'], None, None)
        data = args.match_signature(sig, [])
        new_args = args.unmatch_signature(sig, data)
        assert args.unpack() == new_args.unpack()

        args = Arguments(space, [1])
        sig = (['a', 'b', 'c'], None, None)
        data = args.match_signature(sig, [2, 3])
        new_args = args.unmatch_signature(sig, data)
        assert args.unpack() == new_args.unpack()

        args = Arguments(space, [1,2,3,4,5])
        sig = (['a', 'b', 'c'], 'r', None)
        data = args.match_signature(sig, [])
        new_args = args.unmatch_signature(sig, data)
        assert args.unpack() == new_args.unpack()

        args = Arguments(space, [1], {'c': 3, 'b': 2})
        sig = (['a', 'b', 'c'], None, None)
        data = args.match_signature(sig, [])
        new_args = args.unmatch_signature(sig, data)
        assert args.unpack() == new_args.unpack()

        args = Arguments(space, [1], {'c': 5})
        sig = (['a', 'b', 'c'], None, None)
        data = args.match_signature(sig, [2, 3])
        new_args = args.unmatch_signature(sig, data)
        assert args.unpack() == new_args.unpack()

        args = Arguments(space, [1], {'c': 5, 'd': 7})
        sig = (['a', 'b', 'c'], None, 'kw')
        data = args.match_signature(sig, [2, 3])
        new_args = args.unmatch_signature(sig, data)
        assert args.unpack() == new_args.unpack()

        args = Arguments(space, [1,2,3,4,5], {'e': 5, 'd': 7})
        sig = (['a', 'b', 'c'], 'r', 'kw')
        data = args.match_signature(sig, [2, 3])
        new_args = args.unmatch_signature(sig, data)
        assert args.unpack() == new_args.unpack()

        args = Arguments(space, [], {}, w_stararg=[1], w_starstararg={'c': 5, 'd': 7})
        sig = (['a', 'b', 'c'], None, 'kw')
        data = args.match_signature(sig, [2, 3])
        new_args = args.unmatch_signature(sig, data)
        assert args.unpack() == new_args.unpack()

        args = Arguments(space, [1,2], {'g': 9}, w_stararg=[3,4,5], w_starstararg={'e': 5, 'd': 7})
        sig = (['a', 'b', 'c'], 'r', 'kw')
        data = args.match_signature(sig, [2, 3])
        new_args = args.unmatch_signature(sig, data)
        assert args.unpack() == new_args.unpack()

