# Package initialisation
from pypy.interpreter.mixedmodule import MixedModule

class Module(MixedModule):
    """
    This module implements concurrent constraint logic programming for applications.
    """

    appleveldefs = {
    }

    interpleveldefs = {
        'switch_debug_info':'misc.switch_debug_info',
        
        'future':'thread.future',
        'stacklet':'thread.stacklet',
        'this_thread':'thread.this_thread',
        
        'sched_info':'scheduler.sched_info',
        'schedule':'scheduler.schedule',
        'reset_scheduler':'scheduler.reset_scheduler',

        'newspace':'cspace.newspace',
        'choose':'cspace.choose',
        'tell':'cspace.tell',

        'distribute':'constraint.distributor.distribute',

        'make_expression':'constraint.constraint.make_expression',
        'all_diff': 'constraint.constraint.make_alldistinct'
        
    }

