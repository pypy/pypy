def test_match_sequence_string_bug():
    x = "x"
    match x:
        case ['x']:
            y = 2
        case 'x':
            y = 5
    assert y == 5
