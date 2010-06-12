#!/usr/bin/env python

import autopath
import sys
import tarfile
import os, py

goal_dir = py.path.local(__file__).join('..', '..', '..', 'translator', 'goal')

def filenames_from_platform(platform):
    if platform == 'win32':
        files = [goal_dir / 'pypy-c.exe']
        dll = goal_dir.join('pypy-c.dll')
        if dll.check():
            files.append(dll)
    else:
        files = [goal_dir / 'pypy-c']
    for file in files:
        if not file.check():
            print "Necessary file (%s) missing, build pypy" % file
            sys.exit(1)
    return files

def main(outbasename='pypy-c.tar.bz2'):
    files = filenames_from_platform(sys.platform)
    olddir = os.getcwd()
    os.chdir(str(goal_dir))
    try:
        t = tarfile.open(str(goal_dir.join(outbasename)), 'w:bz2')
        for f in files:
            t.add(f.basename)
        t.close()
    finally:
        os.chdir(olddir)

if __name__ == '__main__':
    main()
