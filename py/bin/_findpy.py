#
# find and import a version of 'py' 
# 
import sys
import os
from os.path import dirname as opd, exists, join, basename, abspath 

def searchpy(current):
    while 1:
        last = current
        initpy = join(current, '__init__.py') 
        if not exists(initpy): 
            pydir = join(current, 'py') 
            # recognize py-package and ensure it is importable 
            if exists(pydir) and exists(join(pydir, '__init__.py')): 
                for p in sys.path:
                    if p == current:
                        return True 
                print "inserting into sys.path:", current
                sys.path.insert(0, current) 
                return True
        current = opd(current) 
        if last == current: 
            return False 

if not searchpy(abspath(os.curdir)):
    if not searchpy(opd(abspath(sys.argv[0]))):
        if not searchpy(opd(__file__)):
            raise SystemExit, "Could not find 'py' package!"

import py
