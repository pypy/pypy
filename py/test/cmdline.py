from __future__ import generators
from py import test, path
from py.test import config
import os, sys

#
# main entry point
#
configbasename = 'pytest.py' 

def main(argv=None):
    # the collectors we will be running
    collectors = []
    if argv is None:
        argv = sys.argv
        frame = sys._getframe(1)
        name = frame.f_locals.get('__name__')
        if name != '__main__':
            return # called from an imported test file
        import __main__
        collectors.append(test.collect.Module(__main__)) 
        
    args = argv[1:]
    for x in getanchors(args):
        config.readconfiguration(x) 
    
    if config.restartpython():
        return 
    filenames = config.parseargs(args)
    collectors.extend(getcollectors(filenames))
    if not collectors:
        collectors.append(test.collect.Directory(path.local()))

    reporter = config.reporter 
    runner = test.run.Driver(reporter)
    runner.setup()
    try:
        try:
            reporter.start()
            try:
                for collector in collectors: 
                    runner.run(collector)
            except test.run.Exit:
                pass
        finally:
            runner.teardown() 
    except KeyboardInterrupt:
        print >>sys.stderr, "KEYBOARD INTERRUPT" 
        sys.exit(2) 
    except SystemExit:
        print >>sys.stderr, "SYSTEM Exit" 
        sys.exit(-1) 
    reporter.end()
        
def getcollectors(filenames):
    current = path.local()
    yielded = False 
    for fn in filenames:
        fullfn = current.join(fn, abs=1)
        if fullfn.check(file=1):
            yield test.collect.Module(fullfn)
        elif fullfn.check(dir=1):
            yield test.collect.Directory(fullfn)
        else:
            raise RuntimeError, "%r does not exist" % fn 
        yielded = True
        
def getanchors(args):
    """ yield anchors from skimming the args for existing files/dirs. """
    current = path.local()
    yielded = False 
    for arg in args: 
        anchor = current.join(arg, abs=1) 
        if anchor.check():
            yield anchor 
            yielded = True
    if not yielded:
        yield current 
