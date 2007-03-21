# Package initialisation
from pypy.interpreter.mixedmodule import MixedModule

class Module(MixedModule):
    """
    This module implements concurrent constraint logic programming for applications.
    """

    appleveldefs = {
        'make_expression':'app.make_expression'
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
        'dorkspace':'cspace.dorkspace',
        'choose':'cspace.choose',
        'tell':'cspace.tell',

        'distribute':'cspace.distribute',

        '_make_expression':'constraint.constraint._make_expression',
        'all_diff': 'constraint.constraint.make_alldistinct'
        
    }

