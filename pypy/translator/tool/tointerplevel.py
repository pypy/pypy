# this module can still be used, but it is no
# longer needed to bootstrap pypy.

import autopath
import sys
import optparse
import os
import new

from pypy.objspace.flow.objspace import FlowObjSpace
from pypy.translator.translator import Translator
from pypy.translator.geninterplevel import GenRpy, needed_passes as genrpy_needed_passes

# change default
FlowObjSpace.builtins_can_raise_exceptions = True

def main():
    opt_parser = optparse.OptionParser(usage="usage: %prog [options] module-file obj-name...")
    opt_parser.add_option("--import-as", dest="as", type="string",
                          help="import module-file with this name")
    opt_parser.add_option("-o","--out",dest="output",type="string", help="output file")
    opt_parser.add_option("--modname",dest="modname", type="string", help="modname to be used by GenRpy")

    options, args = opt_parser.parse_args()

    if len(args) < 1:
        opt_parser.error("missing module-file")
    if len(args) < 2:
        print "no obj-name given. Using the module dict!"
        
    modfile = os.path.abspath(args[0])

    name = os.path.splitext(os.path.basename(modfile))[0]

    as = options.as or name

    mod = new.module(as)
    mod.__dict__['__file__'] = modfile
    execfile(modfile, mod.__dict__)

    del mod.__dict__['__builtins__']

    modname = options.modname or name

    objs = []

    for objname in args[1:]:
        try:
            objs.append(getattr(mod, objname))
        except AttributeError, e:
            raise Exception,"module has no object '%s'" % objname

    if len(objs) == 0:
        entrypoint = mod.__dict__
    elif len(objs) == 1:
        entrypoint = objs[0]
    else:
        entrypoint = tuple(objs)

    t = Translator(None, verbose=False, simplifying=genrpy_needed_passes, builtins_can_raise_exceptions=True)
    gen = GenRpy(t, entrypoint, modname, mod.__dict__)

    output = options.output or modname + "interp.py"

    print "generating %s..." % output

    gen.gen_source(output)
    


if __name__ == "__main__":
    main()
    
    



    
