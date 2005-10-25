from pypy.tool.udir import udir 
import sys, os

def update_usession_dir(stabledir = udir.dirpath('usession')): 
    from py import path 
    try:
        if stabledir.check(dir=1): 
            for x in udir.visit(lambda x: x.check(file=1)): 
                target = stabledir.join(x.relto(udir)) 
                if target.check():
                    target.remove()
                else:
                    target.dirpath().ensure(dir=1) 
                try:
                    target.mklinkto(x) 
                except path.Invalid: 
                    x.copy(target) 
    except path.Invalid: 
        print "ignored: couldn't link or copy to %s" % stabledir 

def mkexename(name):
    if sys.platform == 'win32':
        name = os.path.normpath(name + '.exe')
    return name

def assert_rtyper_not_imported(): 
    prefix = 'pypy.rpython.'
    oknames = ('rarithmetic memory memory.lladdress extfunctable ' 
               'lltype objectmodel error ros ootypesystem ootypesystem.ootype'.split())
    wrongimports = []
    for name, module in sys.modules.items(): 
        if module is not None and name.startswith(prefix): 
            sname = name[len(prefix):]
            for okname in oknames: 
                if sname.startswith(okname): 
                    break
            else:
                wrongimports.append(name) 
    if wrongimports: 
       raise RuntimeError("cannot fork because improper rtyper code"
                          " has already been imported: %r" %(wrongimports,))



