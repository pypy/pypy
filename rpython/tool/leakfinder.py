import sys, gc
try:
    import cStringIO
except ImportError as e:
    if sys.version_info.major > 2:
        raise RuntimeError('use python 2 to run tests')
    raise
import traceback

# Track allocations to detect memory leaks.
# So far, this is used for lltype.malloc(flavor='raw').
#
# Keyed by id(obj): lltype container objects can change
# their hash after allocation (e.g. when turned into a <C object> by
# ll2ctypes), so obj-keyed lookups in remember_free() are unreliable
# See remember_free() for the equality fallback that keeps cpyext working.
TRACK_ALLOCATIONS = False
ALLOCATED = {}    # id(obj) -> (obj, traceback)

class MallocMismatch(Exception):
    def __str__(self):
        dict = self.args[0]
        dict2 = {}
        for obj, traceback in dict.values():
            traceback = traceback.splitlines()
            if len(traceback) > 8:
                traceback = ['    ...'] + traceback[-6:]
            traceback = '\n'.join(traceback)
            dict2.setdefault(traceback, [])
            dict2[traceback].append(obj)
        lines = ['{']
        for traceback, objs in dict2.items():
            lines.append('')
            for obj in objs:
                lines.append('%s:' % (obj,))
            lines.append(traceback)
        lines.append('}')
        return '\n'.join(lines)

def start_tracking_allocations():
    global TRACK_ALLOCATIONS
    if TRACK_ALLOCATIONS:
        result = ALLOCATED.copy()   # nested start
    else:
        result = None
    TRACK_ALLOCATIONS = True
    ALLOCATED.clear()
    return result

def stop_tracking_allocations(check, prev=None, do_collection=gc.collect):
    global TRACK_ALLOCATIONS
    assert TRACK_ALLOCATIONS
    for i in range(5):
        if not ALLOCATED:
            break
        do_collection()
    result = ALLOCATED.copy()
    ALLOCATED.clear()
    if prev is None:
        TRACK_ALLOCATIONS = False
    else:
        ALLOCATED.update(prev)
    if check and result:
        raise MallocMismatch(result)
    return result

def remember_malloc(obj, framedepth=1):
    if TRACK_ALLOCATIONS:
        frame = sys._getframe(framedepth)
        sio = cStringIO.StringIO()
        traceback.print_stack(frame, limit=10, file=sio)
        tb = sio.getvalue()
        ALLOCATED[id(obj)] = (obj, tb)

def remember_free(obj):
    if TRACK_ALLOCATIONS:
        # Fast path: id(obj) is stable even when the object's hash later
        # changes (e.g. when it is turned into a <C object> by ll2ctypes),
        if id(obj) in ALLOCATED:
            del ALLOCATED[id(obj)]
            return
        # Slow path: the object may be freed through a different wrapper of
        # the same allocation than the one that was remembered (e.g. a
        # render_as_const cast in cpyext).  Fall back to an equality scan.
        for key, (o, tb) in ALLOCATED.items():
            try:
                match = o is obj or o == obj
            except Exception:
                # comparing against an already-freed container raises at the
                # Python level (never a C dereference); treat as no match.
                match = False
            if match:
                del ALLOCATED[key]
                return
        raise KeyError(obj)
