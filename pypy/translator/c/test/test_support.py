from pypy.translator.c.support import gen_assignments


def gen_assign(input, expected):
    assert ' '.join(gen_assignments(input)) == expected

def test_gen_assignments():
    yield gen_assign, [('int @', 'a', 'a')], ''
    yield gen_assign, [('int @', 'a', 'b')], 'a = b;'
    yield gen_assign, [('int @', 'a', 'b'),
                       ('int @', 'c', 'b')], 'a = b; c = b;'
    yield gen_assign, [('int @', 'a', 'b'),
                       ('int @', 'b', 'c')], 'a = b; b = c;'
    yield gen_assign, [('int @', 'b', 'c'),
                       ('int @', 'a', 'b')], 'a = b; b = c;'
    yield gen_assign, [('int @', 'a', 'b'),
                       ('int @', 'b', 'a')], '{ int tmp = b; b = a; a = tmp; }'
    yield gen_assign, [('int @', 'a', 'b'),
                       ('int @', 'b', 'c'),
                       ('int @', 'd', 'b')], 'a = b; d = b; b = c;'
