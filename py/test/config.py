from __future__ import generators
from py import test, path
from py.__impl__.test.tool import optparse 

import os, sys, new
dummy = object()

#
# config file handling (utest.conf)
#
configbasename = 'pytest.py' 

class Config:
    def __init__(self):
        self.files = {}
        self.option = optparse.Values()

    def getoptions(self):
        Option = test.Option
        return ('py.test standard options', [
            Option('-v', '--verbose', 
                   action="count", dest="verbose", default=0,
                   help="increase verbosity"),
            Option('-x', '--exitfirst', 
                   action="store_true", dest="exitfirstproblem", default=False, 
                   help="exit instantly on first error or failed test."),
            Option('-S', '--nocapture', 
                   action="store_true", dest="nocapture", default=False,
                   help="disable catching of sys.stdout/stderr output."),
            Option('-l', '--showlocals', 
                   action="store_true", dest="showlocals", default=False, 
                   help="show locals in tracebacks (disabled by default)"),
            Option('', '--fulltrace', 
                   action="store_true", dest="fulltrace", default=False, 
                   help="Don't try to cut any tracebacks (default is to cut)"),
            Option('', '--nomagic', 
                   action="store_true", dest="nomagic", default=False, 
                   help="don't invoke magic to e.g. beautify failing/error statements."),
            Option('', '--pdb',
                   action="store_true", dest="usepdb", default=False,
                   help="Start pdb (the Python debugger) on errors."),
            Option('', '--collectonly', 
                   action="store_true", dest="collectonly", default=False,
                   help="only collect tests, don't execute them. "),
        ])

    def _gettmpdir(self, sessiondir=[]):
        try:
            return sessiondir[0]
        except IndexError:
            d = path.local.make_numbered_dir(base='utest-')
            sessiondir.append(d)
            return d
    tmpdir = property(_gettmpdir, None, None, "Temp Directory")

    def readconfiguration(self, anchor):
        """ read all neccessary configuration files for the given anchor file.
       
        a) visit downwards for all config files 
        b) traverse upwards to find parent config files 
        """
        if anchor.check(file=1):
            anchor = anchor.dirpath()
        fil = path.checker(file=1, basename=configbasename) 
        for p in anchor.visit(fil=fil, rec=path.checker(dotfile=0)):
            if p not in self.files:
                self.importconfig(p)
        candidates = [x / configbasename for x in anchor.parts()]
        candidates.reverse() 
        for p in candidates: 
            if p.check(file=1): 
                self.importconfig(p)
       
    #def getconfig(self, directory, upwards=True): 
    #    assert upwards, "for now"
    #    assert directory.check(dir=1)
    #    here = directory / configbasename 
    #    if here.check(file=1):
    #        return self.importconfig(here) 
    #    min = None
    #    for x in self.files:
    #        r = directory.relto(x.dirpath())
    #        if r and (min is None or len(r) < min):
    #            min = x
    #    if min:
    #        return self.importconfig(min)

    def importconfig(self, uconf):    
        try:
            return self.files[uconf]
        except KeyError:
            par = [x.basename for x in uconf.parts()]
            name = "_".join(par) 
            mod = new.module(name)
            mod.__file__ = uconf 
            execfile(str(uconf), mod.__dict__) 
            self.files[uconf] = mod
            return mod

    def listconfigs(self, reverse=False): 
        """ list config modules, (reverse) sorted by length of path, shortest first. """
        keys = self.files.keys()
        keys.sort() 
        configs = []
        for key in keys:
            configs.append(self.files[key])
        if reverse:
            configs.reverse()
        return configs
        
    def topmost(self):
        """ return topmost (shortest path) config module. """
        configs = self.listconfigs()
        if not configs:
            return None 
        return configs[0]

    def _getreporter(self):
        try:
            return self._reporter 
        except AttributeError:
             self._reporter = test.TextReporter()
        return self._reporter 
    reporter = property(_getreporter, None, None)

    def getfirst(self, param, default=dummy):
        """ return first found parameter. """
        for config in self.listconfigs():
            try:
                return getattr(config, param)
            except AttributeError:
                pass
        if default is dummy:
            raise AttributeError, param
        return default
        #if default is not dummy:
        #    return getattr(self, param, default)
        #return getattr(self, param)
            
    def parseargs(self, args): 
        # first a small fight with optparse to merge the 
        # utest.conf file options correctly 
        parser = optparse.OptionParser()
        for config in self.listconfigs() + [self]: 
            meth = getattr(config, 'getoptions', None)
            if meth is not None:
                groupname, groupoptions = meth()
                optgroup = optparse.OptionGroup(parser, groupname) 
                optgroup.add_options(groupoptions)
                parser.add_option_group(optgroup)

        # extract and remove defaults from options
        for option in flattenoptions(parser):
            if option.dest:
                value = self.getfirst(option.dest, option.default) 
                #print "setting %r to %r" %(option.dest, value)
                setattr(self.option, option.dest, value) 
                option.default = 'NODEFAULT'
        
        # parse cmdline args  
        cmdlineoption, remaining = parser.parse_args(args, self.option) 
        # override previously computed defaults 
        #for name in cmdlineoption.__dict__:
        #    if not name.startswith('_'):
        #        print "resetting %r to %r" %(name, cmdlineoption.__dict__[name])
        #        setattr(self.option, name, cmdlineoption.__dict__[name])
        return remaining 

    def restartpython(self):
        # XXX better hack to restart with correct python version? 
        pythonexecutable = self.getfirst('pythonexecutable', None)
        if pythonexecutable:
            bn = path.local(sys.executable).basename
            if bn != pythonexecutable:
                # XXX shell escaping
                print "restarting with", pythonexecutable
                print "%s %s" % (pythonexecutable, " ".join(sys.argv[0:]))
                os.system("%s %s" % (pythonexecutable, " ".join(sys.argv[0:])))
                return True

config = Config()

# helpers 

def flattenoptions(parser):
    for group in parser.option_groups:
        for y in group.option_list: 
            yield y
    for x in parser.option_list:
        yield x 
