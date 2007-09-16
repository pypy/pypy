# link between the app-level 'imp' module and '__builtin__.importing'.
# XXX maybe this should go together with 'imp.py' and the interp-level
# import logic into a MixedModule.

from pypy.module.__builtin__ import importing

def held(space):
    return space.wrap(importing.getimportlock(space).lock_held())

def acquire(space):
    importing.getimportlock(space).acquire_lock()

def release(space):
    importing.getimportlock(space).release_lock()
