#!/usr/bin/env python
"""
Try:
    ./objdump.py file.asm
    ./objdump.py --decode dumpfile
"""
import os, sys, py

def objdump(input):
    os.system('objdump -D --architecture=arm --target=binary %s' % input)


def get_tmp_file():
    # don't use pypy.tool.udir here to avoid removing old usessions which
    # might still contain interesting executables
    udir = py.path.local.make_numbered_dir(prefix='viewcode-', keep=2)
    tmpfile = str(udir.join('dump.tmp'))
    return tmpfile

def decode(source):
    with open(source, 'r') as f:
        data = f.read().strip()
        data = data.decode('hex')

    target = get_tmp_file()
    with open(target, 'wb') as f:
        f.write(data)
    return target


if __name__ == '__main__':
    if len(sys.argv) == 2:
        objdump(sys.argv[1])
    elif len(sys.argv) == 3:
        assert sys.argv[1] == '--decode'
        f = decode(sys.argv[2])
        objdump(f)
    else:
        print >> sys.stderr, __doc__
        sys.exit(2)
