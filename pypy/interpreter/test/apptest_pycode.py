
def test_invalid_positions_dont_crash():
    def f(a, b):
        return a / b

    c = f.__code__.replace(co_linetable=b'\xff')
    list(c.co_lines()) # these must not crash
    list(c._positions())
    c.co_lnotab
