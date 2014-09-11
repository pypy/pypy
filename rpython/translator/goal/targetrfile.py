from rpython.rlib import rfile

def entry_point(argv):
    i, o, e = rfile.create_stdio()
    o.write('test\n')
    return 0

# _____ Define and setup target ___

def target(*args):
    return entry_point, None

if __name__ == '__main__':
    import sys
    sys.exit(entry_point(sys.argv))
