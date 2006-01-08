import optparse

from pypy.translator.translator import TranslationContext
from pypy.translator.goal import driver

DEFAULT_OPTIONS = {
  'gc': 'ref',

  'thread': False, # influences GC policy

  'stackless': False,
  'debug': True,
  'insist': False,
   
   'backend': None,
   'lowmem': False,

   'fork_before': None,

   'merge_if_blocks': True
}

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
        'rtype': ['insist'],
        'backendopt': ['merge_if_blocks'],
        'database_c': ['gc', 'stackless'],
        'source_llvm': ['gc', 'stackless'],
        'source_c': [],
    }

    def driver_event(self, kind, goal, func):
        if kind == 'pre':
             print goal
             self.ensure_setup()
        elif kind == 'post':
            used_opts = dict.fromkeys(self.GOAL_USES_OPTS[goal], True)
            self.frozen_options.update(used_opts)

    def ensure_setup(self, argtypes=None, policy=None):
        if not self.driver_setup:
            if argtypes is None:
                 argtypes = []
            self.driver.setup(self.entry_point, argtypes, policy)
            self.ann_argtypes = argtypes
            self.ann_policy = policy
            self.driver_setup = True
        else:
            # check consistency
            if argtypes is not None and argtypes != self.ann_argtypes:
                raise Exception("incosistent argtype supplied")
            if policy is not None and policy != self.ann_policy:
                raise Exception("incosistent annotation polish supplied")

    def update_options(self, argtypes, kwds):
        if argtypes or kwds.get('policy'):
            self.ensure_setup(argtypes, kwds.get('policy'))
        for optname, value in kwds.iteritems():
            if optname in self.frozen_options:
                if getattr(self.driver.options, optname) != value:
                     raise Exception("incosistent option supplied: %s" % optname)
            else:
                setattr(self.driver.options, optname, value)
                self.frozen_options[optname] = True

    def ensure_backend(self, backend=None):
        if backend is not None:
            self.update_options(None, {'backend': backend})
        if self.driver.options.backend is None:
            raise Exception("a backend should have been specified at this point")
        return self.driver.options.backend

    # backend independent

    def annotate(self, argtypes=None, **kwds):
        self.update_options(argtypes, kwds)
        return self.driver.annotate()

    def rtype(self, argtypes=None, **kwds):
        self.update_options(argtypes, kwds)
        return self.driver.rtype()

    # backend depedent
    # xxx finish
    # xxx how to skip a goal?

    def backendopt(self, argtypes=None, **kwds):
        self.update_options(argtypes, kwds)
        self.ensure_backend()
        self.driver.backendopt()

    def backendopt_c(self, argtypes=None, **kwds):
        self.update_options(argtypes, kwds)
        self.ensure_backend('c')
        self.driver.backendopt()
            
    def source(self, argtypes=None, **kwds):
        backend = self.ensure_backend()
        self.update_options(argtypes, kwds)
        getattr(self.driver, 'source_'+backend)()
       
    def source_c(self, argtypes=None, **kwds):
        self.ensure_backend('c')
        self.update_options(argtypes, kwds)
        self.driver.source_c()

    def source_llvm(self, argtypes=None, **kwds):
        self.ensure_backend('llvm')
        self.update_options(argtypes, kwds)
        self.driver.source_c()
        
