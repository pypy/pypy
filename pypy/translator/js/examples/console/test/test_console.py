
import py

def test_line_skip():
    from pypy.translator.js.examples.console.console import line_split
    assert line_split("asdf", 80) == "asdf"
    assert line_split("a b c d", 3) == "a b\n c \nd"
    assert line_split("a b c d e f g h i j", 3) == "a b\n c \nd e\n f \ng h\n i \nj"

def test_run_console():
    """ Check if we can read anything
    """
    import py
    py.test.skip("XXX")

    from pypy.translator.js.examples.console import console
    pipe = console.run_console("python")
    pipe.stdin.close()
    t = False
    while not t:
        try:
            d = pipe.stdout.read()
            t = True
        except IOError:
            import time
            time.sleep(.1)
