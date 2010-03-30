from pypy.rlib.objectmodel import we_are_translated

# RPython raises StackOverflow instead of just RuntimeError when running
# out of C stack.  We need some hacks to support "except StackOverflow:"
# in untranslated code too.  This StackOverflow has a strange shape in
# order to be special-cased by the flow object space (it is replaced by
# the class StackOverflow).

class StackOverflow(RuntimeError):
    """Out of C stack."""

# rename the variable, but the name of the class is still StackOverflow
_StackOverflow = StackOverflow

# replace StackOverflow with this, which works in untranslated code too
StackOverflow = ((RuntimeError, AttributeError),)


def check_stack_overflow(e):
    if we_are_translated():
        return
    # before translation, an "except StackOverflow" includes all RuntimeErrors,
    # including NotImplementedError.  Special-case them.
    if type(e) is not RuntimeError or 'recursion' not in str(e):
        raise e
