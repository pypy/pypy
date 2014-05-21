#!/usr/bin/env python

from create_package import *

if __name__ == '__main__':
    import sys
    args = ['create_package',]
    #package.py [--nostrip] [--without-tk] root-pypy-dir [name-of-archive] [name-of-pypy-c] [destination-for-tarball] [pypy-c-path]
    if len(sys.argv) == 1:
        create_package([__file__, '-h'])

    for i, arg in enumerate(sys.argv[1:]):
        if arg == '-h' or arg == '--help':
            create_package([__file__, '-h'])
        elif arg in ['--nostrip', '--without-tk']:
            args.append(arg)
        elif not arg.startswith('--'):
            break
        else:
            create_package([__file__, '-h'])
    i += 1
    if len(sys.argv) > i:
        # root-pypy-dir, ignore
        i += 1
    if len(sys.argv) > i:
        args += ['--archive-name', sys.argv[i]]
        i += 1
    if len(sys.argv) > i:
        args += ['--rename_pypy_c', sys.argv[i]]
        i += 1
    if len(sys.argv) > i:
        args += ['--targetdir', sys.argv[i]]
        i += 1

else:
    print 'please update to use create_package directly instead'
