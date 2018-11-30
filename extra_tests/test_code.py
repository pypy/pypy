import sys
import cStringIO
import code


def test_flush_stdout_on_error():
    runner = code.InteractiveInterpreter()
    old_stdout = sys.stdout
    try:
        mystdout = cStringIO.StringIO()
        sys.stdout = mystdout
        runner.runcode(compile("print 5,;0/0", "<interactive>", "exec"))
    finally:
        sys.stdout = old_stdout

    if '__pypy__' in sys.builtin_module_names:
        assert mystdout.getvalue() == "5\n"
    else:
        assert mystdout.getvalue() == "5"
