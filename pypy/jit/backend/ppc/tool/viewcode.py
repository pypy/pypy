
#!/usr/bin/env python
"""
Try:
    ./viewcode.py file.asm
    ./viewcode.py --decode dumpfile
"""
import os, sys, py
import subprocess

def machine_code_dump(data, originaddr, backend_name, label_list=None):
    assert backend_name in ["ppc", "ppc_32", "ppc_64"]
    tmpfile = get_tmp_file()
    objdump  = "objdump -EB -D --target=binary --adjust-vma=%(origin)d "
    objdump += "--architecture=powerpc %(file)s"
    #
    f = open(tmpfile, 'wb')
    f.write(data)
    f.close()
    p = subprocess.Popen(objdump % {
        'file': tmpfile,
        'origin': originaddr,
    }, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    stdout, stderr = p.communicate()
    assert not p.returncode, ('Encountered an error running objdump: %s' %
                              stderr)
    # drop some objdump cruft
    lines = stdout.splitlines(True)[6:]     # drop some objdump cruft
    return format_code_dump_with_labels(originaddr, lines, label_list)

def format_code_dump_with_labels(originaddr, lines, label_list):
    from pypy.rlib.rarithmetic import r_uint
    if not label_list:
        label_list = []
    originaddr = r_uint(originaddr)
    itlines = iter(lines)
    yield itlines.next() # don't process the first line
    for lbl_start, lbl_name in label_list:
        for line in itlines:
            addr, _ = line.split(':', 1)
            addr = int(addr, 16)
            if addr >= originaddr+lbl_start:
                yield '\n'
                if lbl_name is None:
                    yield '--end of the loop--\n'
                else:
                    yield str(lbl_name) + '\n'
                yield line
                break
            yield line
    # yield all the remaining lines
    for line in itlines:
        yield line

def objdump(input):
    os.system("objdump -EB -D --target=binary --architecture=powerpc %s" % input)


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
