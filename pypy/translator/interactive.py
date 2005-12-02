import optparse

from pypy.translator.translator import TranslationContext
from pypy.translator.goal import driver

DEFAULT_OPTIONS = optparse.Values(defaults={
  'gc': 'ref',

  'thread': False, # influences GC policy

  'stackless': False,
  'debug': True,
  'insist': False,
   
   'backend': None,
   'lowmem': False,

   'fork_before': None
})

class Translation(object):

    def __init__(self, entry_point, argtypes=None, **kwds):
        self.entry_point = entry_point
        self.context = TranslationContext()
        # for t.view() to work just after construction
        graph = self.context.buildflowgraph(entry_point)
        self.context._prebuilt_graphs[entry_point] = graph

        self.driver = driver.TranslationDriver(DEFAULT_OPTIONS)
        
        # hook into driver events
        driver_own_event = self.driver._event
        def _event(kind, goal, func):
            self.driver_event(kind, goal, func)
            driver_own_event(kind, goal, func)
        self.driver._event = _event
        self.driver_setup = False

        self.frozen_options = {}

        self.update_options(argtypes, kwds)

    def driver_event(self, kind, goal, func):
        if kind == 'pre':
             print goal
             self.ensure_setup()
        elif kind == 'post':
            if 'goal' == 'annotate':  # xxx use a table instead
                self.frozen_options['debug'] = True

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
                raise Exception("xxx")
            if policy is not None and policy != self.ann_policy:
                raise Exception("xxx")

    def update_options(self, argtypes, kwds):
        if argtypes or kwds.get('policy'):
            self.ensure_setup(argtypes, kwds.get('policy'))
        for optname, value in kwds:
            if optname in self.frozen_options:
                if getattr(self.driver.options, optname) != value:
                     raise Exception("xxx")
            else:
                setattr(self.driver.options, optname, value)
                self.frozen_options[optname] = True

    def annotate(self, argtypes=None, **kwds):
        self.update_options(argtypes, kwds)
        return self.driver.annotate()

    def source(self, argtypes, **kwds):
        backend = self.ensure_backend()
        self.update_options(argtypes, kwds)
        getattr(self.driver, 'source_'+backend)()
       
    def source_c(self, argtypes, **kwds):
        self.ensure_backend('c')
        self.update_options(argtypes, kwds)
        self.driver.source_c()
        
