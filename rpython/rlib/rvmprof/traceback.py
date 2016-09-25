"""
Semi-public interface to gather and print a raw traceback, e.g.
from the faulthandler module.
"""

from rpython.rlib.rvmprof import cintf
from rpython.rlib.objectmodel import specialize


@specialize.arg(0, 1)
def traceback(CodeClass, callback, arg):
    """For each frame, invoke 'callback(depth, code_obj, arg)'.
    'code_obj' is either a CodeClass, or None if we fail to determine
    what it should be (shouldn't occur, but you never know).  If it
    returns a non-null integer, stop and return that.  Otherwise,
    continue.  If all callbacks return 0, this returns 0.
    """
    s = cintf.get_rvmprof_stack()
    depth = 0
    while s:
        if s.c_kind == cintf.VMPROF_CODE_TAG:
            code_id = s.c_value
            found_code = None
            if code_id != 0:
                all_code_wrefs = CodeClass._vmprof_weak_list.get_all_handles()
                i = len(all_code_wrefs) - 1
                while i >= 0:
                    code = all_code_wrefs[i]()
                    if code is not None and code._vmprof_unique_id == code_id:
                        found_code = code
                        break
                    i -= 1
            result = callback(depth, found_code, arg)
            if result != 0:
                return result
            depth += 1
        s = s.c_next
    return 0
