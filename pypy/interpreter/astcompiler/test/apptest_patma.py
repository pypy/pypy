import pytest

def test_match_sequence_string_bug():
    x = "x"
    match x:
        case ['x']:
            y = 2
        case 'x':
            y = 5
    assert y == 5

def test_sequence_missing_not_used():
    class defaultdict(dict):
        def __missing__(self, key):
            return 0
    x = defaultdict()
    x[1] = 1
    match x:
        case {0: 0}:
            y = 0
        case {**z}:
            y = 1
    assert x == {1: 1} # no keys added
    assert y == 1 # second case applies
    assert z == {1: 1} # the extracted inner dict is like the outer one

def test_error_name_bindings_duplicate():
    with pytest.raises(SyntaxError) as info:
        exec("""
match x:
    case [a, a]:
        pass
""")

def test_error_name_bindings_duplicate_or():
    with pytest.raises(SyntaxError) as info:
        exec("""
def f(x):
    match x:
            case [1 as a,
                ((2 as a) | (3 as a))]: return 17
""")
    assert info.value.msg == "multiple assignments to name 'a' in pattern, previous one was on line 4"
    assert info.value.lineno == 5


def test_error_name_bindings_or():
    with pytest.raises(SyntaxError) as info:
        exec("""
match x:
    case "a" | a:
        pass
""")

def test_error_allow_always_passing_or():
    with pytest.raises(SyntaxError) as info:
        exec("""
match x:
    case a | "a":
        pass
""")
    assert info.value.msg == "name capture 'a' makes remaining patterns unreachable"

def test_error_forbidden_name():
    with pytest.raises(SyntaxError) as info:
        exec("""
match x:
    case 1 as True:
        pass
""")

def test_match_list():
    def match_list(x):
        match x:
            case [True]: return "[True]"
            case [1,2,3]: return "list[1,2,3]"
            case [1]: return "list[1]"
            case []: return "emptylist"
            case [_]: return "list"
    assert match_list(['']) == "list"
    assert match_list([1]) == "list[1]"
    assert match_list([1,2,3]) == "list[1,2,3]"
    assert match_list([1,2,4]) is None
    assert match_list([2,3,4]) is None
    assert match_list([1, 2]) is None
    assert match_list([]) == "emptylist"

def test_match_with_if_bug():
    def match_truthy(x):
        match x:
            case a if a: return a
    assert match_truthy(1) == 1
    assert match_truthy(True) is True
    assert match_truthy([]) is None
    assert match_truthy('') is None


def test_or():
    x = 2
    match x:
        case 1 | 2:
            a = 2
        case _:
            a = 3
    assert a == 2

def test_dont_use_is():
    match [1.0]:
        case [1]: pass
        case _: assert False

def test_only_bind_at_end():
    a = 5
    match [1, 2, 3]:
        case [a, 1, b]:
            pass
    assert a == 5

def test_or_reorder():
    def or_orders(x):
        match x:
            case [a, b, 1] | [b, a, 2]:
                return a, b
        return 12
    assert or_orders([1, 2, 1]) == (1, 2)
    assert or_orders([1, 2, 2]) == (2, 1)
    assert or_orders([1, 3, 4]) == 12

def test_bug_repeated_names_not_reset_between_cases():
    def as_bug(x):
        match x:
            case 1 as y: return y
            case 2 as y: return y
    assert as_bug(1) == 1
    assert as_bug(2) == 2
    assert as_bug(3) is None

def test_bug_match_sequence_star():
    def sequence_star_bug(x):
        match x:
            case [1, a, *rest, x, 3]:
                return a, rest, x
    assert sequence_star_bug([1, 2, 3, 4, 5, 6, 3]) == (2, [3, 4, 5], 6)
    # rest must not end up in globals!
    assert "rest" not in globals()

def test_bug_match_class_builtin():
    def match_class_bool(x):
        match x:
            case bool(b) if b: return "True"
            case bool(): return "False"
    assert match_class_bool(True) == "True"
    assert match_class_bool(False) == "False"

