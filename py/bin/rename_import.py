#!/usr/bin/python 

import py, sys
import bike 
import rlcompleter2 
rlcompleter2.setup()

if __name__ == '__main__':
    source = py.path.local(sys.argv[1])
    assert source.check(dir=1) 

    #dest = std.path.local(sys.argv[2])

    #dest.ensure(dir=1) 

    import bike 
    ctx = bike.init().brmctx 

    for x in source.visit(py.path.checker(file=1, fnmatch='*.py'), 
                          py.path.checker(dotfile=0)):
        ctx.paths.append(str(x))


