__all__ = ['ContractAspect', 'ContractError', 'PreconditionError', 'PostConditionError']
from aop import *
from copy import deepcopy
class ContractAspect:
    __metaclass__ = Aspect
    def __init__(self):
        self.initial_state = {}

    @around(PointCut(func='[^_].*', klass='.+').execution())
    def contract_check(self, tjp):
        target = tjp.target()
        args, kwargs = tjp.arguments()
        try:
            prefunc = getattr(target, '_pre_%s' % tjp.name())
        except AttributeError:
            prefunc = None
        try:
            postfunc = getattr(target, '_post_%s' % tjp.name())
        except AttributeError:
            postfunc = None
        else:
            oldtarget = deepcopy(target)
                    
        if prefunc is not None:
            status = prefunc(*args, **kwargs)
            if not status:
                raise PreconditionError(tjp.name())
        tjp.proceed(target, *args, **kwargs)
        if postfunc is not None:
            if not postfunc(oldtarget, tjp.result(), *args, **kwargs):
                raise PostconditionError(tjp.name())
        return tjp.result()
                               
    
class ContractError(StandardError):
    pass

class PreconditionError(ContractError):
    pass

class PostconditionError(ContractError):
    pass
