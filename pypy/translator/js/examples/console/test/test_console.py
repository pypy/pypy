
import py
py.test.skip("XXX")

from pypy.translator.js.examples.console import console

def test_run_console():
    """ Check if we can read anything
    """
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
