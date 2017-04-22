#!/usr/bin/env python
'''Usage: import_qcgc.py [PATH_TO_QCGC]'''
import sys
import py.path


# Configuration
whitelist = ['src', 'config.h', 'qcgc.c', 'qcgc.h']


def main(qcgc_dir):
    qcgc_src = py.path.local(qcgc_dir)
    include = lambda f: len(set([ x.basename for x in f.parts()]) & set(whitelist)) > 0
    qcgc_files = qcgc_src.visit(fil=include, rec=include)
    qcgc_dest = py.path.local(__file__).join('..')
    for src_file in qcgc_files:
        dest_file = qcgc_dest.join(src_file.relto(qcgc_src))
        dest_file.join('..').ensure(dir=True)
        if dest_file.check():
            dest_file.remove()
        src_file.copy(dest_file)


if __name__ == '__main__':
    if len(sys.argv) != 2:
        print(__doc__)
        sys.exit(2)
    main(sys.argv[1])
