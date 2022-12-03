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
