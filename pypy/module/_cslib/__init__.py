# Package initialisation
from pypy.interpreter.mixedmodule import MixedModule

#print '_csp module'

class Module(MixedModule):
    appleveldefs = {
    }

    interpleveldefs = {
        'FiniteDomain'    : 'fd.make_fd',
        'AllDistinct'     : 'constraint.make_alldistinct',
        '_make_expression': 'constraint.interp_make_expression',
        'Repository'      : 'propagation.make_repo',
        'Solver'          : 'propagation.make_solver'
    }
