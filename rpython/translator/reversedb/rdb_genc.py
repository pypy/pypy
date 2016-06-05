import py

def extra_files():
    srcdir = py.path.local(__file__).join('..', 'rdb-src')
    return [
        srcdir / 'rdb.c',
    ]