def test_error_repeated_class_keyword():
    with pytest.raises(SyntaxError) as info:
        exec("""
match x:
    case A(a=_, a=_):
        pass
""")

def test_error_duplicate_key():
    with pytest.raises(SyntaxError) as info:
        exec("""
match x:
    case {"a": 1, "a": 2}:
        pass
""")
    assert info.value.msg == "mapping pattern checks duplicate key ('a')"
    assert info.value.lineno == 3

def test_error_key_wrong_kind():
    with pytest.raises(SyntaxError) as info:
        exec("""
match x:
    case {f"{a}": 1}:
        pass
""")
    assert info.value.msg == "mapping pattern keys may only match literals and attribute lookups"
    assert info.value.lineno == 3

def test_error_key_wrong_kind():
    with pytest.raises(SyntaxError) as info:
        exec("""
match x:
    case [a, *b, c, *d]:
        pass
""")
    assert info.value.msg == "multiple starred names in sequence pattern"
    assert info.value.lineno == 3

def test_match_args_tuple():
    class C:
        __match_args__ = ["a", "b"]
        a = 0
        b = 1
    x = C()
    w = y = z = None
    with pytest.raises(TypeError):
        match x:
            case C(y, z):
                w = 12
    assert w is y is z is None

def test_match_keys_duplicate_runtime():
    class K:
        k = "a"
    w = y = z = None
    with pytest.raises(ValueError):
        match {"a": 1, "b": 2}:
            case {K.k: y, "a": z}: w = 12
    assert w is y is z is None

def test_optimize_unpack_sequence_star_no_capture():
    class Sequence:
        def __getitem__(self, index):
            return index
        def __len__(self):
            return 42
        def __iter__(self):
            return self
        def __next__(self):
            return 1
    a = 0
    b = 0
    match Sequence():
        case [0, *_, b, 41]:
            a = 1
    assert a == 1
    assert b == 40

def test_unpack_sequence_bug():
    def f(w):
        match w:
            case (p, q) as x:
                locals()
                return p, q, x
    assert f((1, 2)) == (1, 2, (1, 2))
    assert "p" not in globals()
    assert "q" not in globals()

def test_or_reordering_bug():
    def annoying_or(x):
        match x:
            case ((a, b, c, d, e, 7) |
                 (a, b, d, e, c, 8)):
                        pass
        out = locals()
        del out["x"]
        return out

    res = annoying_or(range(3, 9))
    exp = dict(a=3, b=4, d=5, e=6, c=7)
    assert res == exp

def test_bytearray_does_not_match_sequence():
    def sequence_match(x):
        match x:
            case [120]:
                return 1
            case 120:
                return 2
        return 3
    assert sequence_match(bytearray(b"x")) == 3


def test_error_fstring():
    with pytest.raises(SyntaxError) as info:
        exec("""
def fstringbug():
    match x:
        case f"{x}":
            pass
""")
    assert info.value.msg == "patterns may only match literals and attribute lookups"


def test_collections_abcs():
    import collections.abc
    class Seq(collections.abc.Sequence):
        __getitem__ = None

        def __init__(self, l):
            self.l = l

        def __len__(self):
            return self.l
    match Seq(0):
        case []:
            y = 0
    assert y == 0

    match Seq(34):
        case [*_]:
            y = 10
    assert y == 10

def test_sequence_doesnt_need_length():
    class A:
        def __getitem__(self, x):
            return 1
    match A():
        case [*_]:
            y = 10
    assert y == 10

def test_collections_abc_mapping():
    import collections.abc
    class A:
        pass
    collections.abc.Mapping.register(A)
    match A():
        case [*_]: assert 0, "unreachable"
        case {}: x = 11121
    assert x == 11121

    class B(A): # made after registering
        pass

    match B():
        case [*_]: assert 0, "unreachable"
        case {}: x = 111213434
    assert x == 111213434
