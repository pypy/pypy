from __future__ import unicode_literals

from rpython.tool import py3distance


def count(name, source):
    tokens = py3distance.tokenize_source(source)
    code = py3distance.blank_strings_and_comments(source, tokens)
    matcher = dict((n, m) for n, m, _ in py3distance.CATEGORIES)[name]
    if hasattr(matcher, 'findall'):
        return len(matcher.findall(code))
    return matcher(tokens)


def test_ur_prefix_counted_in_code():
    assert count('ur_prefix', 'x = ur"a+"\ny = UR\'b\'\n') == 2


def test_ur_prefix_not_counted_elsewhere():
    source = ('x = u"a" + r"b" + "ur\'c\'"  # ur"d"\n'
              'your = "e"\n')
    assert count('ur_prefix', source) == 0


def test_blanking_keeps_prefix_and_quotes():
    source = 'x = ur"secret" + """more"""\n'
    tokens = py3distance.tokenize_source(source)
    code = py3distance.blank_strings_and_comments(source, tokens)
    assert code == 'x = ur"xxxxxx" + """xxxx"""\n'


def test_bare_tuple_listcomp():
    source = ('a = [c for c in "a", "b"]\n'
              'b = [c for c in x for d in 1, 2]\n')
    assert count('bare_tuple_listcomp', source) == 2


def test_bare_tuple_listcomp_ignores_valid_forms():
    source = ('a = [c for c in ("a", "b")]\n'
              'b = [f(c, d) for c in x if g(c, d)]\n'
              'c = [c in x, y]\n'
              'd = [(c, d) for c, d in pairs]\n'
              'e = {k: v for k, v in items}\n')
    assert count('bare_tuple_listcomp', source) == 0


def test_tuple_print_counted_without_future_import():
    source = ('print("a", 1)\n'
              'print("a")\n'
              'print(f(a, b))\n'
              'x = print\n')
    assert count('tuple_print', source) == 1


def test_tuple_print_not_counted_with_future_import():
    source = ('"""doc"""\n'
              'from __future__ import absolute_import, print_function\n'
              'print("a", 1)\n')
    assert count('tuple_print', source) == 0
