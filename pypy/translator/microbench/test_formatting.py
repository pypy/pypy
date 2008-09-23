iterations = 100000

def test_simple_formatting():
    i = 0
    tup = ('foo', 'bar', 'baz')
    while i < iterations:
        '%s - %s - %s' % tup
        i += 1

def test_dict_formatting():
    i = 0
    d = {'foo': 'bar', 'baz': 'qux'}
    while i < iterations:
        '%(foo)s - %(baz)s' % d
        i += 1

def test_number_formatting():
    i = 0
    tup = (10, 10.1234, 10.1234)
    while i < iterations:
        '%04d %g %2f' % tup
        i += 1

def test_repr_formatting():
    i = 0
    d = {'foo': 'bar', 'baz': 'qux'}
    while i < iterations:
        '%r' % (d,)
        i += 1

def test_format_unicode():
    i = 0
    tup = (u'foo', u'bar')
    while i < iterations:
        '%s %s' % tup
        i += 1

def test_format_long():
    i = 0
    tup = (100000000000L,)
    while i < iterations:
        '%d' % tup
        i += 1
