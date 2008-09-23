
TESTCASES = """\
    None
    False
    True
    StopIteration
    Ellipsis
    42
    -17
    sys.maxint
    -1.25
    -1.25 #2
    2+5j
    2+5j #2
    42L
    -1234567890123456789012345678901234567890L
    hello   # not interned
    "hello"
    ()
    (1, 2)
    []
    [3, 4]
    {}
    {5: 6, 7: 8}
    func.func_code
    scopefunc.func_code
    u'hello'
    set()
    set([1, 2])
    frozenset()
    frozenset([3, 4])
""".strip().split('\n')

def readable(s):
    for c, repl in (
        ("'", '_quote_'), ('"', '_Quote_'), (':', '_colon_'), ('.', '_dot_'),
        ('[', '_list_'), (']', '_tsil_'), ('{', '_dict_'), ('}', '_tcid_'),
        ('-', '_minus_'), ('+', '_plus_'),
        (',', '_comma_'), ('(', '_brace_'), (')', '_ecarb_') ):
        s = s.replace(c, repl)
    lis = list(s)
    for i, c in enumerate(lis):
        if c.isalnum() or c == '_':
            continue
        lis[i] = '_'
    return ''.join(lis)

print """class AppTestMarshal:
"""
for line in TESTCASES:
    line = line.strip()
    name = readable(line)
    version = ''
    extra = ''
    if line.endswith('#2'):
        version = ', 2'
        extra = '; assert len(s) in (9, 17)'
    src = '''\
    def test_%(name)s(self):
        import sys
        hello = "he"
        hello += "llo"
        def func(x):
            return lambda y: x+y
        scopefunc = func(42)
        import marshal, StringIO
        case = %(line)s
        print "case: %%-30s   func=%(name)s" %% (case, )
        s = marshal.dumps(case%(version)s)%(extra)s
        x = marshal.loads(s)
        assert x == case
        f = StringIO.StringIO()
        marshal.dump(case, f)
        f.seek(0)
        x = marshal.load(f)
        assert x == case
''' % {'name': name, 'line': line, 'version' : version, 'extra': extra}
    print src
