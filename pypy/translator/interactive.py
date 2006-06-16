import optparse

import autopath
from pypy.translator.translator import TranslationContext
from pypy.translator import driver

DEFAULT_OPTIONS = driver.DEFAULT_OPTIONS.copy()
DEFAULT_OPTIONS.update({
  'backend': None,
})

class Translation(object):

    def __init__(self, entry_point, argtypes=None, **kwds):
        self.entry_point = entry_point
        self.context = TranslationContext()
        # for t.view() to work just after construction
        graph = self.context.buildflowgraph(entry_point)
        self.context._prebuilt_graphs[entry_point] = graph

        self.driver = driver.TranslationDriver(
            optparse.Values(defaults=DEFAULT_OPTIONS))
         
        # hook into driver events
        driver_own_event = self.driver._event
        def _event(kind, goal, func):
            self.driver_event(kind, goal, func)
            driver_own_event(kind, goal, func)
        self.driver._event = _event
        self.driver_setup = False

        self.frozen_options = {}

        self.update_options(argtypes, kwds)

    GOAL_USES_OPTS = {
        'annotate': ['debug'],
        'rtype_lltype': ['insist'],
        'rtype_ootype': ['insist'],
        'backendopt_lltype': ['raisingop2direct_call', 'merge_if_blocks'],
        'stackcheckinsertion_lltype': [],
        'database_c': ['gc', 'stackless'],
        'source_llvm': [],
        'source_js': [],
        'source_c': [],
        'compile_c': [],
        'compile_llvm': [],
        'source_cl': [],
        'source_cli': [],
        'compile_cli': [],
    }

    def view(self):
        self.context.view()

    def viewcg(self):
        self.context.viewcg()

    def driver_event(self, kind, goal, func):
        if kind == 'pre':
             #print goal
             self.ensure_setup()
        elif kind == 'post':
            used_opts = dict.fromkeys(self.GOAL_USES_OPTS[goal], True)
            self.frozen_options.update(used_opts)

    def ensure_setup(self, argtypes=None, policy=None, standalone=False):
        if not self.driver_setup:
            if standalone:
                assert argtypes is None
            else:
                if argtypes is None:
                    argtypes = []
            self.driver.setup(self.entry_point, argtypes, policy, empty_translator=self.context)
            self.ann_argtypes = argtypes
            self.ann_policy = policy
            self.driver_setup = True
        else:
            # check consistency
            if standalone:
                assert argtypes is None
                assert self.ann_argtypes is None
            elif argtypes is not None and argtypes != self.ann_argtypes:
                raise Exception("inconsistent argtype supplied")
            if policy is not None and policy != self.ann_policy:
                raise Exception("inconsistent annotation polish supplied")

    def update_options(self, argtypes, kwds):
        if argtypes or kwds.get('policy') or kwds.get('standalone'):
            self.ensure_setup(argtypes, kwds.get('policy'),
                                        kwds.get('standalone'))
        for optname, value in kwds.iteritems():
            if optname in ('policy', 'standalone'):
                continue
            if optname in self.frozen_options:
                if getattr(self.driver.options, optname) != value:
                     raise Exception("inconsistent option supplied: %s" % optname)
            else:
                if not hasattr(self.driver.options, optname):
                    raise TypeError('driver has no option %r' % (optname,))
                setattr(self.driver.options, optname, value)
                self.frozen_options[optname] = True

    def ensure_opt(self, name, value=None, fallback=None):
        if value is not None:
            self.update_options(None, {name: value})
        elif fallback is not None and name not in self.frozen_options:
            self.update_options(None, {name: fallback})
        val =  getattr(self.driver.options, name)
        if val is None:
            raise Exception("the %r option should have been specified at this point" % name)
        return val

    def ensure_type_system(self, type_system=None):
        if type_system is None:
            backend = self.driver.options.backend
            if backend is not None:
                type_system = driver.backend_to_typesystem(backend)
        return self.ensure_opt('type_system', type_system, 'lltype')
        
    def ensure_backend(self, backend=None):
        backend = self.ensure_opt('backend', backend)
        self.ensure_type_system()
        if backend == 'llvm':
            self.update_options(None, {'gc': 'boehm'})
        return backend

    # disable some goals (steps)
    def disable(self, to_disable):
        self.driver.disable(to_disable)

    # backend independent

    def annotate(self, argtypes=None, **kwds):
        self.update_options(argtypes, kwds)
        return self.driver.annotate()

    # type system dependent

    def rtype(self, argtypes=None, **kwds):
        self.update_options(argtypes, kwds)
        ts = self.ensure_type_system()
        return getattr(self.driver, 'rtype_'+ts)()        

    def backendopt(self, argtypes=None, **kwds):
        self.update_options(argtypes, kwds)
        ts = self.ensure_type_system('lltype')
        return getattr(self.driver, 'backendopt_'+ts)()                
            
    # backend depedent

    def source(self, argtypes=None, **kwds):
        self.update_options(argtypes, kwds)
        backend = self.ensure_backend()
        getattr(self.driver, 'source_'+backend)()
       
    def source_c(self, argtypes=None, **kwds):
        self.update_options(argtypes, kwds)
        self.ensure_backend('c')
        self.driver.source_c()

    def source_llvm(self, argtypes=None, **kwds):
        self.update_options(argtypes, kwds)
        self.ensure_backend('llvm')
        self.driver.source_llvm()

    def source_js(self, argtypes=None, **kwds):
        self.update_options(argtypes, kwds)
        self.ensure_backend('js')
        self.driver.source_js()
        return open(str(self.driver.gen.filename)).read()

    def source_cl(self, argtypes=None, **kwds):
        self.update_options(argtypes, kwds)
        self.ensure_backend('cl')
        self.driver.source_cl()

    def compile(self, argtypes=None, **kwds):
        self.update_options(argtypes, kwds)
        backend = self.ensure_backend()
        getattr(self.driver, 'compile_'+backend)()
        return self.driver.c_entryp
       
    def compile_c(self, argtypes=None, **kwds):
        self.update_options(argtypes, kwds)
        self.ensure_backend('c')
        self.driver.compile_c()
        return self.driver.c_entryp

    def compile_llvm(self, argtypes=None, **kwds):
        self.update_options(argtypes, kwds)
        self.ensure_backend('llvm')
        self.driver.compile_llvm()
        return self.driver.c_entryp
  
    def compile_cli(self, argtypes=None, **kwds):
        self.update_options(argtypes, kwds)
        self.ensure_backend('cli')
        self.driver.compile_cli()
        return self.driver.c_entryp

    def source_cli(self, argtypes=None, **kwds):
        self.update_options(argtypes, kwds)
        self.ensure_backend('cli')
        self.driver.source_cli()
