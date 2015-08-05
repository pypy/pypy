==================================
VMProf: a profiler for RPython VMs
==================================

**Limited to 64-bit Linux.**


from rpython.rlib import rvmprof


Your VM must have an interpreter for "code" objects, which can be
of any RPython instance.

Use this decorator on the mainloop of the interpreter, to tell vmprof
when you enter and leave a "code" object:

    def vmprof_execute_code(name, get_code_fn, result_class=None):
        """Decorator to be used on the function that interprets a code object.

        'name' must be a unique name.

        'get_code_fn(*args)' is called to extract the code object from the
        arguments given to the decorated function.

        The original function can return None, an integer, or an instance.
        In the latter case (only), 'result_class' must be set.

        NOTE: for now, this assumes that the decorated functions only takes
        instances or plain integer arguments, and at most 5 of them
        (including 'self' if applicable).
        """


The class of code objects needs to be registered by calling the
following function (once, before translation):

    def register_code_object_class(CodeClass, full_name_func):
        """NOT_RPYTHON
        Register statically the class 'CodeClass' as containing user
        code objects.

        full_name_func() is a function called at runtime with an
        instance of CodeClass and it should return a string.  This
        is the string stored in the vmprof file identifying the code
        object.  It can be directly an unbound method of CodeClass.
        IMPORTANT: the name returned must be at most MAX_FUNC_NAME
        characters long, and with exactly 3 colons, i.e. of the form

            class:func_name:func_line:filename

        where 'class' is 'py' for PyPy.

        Instances of the CodeClass will have a new attribute called
        '_vmprof_unique_id', but that's managed internally.
        """


To support adding new code objects at run-time, whenever a code
object is instantiated, call this function:

    @specialize.argtype(1)
    def register_code(code, name):
        """Register the code object.  Call when a new code object is made.
        """

    @specialize.argtype(1)
    def get_unique_id(code):
        """Return the internal unique ID of a code object.  Can only be
        called after register_code().  Call this in the jitdriver's
        method 'get_unique_id(*greenkey)'.  Always returns 0 if we
        didn't call register_code_object_class() on the class.
        """


Enable the profiler with:

    def enable(fileno, interval):
        """Enable vmprof.  Writes go to the given 'fileno'.
        The sampling interval is given by 'interval' as a number of
        seconds, as a float which must be smaller than 1.0.
        Raises VMProfError if something goes wrong.
        """


The file descriptor must remain open until the profiler is disabled.
The profiler must be disabled before the program exit, otherwise the
file is incompletely written.  Disable it with:

    def disable():
        """Disable vmprof.
        Raises VMProfError if something goes wrong.
        """

You should close the file descriptor afterwards; it is not
automatically closed.
