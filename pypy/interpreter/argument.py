"""
Arguments objects.
"""

from pypy.interpreter.error import OperationError


class Arguments:
    """
    Collects the arguments of a function call.
    
    Instances should be considered immutable.
    """

    ###  Construction  ###

    blind_arguments = 0

    def __init__(self, space, args_w=[], kwds_w={}):
        self.space = space
        self.args_w = args_w
        self.kwds_w = kwds_w

    def frompacked(space, w_args=None, w_kwds=None):
        """Static method to build an Arguments
        from a wrapped sequence and optionally a wrapped dictionary.
        """
        if w_args is None:
            args_w = []
        else:
            args_w = space.unpackiterable(w_args)
        if w_kwds is None:
            return Arguments(space, args_w)
        # maybe we could allow general mappings?
        if not space.is_true(space.isinstance(w_kwds, space.w_dict)):
            raise OperationError(space.w_TypeError,
                                 space.wrap("the keywords must be "
                                            "a dictionary"))
        kwds_w = {}
        for w_key in space.unpackiterable(w_kwds):
            key = space.unwrap(w_key)
            if not isinstance(key, str):
                raise OperationError(space.w_TypeError,
                                     space.wrap("keywords must be strings"))
            kwds_w[key] = space.getitem(w_kwds, w_key)
        return Arguments(space, args_w, kwds_w)
    frompacked = staticmethod(frompacked)

    ###  Manipulation  ###

    def prepend(self, w_firstarg):
        "Return a new Arguments with a new argument inserted first."
        args =  Arguments(self.space, [w_firstarg] + self.args_w, self.kwds_w)
        args.blind_arguments = self.blind_arguments + 1
        return args

    def join(self, other):
        "Return a new Arguments combining the content of two Arguments."
        args_w = self.args_w + other.args_w
        kwds_w = self.kwds_w.copy()
        for key, w_value in other.kwds_w.items():
            if key in kwds_w:
                raise OperationError(self.space.w_TypeError,
                                     self.space.wrap("got multiple values for "
                                                     "keyword argument '%s'" %
                                                     key))
            kwds_w[key] = w_value
        return Arguments(self.space, args_w, kwds_w)

    def pack(self):
        "Return a (wrapped tuple, wrapped dictionary)."
        space = self.space
        w_args = space.newtuple(self.args_w)
        w_kwds = space.newdict([(space.wrap(key), w_value)
                                for key, w_value in self.kwds_w.items()])
        return w_args, w_kwds

    ###  Parsing for function calls  ###

    def parse(self, fnname, signature, defaults_w=[]):
        """Parse args and kwargs to initialize a frame
        according to the signature of code object.
        """
        space = self.space
        args_w = self.args_w
        kwds_w = self.kwds_w
        argnames = signature[0]
        varargname = signature[1]
        kwargname  = signature[2] 
        #
        #   args_w = list of the normal actual parameters, wrapped
        #   kwds_w = real dictionary {'keyword': wrapped parameter}
        #   argnames = list of formal parameter names
        #   scope_w = resulting list of wrapped values
        #
        # We try to give error messages following CPython's, which are
        # very informative.
        #
        co_argcount = len(argnames) # expected formal arguments, without */**

        # put as many positional input arguments into place as available
        scope_w = args_w[:co_argcount]
        input_argcount = len(scope_w)

        # check that no keyword argument conflicts with these
        # note that for this purpose we ignore the first blind_arguments,
        # which were put into place by prepend().  This way, keywords do
        # not conflict with the hidden extra argument bound by methods.
        if kwds_w:
            for name in argnames[self.blind_arguments:input_argcount]:
                if name in kwds_w:
                    self.raise_argerr_multiple_values(fnname, name)

        remainingkwds_w = kwds_w.copy()
        if input_argcount < co_argcount:
            # not enough args, fill in kwargs or defaults if exists
            def_first = co_argcount - len(defaults_w)
            for i in range(input_argcount, co_argcount):
                name = argnames[i]
                if name in remainingkwds_w:
                    scope_w.append(remainingkwds_w[name])
                    del remainingkwds_w[name]
                elif i >= def_first:
                    scope_w.append(defaults_w[i-def_first])
                else:
                    self.raise_argerr(fnname, signature, defaults_w, False)
                    
        # collect extra positional arguments into the *vararg
        if varargname is not None:
            scope_w.append(space.newtuple(args_w[co_argcount:]))
        elif len(args_w) > co_argcount:
            self.raise_argerr(fnname, signature, defaults_w, True)

        # collect extra keyword arguments into the **kwarg
        if kwargname is not None:
            w_kwds = space.newdict([(space.wrap(key), w_value)
                                    for key, w_value in remainingkwds_w.items()])
            scope_w.append(w_kwds)
        elif remainingkwds_w:
            self.raise_argerr_unknown_kwds(fnname, remainingkwds_w)
        return scope_w

    # helper functions to build error message for the above

    def raise_argerr(self, fnname, signature, defaults_w, too_many):
        argnames, varargname, kwargname = signature
        nargs = len(self.args_w)
        n = len(argnames)
        if n == 0:
            if kwargname is not None:
                msg2 = "non-keyword "
            else:
                msg2 = ""
                nargs += len(self.kwds_w)
            msg = "%s() takes no %sargument (%d given)" % (
                fnname, 
                msg2,
                nargs)
        else:
            defcount = len(defaults_w)
            if defcount == 0:
                msg1 = "exactly"
            elif too_many:
                msg1 = "at most"
            else:
                msg1 = "at least"
                n -= defcount
            if kwargname is not None:
                msg2 = "non-keyword "
            else:
                msg2 = ""
            if n == 1:
                plural = ""
            else:
                plural = "s"
            msg = "%s() takes %s %d %sargument%s (%d given)" % (
                fnname,
                msg1,
                n,
                msg2,
                plural,
                nargs)
        raise OperationError(self.space.w_TypeError, self.space.wrap(msg))

    def raise_argerr_multiple_values(self, fnname, argname):
        msg = "%s() got multiple values for keyword argument %s" % (
            fnname,
            argname)
        raise OperationError(self.space.w_TypeError, self.space.wrap(msg))

    def raise_argerr_unknown_kwds(self, fnname, kwds_w):
        if len(kwds_w) == 1:
            msg = "%s() got an unexpected keyword argument '%s'" % (
                fnname,
                kwds_w.keys()[0])
        else:
            msg = "%s() got %d unexpected keyword arguments" % (
                fnname,
                len(kwds_w))
        raise OperationError(self.space.w_TypeError, self.space.wrap(msg))
