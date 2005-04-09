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

    def __init__(self, space, args_w=[], kwds_w={},
                 w_stararg=None, w_starstararg=None):
        self.space = space
        self.arguments_w = list(args_w)
        self.kwds_w = kwds_w.copy()
        self.w_stararg = w_stararg
        self.w_starstararg = w_starstararg

    def frompacked(space, w_args=None, w_kwds=None):
        """Convenience static method to build an Arguments
           from a wrapped sequence and a wrapped dictionary."""
        return Arguments(space, w_stararg=w_args, w_starstararg=w_kwds)
    frompacked = staticmethod(frompacked)

    def __repr__(self):
        if self.w_starstararg is not None:
            return 'Arguments(%s, %s, %s, %s)' % (self.arguments_w,
                                                  self.kwds_w,
                                                  self.w_stararg,
                                                  self.w_starstararg)
        if self.w_stararg is None:
            if not self.kwds_w:
                return 'Arguments(%s)' % (self.arguments_w,)
            else:
                return 'Arguments(%s, %s)' % (self.arguments_w, self.kwds_w)
        else:
            return 'Arguments(%s, %s, %s)' % (self.arguments_w,
                                              self.kwds_w,
                                              self.w_stararg)

    ###  Manipulation  ###

    def unpack(self):
        "Return a ([w1,w2...], {'kw':w3...}) pair."
        # --- unpack the * argument now ---
        if self.w_stararg is not None:
            self.arguments_w += self.space.unpackiterable(self.w_stararg)
            self.w_stararg = None
        # --- unpack the ** argument now ---
        if self.w_starstararg is not None:
            space = self.space
            w_starstararg = self.w_starstararg
            # maybe we could allow general mappings?
            if not space.is_true(space.isinstance(w_starstararg, space.w_dict)):
                raise OperationError(space.w_TypeError,
                                     space.wrap("the keywords must be "
                                                "a dictionary"))
            d = self.kwds_w.copy()   # don't change the original yet,
                                     # in case something goes wrong
            for w_key in space.unpackiterable(w_starstararg):
                try:
                    key = space.str_w(w_key)
                except OperationError:
                    raise OperationError(space.w_TypeError,
                                         space.wrap("keywords must be strings"))
                if key in d:
                    raise OperationError(self.space.w_TypeError,
                                         self.space.wrap("got multiple values "
                                                         "for keyword argument "
                                                         "'%s'" % key))
                d[key] = space.getitem(w_starstararg, w_key)
            self.kwds_w = d
            self.w_starstararg = None
        return self.arguments_w, self.kwds_w

    def prepend(self, w_firstarg):
        "Return a new Arguments with a new argument inserted first."
        args =  Arguments(self.space, [w_firstarg] + self.arguments_w,
                          self.kwds_w, self.w_stararg, self.w_starstararg)
        args.blind_arguments = self.blind_arguments + 1
        return args

    def has_keywords(self):
        return self.kwds_w or (self.w_starstararg is not None and
                               self.space.is_true(self.w_starstararg))

    def fixedunpack(self, argcount):
        """The simplest argument parsing: get the 'argcount' arguments,
        or raise a real ValueError if the length is wrong."""
        if self.has_keywords():
            raise ValueError, "no keyword arguments expected"
        if len(self.arguments_w) > argcount:
            raise ValueError, "too many arguments (%d expected)" % argcount
        if self.w_stararg is not None:
            self.arguments_w += self.space.unpackiterable(self.w_stararg,
                                             argcount - len(self.arguments_w))
            self.w_stararg = None
        elif len(self.arguments_w) < argcount:
            raise ValueError, "not enough arguments (%d expected)" % argcount
        return self.arguments_w

    def firstarg(self):
        "Return the first argument for inspection."
        if self.arguments_w:
            return self.arguments_w[0]
        if self.w_stararg is None:
            return None
        w_iter = self.space.iter(self.w_stararg)
        try:
            return self.space.next(w_iter)
        except OperationError, e:
            if not e.match(self.space, self.space.w_StopIteration):
                raise
            return None

    ###  Parsing for function calls  ###

    def parse(self, fnname, signature, defaults_w=[]):
        """Parse args and kwargs to initialize a frame
        according to the signature of code object.
        """
        space = self.space
        # If w_stararg is not exactly a tuple, unpack it now:
        # self.match_signature() assumes that it can use it directly for
        # a matching *arg in the callee's signature.
        if self.w_stararg is not None:
            if not space.is_true(space.is_(space.type(self.w_stararg),
                                           space.w_tuple)):
                self.unpack()
        try:
            return self.match_signature(signature, defaults_w)
        except ArgErr, e:
            raise OperationError(space.w_TypeError,
                                 space.wrap(e.getmsg(self, fnname)))

    def match_signature(self, signature, defaults_w=[]):
        """Parse args and kwargs according to the signature of a code object,
        or raise an ArgErr in case of failure.
        """
        argnames, varargname, kwargname = signature
        #
        #   args_w = list of the normal actual parameters, wrapped
        #   kwds_w = real dictionary {'keyword': wrapped parameter}
        #   argnames = list of formal parameter names
        #   scope_w = resulting list of wrapped values
        #
        co_argcount = len(argnames) # expected formal arguments, without */**
        if self.w_stararg is not None:
            # There is a case where we don't have to unpack() a w_stararg:
            # if it matches exactly a *arg in the signature.
            if len(self.arguments_w) == co_argcount and varargname is not None:
                pass
            else:
                self.unpack()   # sets self.w_stararg to None
        # always unpack the ** arguments
        if self.w_starstararg is not None:
            self.unpack()

        args_w = self.arguments_w
        kwds_w = self.kwds_w

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
                    raise ArgErrMultipleValues(name)

        remainingkwds_w = kwds_w.copy()
        not_enough = False
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
                    # error: not enough arguments.  Don't signal it immediately
                    # because it might be related to a problem with */** or
                    # keyword arguments, will be checked for below.
                    not_enough = True

        # collect extra positional arguments into the *vararg
        if varargname is not None:
            if self.w_stararg is None:   # common case
                scope_w.append(self.space.newtuple(args_w[co_argcount:]))
            else:      # shortcut for the non-unpack() case above
                scope_w.append(self.w_stararg)
        elif len(args_w) > co_argcount:
            raise ArgErrCount(signature, defaults_w, True)

        # collect extra keyword arguments into the **kwarg
        if kwargname is not None:
            w_kwds = self.space.newdict([])
            for key, w_value in remainingkwds_w.items():
                self.space.setitem(w_kwds, self.space.wrap(key), w_value)
            scope_w.append(w_kwds)
        elif remainingkwds_w:
            raise ArgErrUnknownKwds(remainingkwds_w)

        if not_enough:
            raise ArgErrCount(signature, defaults_w, False)
        return scope_w

    ### Argument <-> list of w_objects together with "shape" information

    def flatten(self):
        shape_cnt  = len(self.arguments_w)        # Number of positional args
        shape_keys = self.kwds_w.keys()           # List of keywords (strings)
        shape_star = self.w_stararg is not None   # Flag: presence of *arg
        shape_stst = self.w_starstararg is not None # Flag: presence of **kwds
        data_w = self.arguments_w + [self.kwds_w[key] for key in shape_keys]
        if shape_star:
            data_w.append(self.w_stararg)
        if shape_stst:
            data_w.append(self.w_starstararg)
        return (shape_cnt, tuple(shape_keys), shape_star, shape_stst), data_w

    def fromshape(space, (shape_cnt,shape_keys,shape_star,shape_stst), data_w):
        args_w = data_w[:shape_cnt]
        p = shape_cnt
        kwds_w = {}
        for i in range(len(shape_keys)):
            kwds_w[shape_keys[i]] = data_w[p]
            p += 1
        if shape_star:
            w_star = data_w[p]
            p += 1
        else:
            w_star = None
        if shape_stst:
            w_starstar = data_w[p]
            p += 1
        else:
            w_starstar = None
        return Arguments(space, args_w, kwds_w, w_star, w_starstar)
    fromshape = staticmethod(fromshape)
    # XXX the "shape" tuple should be considered as a black box from
    #     other code, but translator/genc.h examines it.


