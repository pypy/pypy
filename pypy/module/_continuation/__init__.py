from pypy.interpreter.mixedmodule import MixedModule


class Module(MixedModule):
    """This module exposes 'one-shot continuation containers'.

A 'flexibleframe' object from this module is a container that stores a
one-shot continuation.  It is a frame-like object, attached as the
'f_back' of the entry point function that it calls, and with an 'f_back'
of its own.  Unlike normal frames, the continuation exposed in this
'f_back' can be changed, with the switch() and switch2() methods.

Flexible frames are internally implemented using stacklets.  Stacklets
are a bit more primitive (they are one-shot continuations, usable only
once) but that concept only really works in C, not in Python, notably
because of exceptions.
"""

    appleveldefs = {
        'error': 'app_continuation.error',
        'generator': 'app_continuation.generator',
    }

    interpleveldefs = {
        'flexibleframe': 'interp_continuation.W_FlexibleFrame',
    }
