#!/usr/bin/env python

# XXX needs to run on codespeak 

import py
import sys
import os

base = py.path.local('/www/codespeak.net/htdocs')

def runpytest(path, outfile):
    lockfile = base.join(".gendoclock")
    return os.system("/admin/bin/withlock %s py.test %s >>%s 2>&1" %(
                     lockfile, path, outfile))

if __name__ == '__main__':
    results = []
    for fn in sys.argv[1:]:
        p = base.join(fn, abs=True)
        assert p.check(), p
        outfile = p.join("gendoc.log")
        wc = py.path.svnwc(p)
        wc.update() 
        rev = wc.info().rev
        outfile.write("gendoc for %s revision %d\n\n" %(p, rev))
        errcode = runpytest(p, outfile)
        if errcode: 
            results.append("in revision %d of %s" %(rev, p))
            results.append("  gendoc failed with %d, see %s " %(
                           errcode, outfile))
            print results[-1]

    if results: 
        for line in results: 
            print >>sys.stderr, line 
        sys.exit(1)
        

        
        
    
    