#
# ArgErr family of exceptions raised in case of argument mismatch.
# We try to give error messages following CPython's, which are very informative.
#

class ArgErr(Exception):
    pass

class ArgErrCount(ArgErr):

    def __init__(self, signature, defaults_w, too_many):
        self.signature  = signature
        self.defaults_w = defaults_w
        self.too_many   = too_many

    def getmsg(self, args, fnname):
        argnames, varargname, kwargname = self.signature
        args_w, kwds_w = args.unpack()
        nargs = len(args_w)
        if kwargname is not None or (kwds_w and self.defaults_w):
            msg2 = "non-keyword "
        else:
            msg2 = ""
            nargs += len(kwds_w)
        n = len(argnames)
        if n == 0:
            msg = "%s() takes no %sargument (%d given)" % (
                fnname, 
                msg2,
                nargs)
        else:
            defcount = len(self.defaults_w)
            if defcount == 0 and varargname is None:
                msg1 = "exactly"
            elif self.too_many:
                msg1 = "at most"
            else:
                msg1 = "at least"
                n -= defcount
                if not kwds_w:  # msg "f() takes at least X non-keyword args"
                    msg2 = ""   # is confusing if no kwd arg actually provided
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
        return msg

class ArgErrMultipleValues(ArgErr):

    def __init__(self, argname):
        self.argname = argname

    def getmsg(self, args, fnname):
        msg = "%s() got multiple values for keyword argument '%s'" % (
            fnname,
            self.argname)
        return msg

class ArgErrUnknownKwds(ArgErr):

    def __init__(self, kwds_w):
        self.kwds_w = kwds_w

    def getmsg(self, args, fnname):
        kwds_w = self.kwds_w
        if len(kwds_w) == 1:
            msg = "%s() got an unexpected keyword argument '%s'" % (
                fnname,
                kwds_w.keys()[0])
        else:
            msg = "%s() got %d unexpected keyword arguments" % (
                fnname,
                len(kwds_w))
        return msg
