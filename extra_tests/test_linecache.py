import gc
import linecache
from textwrap import dedent
import weakref

def test_linecache_race():
    # Test that checkcache is resilient to possible race conditions
    # gh-5109
    def gen_func(n):
        func_code = dedent("""
            def func():
                pass
        """)
        g = {}
        exec(func_code, g, g)
        func = g['func']

        filename = f"<generated-{n}>"
        linecache.cache[filename] = (len(func_code), None, func_code.splitlines(True), filename)

        def cleanup_linecache(filename):
            def _cleanup():
                if filename in linecache.cache:
                    del linecache.cache[filename]
            return _cleanup

        weakref.finalize(func, cleanup_linecache(filename))

        return func

    # Unpatched, this required about 6000 iterations to fail
    for n in range(10_000):
        func = gen_func(n)
        del func
        linecache.checkcache()
        if n % 1000 == 0:
            # print(f"{n:5}")
            pass
