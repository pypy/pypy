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

