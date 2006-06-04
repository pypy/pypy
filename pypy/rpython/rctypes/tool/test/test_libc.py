
def test_libc():
    from pypy.rpython.rctypes.tool.libc import libc 
    t = libc.time
