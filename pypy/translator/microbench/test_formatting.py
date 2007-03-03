iterations = 100000

def test_simple_formatting():
    i = 0
    while i < iterations:
        '%s - %s - %s' % ('foo', 'bar', 'baz')
        i += 1

def test_dict_formatting():
    i = 0
    d = {'foo': 'bar', 'baz': 'qux'}
    while i < iterations:
        '%(foo)s - %(baz)s' % d
        i += 1

def test_number_formatting():
    i = 0
    while i < iterations:
        '%04d %g %2f' % (10, 10.1234, 10.1234)
        i += 1

def test_repr_formatting():
    i = 0
    d = {'foo': 'bar', 'baz': 'qux'}
    while i < iterations:
        '%r' % (d,)
        i += 1

