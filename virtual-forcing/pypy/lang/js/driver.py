#!/usr/bin/env python

import autopath
from py import path
import py
import os
import sys
from subprocess import *

pwd = path.local(__file__)
shell = pwd.dirpath('test', 'ecma', 'shell.js')
exclusionlist = ['shell.js', 'browser.js']
def filter(filename):
    if filename.basename in exclusionlist or not filename.basename.endswith('.js'):
        return False
    else:
        return True

if py.path.local.sysfind("js") is None:
    print "js interpreter not found in path"
    sys.exit()

results = open('results.txt', 'w')
for f in pwd.dirpath('test', 'ecma').visit(filter):
    print f.basename
    cmd = './js_interactive.py %s %s'%(shell, f)
    p = Popen(cmd, shell=True, stdout=PIPE)
    
    passed = 0
    total = 0
    for line in p.stdout.readlines():
        if "PASSED!" in line:
            passed += 1
            total += 1
        elif "FAILED!" in line:
            total += 1
        
    results.write('%s passed %s of %s tests\n'%(f.basename, passed, total))
    results.flush()
