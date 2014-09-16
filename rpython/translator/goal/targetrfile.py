from rpython.rlib import rfile

def entry_point(argv):
    f = rfile.create_file(argv[1], argv[2])
    while True:
        line = f.readline()
        if line == '':
            break
    return 0

# _____ Define and setup target ___

def target(*args):
    return entry_point, None

if __name__ == '__main__':
    import sys
    sys.exit(entry_point(sys.argv))
