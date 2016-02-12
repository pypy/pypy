import sys, StringIO

def test_dump(space):
    """test that pycode.dump kind of works with py3 opcodes"""
    compiler = space.createcompiler()
    code = compiler.compile('lambda *, y=7: None', 'filename', 'exec', 0)
    output = None
    stdout = sys.stdout
    try:
        sys.stdout = StringIO.StringIO()
        code.dump()
        output = sys.stdout.getvalue()
        sys.stdout.close()
    finally:
        sys.stdout = stdout
    print '>>>\n' + output + '\n<<<'
    assert ' 1 (7)' in output
    assert ' 4 (None)' in output
    assert ' 19 RETURN_VALUE ' in output
