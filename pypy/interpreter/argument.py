"""
Arguments objects.
"""

from pypy.interpreter.error import OperationError

class AbstractArguments:

    def parse_into_scope(self, w_firstarg,
                         scope_w, fnname, signature, defaults_w=[]):
        """Parse args and kwargs to initialize a frame
        according to the signature of code object.
        Store the argumentvalues into scope_w.
        scope_w must be big enough for signature.
        """
        argnames, varargname, kwargname = signature
        has_vararg = varargname is not None
        has_kwarg = kwargname is not None
        try:
            return self._match_signature(w_firstarg,
                                         scope_w, argnames, has_vararg,
                                         has_kwarg, defaults_w, 0)
        except ArgErr, e:
            raise OperationError(self.space.w_TypeError,
                                 self.space.wrap(e.getmsg(fnname)))

    def _parse(self, w_firstarg, signature, defaults_w, blindargs=0):
        """Parse args and kwargs according to the signature of a code object,
        or raise an ArgErr in case of failure.
        """
        argnames, varargname, kwargname = signature
        scopelen = len(argnames)
        has_vararg = varargname is not None
        has_kwarg = kwargname is not None
        if has_vararg:
            scopelen += 1
        if has_kwarg:
            scopelen += 1
        scope_w = [None] * scopelen
        self._match_signature(w_firstarg, scope_w, argnames, has_vararg, has_kwarg, defaults_w, blindargs)
        return scope_w    

    def parse(self, fnname, signature, defaults_w=[], blindargs=0):
        """Parse args and kwargs to initialize a frame
        according to the signature of code object.
        """
        try:
            return self._parse(None, signature, defaults_w, blindargs)
        except ArgErr, e:
            raise OperationError(self.space.w_TypeError,
                                 self.space.wrap(e.getmsg(fnname)))

    # xxx have only this one
    def parse_obj(self, w_firstarg,
                  fnname, signature, defaults_w=[], blindargs=0):
        """Parse args and kwargs to initialize a frame
        according to the signature of code object.
        """
        try:
            return self._parse(w_firstarg, signature, defaults_w, blindargs)
        except ArgErr, e:
            raise OperationError(self.space.w_TypeError,
                                 self.space.wrap(e.getmsg(fnname)))        

    def frompacked(space, w_args=None, w_kwds=None):
        """Convenience static method to build an Arguments
           from a wrapped sequence and a wrapped dictionary."""
        return Arguments(space, [], w_stararg=w_args, w_starstararg=w_kwds)
    frompacked = staticmethod(frompacked)

    def topacked(self):
        """Express the Argument object as a pair of wrapped w_args, w_kwds."""
        space = self.space
        args_w, kwds_w = self.unpack()
        w_args = space.newtuple(args_w)
        w_kwds = space.newdict()
        for key, w_value in kwds_w.items():
            space.setitem(w_kwds, space.wrap(key), w_value)
        return w_args, w_kwds

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

    def match_signature(self, signature, defaults_w):
        """Parse args and kwargs according to the signature of a code object,
        or raise an ArgErr in case of failure.
        """
        return self._parse(None, signature, defaults_w)

    def unmatch_signature(self, signature, data_w):
        """kind of inverse of match_signature"""
        args_w, kwds_w = self.unpack()
        need_cnt = len(args_w)
        need_kwds = kwds_w.keys()
        space = self.space
        argnames, varargname, kwargname = signature
        cnt = len(argnames)
        data_args_w = data_w[:cnt]
        if varargname:
            data_w_stararg = data_w[cnt]
            cnt += 1
        else:
            data_w_stararg = space.newtuple([])

        unfiltered_kwds_w = {}
        if kwargname:
            data_w_starargarg = data_w[cnt]
            for w_key in space.unpackiterable(data_w_starargarg):
                key = space.str_w(w_key)
                w_value = space.getitem(data_w_starargarg, w_key)
                unfiltered_kwds_w[key] = w_value            
            cnt += 1
        assert len(data_w) == cnt
        
        ndata_args_w = len(data_args_w)
        if ndata_args_w >= need_cnt:
            args_w = data_args_w[:need_cnt]
            for argname, w_arg in zip(argnames[need_cnt:], data_args_w[need_cnt:]):
                unfiltered_kwds_w[argname] = w_arg
            assert not space.is_true(data_w_stararg)
        else:
            stararg_w = space.unpackiterable(data_w_stararg)
            datalen = len(data_args_w)
            args_w = [None] * (datalen + len(stararg_w))
            for i in range(0, datalen):
                args_w[i] = data_args_w[i]
            for i in range(0, len(stararg_w)):
                args_w[i + datalen] = stararg_w[i]
            assert len(args_w) == need_cnt
            
        kwds_w = {}
        for key in need_kwds:
            kwds_w[key] = unfiltered_kwds_w[key]
                    
        return Arguments(self.space, args_w, kwds_w)

    def normalize(self):
        """Return an instance of the Arguments class.  (Instances of other
        classes may not be suitable for long-term storage or multiple
        usage.)  Also force the type and validity of the * and ** arguments
        to be checked now.
        """
        args_w, kwds_w = self.unpack()
        return Arguments(self.space, args_w, kwds_w)

    def unpack(self):
        """ Purely abstract
        """
        raise NotImplementedError()

    def firstarg(self):
        """ Purely abstract
        """
        raise NotImplementedError()

    def prepend(self, w_firstarg):
        """ Purely abstract
        """
        raise NotImplementedError()    

    def _match_signature(self, w_firstarg, scope_w, argnames, has_vararg=False, has_kwarg=False, defaults_w=[], blindargs=0):
        """ Purely abstract
        """
        raise NotImplementedError()
    
    def fixedunpack(self, argcount):
        """ Purely abstract
        """
        raise NotImplementedError()


class ArgumentsFromValuestack(AbstractArguments):
    """
    Collects the arguments of a function call as stored on a PyFrame
    valuestack.

    Only for the case of purely positional arguments, for now.
    """

    def __init__(self, space, frame, nargs=0):
        self.space = space
        self.frame = frame
        self.nargs = nargs

    def firstarg(self):
        if self.nargs <= 0:
            return None
        return self.frame.peekvalue(self.nargs - 1)

    def prepend(self, w_firstarg):
        "Return a new Arguments with a new argument inserted first."
        args_w = self.frame.peekvalues(self.nargs)
        return Arguments(self.space, [w_firstarg] + args_w)
        
    def __repr__(self):
        return 'ArgumentsFromValuestack(%r, %r)' % (self.frame, self.nargs)

    def has_keywords(self):
        return False

    def unpack(self):
        args_w = [None] * self.nargs
        for i in range(self.nargs):
            args_w[i] = self.frame.peekvalue(self.nargs - 1 - i)
        return args_w, {}

    def fixedunpack(self, argcount):
        if self.nargs > argcount:
            raise ValueError, "too many arguments (%d expected)" % argcount
        elif self.nargs < argcount:
            raise ValueError, "not enough arguments (%d expected)" % argcount
        data_w = [None] * self.nargs
        nargs = self.nargs
        for i in range(nargs):
            data_w[i] = self.frame.peekvalue(nargs - 1 - i)
        return data_w

    def _rawshape(self, nextra=0):
        return nextra + self.nargs, (), False, False

    def _match_signature(self, w_firstarg, scope_w, argnames, has_vararg=False, has_kwarg=False, defaults_w=[], blindargs=0):
        """Parse args and kwargs according to the signature of a code object,
        or raise an ArgErr in case of failure.
        Return the number of arguments filled in.
        """
        co_argcount = len(argnames)
        extravarargs = None
        input_argcount =  0

        if w_firstarg is not None:
            upfront = 1
            if co_argcount > 0:
                scope_w[0] = w_firstarg
                input_argcount = 1
            else:
                extravarargs = [ w_firstarg ]
        else:
            upfront = 0

        avail = upfront + self.nargs
        
        if avail + len(defaults_w) < co_argcount:
            raise ArgErrCount(blindargs + self.nargs , 0,
                              (co_argcount, has_vararg, has_kwarg),
                              defaults_w, co_argcount - avail - len(defaults_w))
        if avail > co_argcount and not has_vararg:
            raise ArgErrCount(blindargs + self.nargs, 0,
                              (co_argcount, has_vararg, has_kwarg),
                              defaults_w, 0)

        if avail >= co_argcount:
            for i in range(co_argcount - input_argcount):
                scope_w[i + input_argcount] = self.frame.peekvalue(self.nargs - 1 - i)
            if has_vararg:
                if upfront > co_argcount:
                    assert extravarargs is not None                    
                    stararg_w = extravarargs + [None] * self.nargs
                    for i in range(self.nargs):
                        stararg_w[i + len(extravarargs)] = self.frame.peekvalue(self.nargs - 1 - i)
                else:
                    args_left = co_argcount - upfront                
                    stararg_w = [None] * (avail - co_argcount)
                    for i in range(args_left, self.nargs):
                        stararg_w[i - args_left] = self.frame.peekvalue(self.nargs - 1 - i)
                scope_w[co_argcount] = self.space.newtuple(stararg_w)
        else:
            for i in range(self.nargs):
                scope_w[i + input_argcount] = self.frame.peekvalue(self.nargs - 1 - i)
            ndefaults = len(defaults_w)
            missing = co_argcount - avail
            first_default = ndefaults - missing
            for i in range(missing):
                scope_w[avail + i] = defaults_w[first_default + i]
            if has_vararg:
                scope_w[co_argcount] = self.space.newtuple([])

        if has_kwarg:
            scope_w[co_argcount + has_vararg] = self.space.newdict()
        return co_argcount + has_vararg + has_kwarg
    
    def flatten(self):
        data_w = [None] * self.nargs
        for i in range(self.nargs):
            data_w[i] = self.frame.peekvalue(self.nargs - 1 - i)
        return nextra + self.nargs, (), False, False, data_w

    def num_args(self):
        return self.nargs

    def num_kwds(self):
        return 0

class Arguments(AbstractArguments):
    """
    Collects the arguments of a function call.
    
    Instances should be considered immutable.
    """

    ###  Construction  ###

    def __init__(self, space, args_w, kwds_w=None,
                 w_stararg=None, w_starstararg=None):
        self.space = space
        assert isinstance(args_w, list)
        self.arguments_w = args_w
        from pypy.rlib.debug import make_sure_not_resized
        make_sure_not_resized(self.arguments_w)
        self.kwds_w = kwds_w
        self.w_stararg = w_stararg
        self.w_starstararg = w_starstararg

    def num_args(self):
        self._unpack()
        return len(self.arguments_w)

    def num_kwds(self):
        self._unpack()
        return len(self.kwds_w)
        
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
        self._unpack()
        return self.arguments_w, self.kwds_w

    def prepend(self, w_firstarg):
        "Return a new Arguments with a new argument inserted first."
        return Arguments(self.space, [w_firstarg] + self.arguments_w,
                         self.kwds_w, self.w_stararg, self.w_starstararg)
            
    def _unpack(self):
        "unpack the *arg and **kwd into w_arguments and kwds_w"
        # --- unpack the * argument now ---
        if self.w_stararg is not None:
            self.arguments_w = (self.arguments_w +
                                self.space.unpackiterable(self.w_stararg))
            self.w_stararg = None
        # --- unpack the ** argument now ---
        if self.kwds_w is None:
            self.kwds_w = {}
        if self.w_starstararg is not None:
            space = self.space
            w_starstararg = self.w_starstararg
            # maybe we could allow general mappings?
            if not space.is_true(space.isinstance(w_starstararg, space.w_dict)):
                raise OperationError(space.w_TypeError,
                                     space.wrap("argument after ** must be "
                                                "a dictionary"))
            # don't change the original yet,
            # in case something goes wrong               
            d = self.kwds_w.copy()
            for w_key in space.unpackiterable(w_starstararg):
                try:
                    key = space.str_w(w_key)
                except OperationError, e:
                    if not e.match(space, space.w_TypeError):
                        raise
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

    def has_keywords(self):
        return bool(self.kwds_w) or (self.w_starstararg is not None and
                                     self.space.is_true(self.w_starstararg))

    def fixedunpack(self, argcount):
        """The simplest argument parsing: get the 'argcount' arguments,
        or raise a real ValueError if the length is wrong."""
        if self.has_keywords():
            raise ValueError, "no keyword arguments expected"
        if len(self.arguments_w) > argcount:
            raise ValueError, "too many arguments (%d expected)" % argcount
        if self.w_stararg is not None:
            self.arguments_w = (self.arguments_w +
                                self.space.viewiterable(self.w_stararg,
                                         argcount - len(self.arguments_w)))
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

    def _match_signature(self, w_firstarg, scope_w, argnames, has_vararg=False,
                         has_kwarg=False, defaults_w=[], blindargs=0):
        """Parse args and kwargs according to the signature of a code object,
        or raise an ArgErr in case of failure.
        Return the number of arguments filled in.
        """
        #
        #   args_w = list of the normal actual parameters, wrapped
        #   kwds_w = real dictionary {'keyword': wrapped parameter}
        #   argnames = list of formal parameter names
        #   scope_w = resulting list of wrapped values
        #
        co_argcount = len(argnames) # expected formal arguments, without */**
        extravarargs = None
        input_argcount =  0

        if w_firstarg is not None:
            upfront = 1
            if co_argcount > 0:
                scope_w[0] = w_firstarg
                input_argcount = 1
            else:
                extravarargs = [ w_firstarg ]
        else:
            upfront = 0
        
        if self.w_stararg is not None:
            # There is a case where we don't have to unpack() a w_stararg:
            # if it matches exactly a *arg in the signature.
            if (len(self.arguments_w) + upfront == co_argcount and
                has_vararg and
                self.space.is_w(self.space.type(self.w_stararg),
                                self.space.w_tuple)):
                pass
            else:
                self._unpack()   # sets self.w_stararg to None
        # always unpack the ** arguments
        if self.w_starstararg is not None:
            self._unpack()

        args_w = self.arguments_w
        num_args = len(args_w)

        kwds_w = self.kwds_w
        num_kwds = 0
        if kwds_w is not None:
            num_kwds = len(kwds_w)

        avail = num_args + upfront

        if input_argcount < co_argcount:
            # put as many positional input arguments into place as available
            if avail > co_argcount:
                take = co_argcount - input_argcount
            else:
                take = num_args

            for i in range(take):
                scope_w[i + input_argcount] = args_w[i]
            input_argcount += take

        # check that no keyword argument conflicts with these
        # note that for this purpose we ignore the first blindargs,
        # which were put into place by prepend().  This way, keywords do
        # not conflict with the hidden extra argument bound by methods.
        if kwds_w and input_argcount > blindargs:
            for name in argnames[blindargs:input_argcount]:
                if name in kwds_w:
                    raise ArgErrMultipleValues(name)

        remainingkwds_w = self.kwds_w
        missing = 0
        if input_argcount < co_argcount:
            if remainingkwds_w is None:
                remainingkwds_w = {}
            else:
                remainingkwds_w = remainingkwds_w.copy()            
            # not enough args, fill in kwargs or defaults if exists
            def_first = co_argcount - len(defaults_w)
            for i in range(input_argcount, co_argcount):
                name = argnames[i]
                if name in remainingkwds_w:
                    scope_w[i] = remainingkwds_w[name]
                    del remainingkwds_w[name]
                elif i >= def_first:
                    scope_w[i] = defaults_w[i-def_first]
                else:
                    # error: not enough arguments.  Don't signal it immediately
                    # because it might be related to a problem with */** or
                    # keyword arguments, which will be checked for below.
                    missing += 1

        
        # collect extra positional arguments into the *vararg
        if has_vararg:
            if self.w_stararg is None:   # common case
                args_left = co_argcount - upfront
                if args_left < 0:  # check required by rpython
                    assert extravarargs is not None
                    starargs_w = extravarargs
                    if num_args:
                        starargs_w = starargs_w + args_w
                elif num_args > args_left:
                    starargs_w = args_w[args_left:]
                else:
                    starargs_w = []
                scope_w[co_argcount] = self.space.newtuple(starargs_w)
            else:      # shortcut for the non-unpack() case above
                scope_w[co_argcount] = self.w_stararg
        elif avail > co_argcount:
            raise ArgErrCount(avail, num_kwds,
                              (co_argcount, has_vararg, has_kwarg),
                              defaults_w, 0)

        # collect extra keyword arguments into the **kwarg
        if has_kwarg:
            w_kwds = self.space.newdict()
            if remainingkwds_w:
                for key, w_value in remainingkwds_w.items():
                    self.space.setitem(w_kwds, self.space.wrap(key), w_value)
            scope_w[co_argcount + has_vararg] = w_kwds
        elif remainingkwds_w:
            raise ArgErrUnknownKwds(remainingkwds_w)

        if missing:
            raise ArgErrCount(avail, num_kwds,
                              (co_argcount, has_vararg, has_kwarg),
                              defaults_w, missing)

        return co_argcount + has_vararg + has_kwarg
    
    ### Argument <-> list of w_objects together with "shape" information

    def _rawshape(self, nextra=0):
        shape_cnt  = len(self.arguments_w)+nextra        # Number of positional args
        if self.kwds_w:
            shape_keys = self.kwds_w.keys()           # List of keywords (strings)
        else:
            shape_keys = []
        shape_star = self.w_stararg is not None   # Flag: presence of *arg
        shape_stst = self.w_starstararg is not None # Flag: presence of **kwds
        shape_keys.sort()
        return shape_cnt, tuple(shape_keys), shape_star, shape_stst # shape_keys are sorted

    def flatten(self):
        shape_cnt, shape_keys, shape_star, shape_stst = self._rawshape()
        data_w = self.arguments_w + [self.kwds_w[key] for key in shape_keys]
        if shape_star:
            data_w.append(self.w_stararg)
        if shape_stst:
            data_w.append(self.w_starstararg)
        return (shape_cnt, shape_keys, shape_star, shape_stst), data_w

def rawshape(args, nextra=0):
    return args._rawshape(nextra)


#
# ArgErr family of exceptions raised in case of argument mismatch.
# We try to give error messages following CPython's, which are very informative.
#

class ArgErr(Exception):
    
    def getmsg(self, fnname):
        raise NotImplementedError

class ArgErrCount(ArgErr):

    def __init__(self, nargs, nkwds, signature, defaults_w, missing_args):
        self.signature    = signature
        self.num_defaults = len(defaults_w)
        self.missing_args = missing_args
        self.num_args = nargs
        self.num_kwds = nkwds
        
    def getmsg(self, fnname):
        args = None
        num_args, has_vararg, has_kwarg = self.signature
        #args_w, kwds_w = args.unpack()
        if has_kwarg or (self.num_kwds and self.num_defaults):
            msg2 = "non-keyword "
            if self.missing_args:
                required_args = num_args - self.num_defaults
                nargs = required_args - self.missing_args
            else:
                nargs = self.num_args
        else:
            msg2 = ""
            nargs = self.num_args + self.num_kwds
        n = num_args
        if n == 0:
            msg = "%s() takes no %sargument (%d given)" % (
                fnname, 
                msg2,
                nargs)
        else:
            defcount = self.num_defaults
            if defcount == 0 and not has_vararg:
                msg1 = "exactly"
            elif not self.missing_args:
                msg1 = "at most"
            else:
                msg1 = "at least"
                n -= defcount
                if not self.num_kwds:  # msg "f() takes at least X non-keyword args"
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

    def getmsg(self, fnname):
        msg = "%s() got multiple values for keyword argument '%s'" % (
            fnname,
            self.argname)
        return msg

class ArgErrUnknownKwds(ArgErr):

    def __init__(self, kwds_w):
        self.kwd_name = ''
        self.num_kwds = len(kwds_w)
        if self.num_kwds == 1:
            self.kwd_name = kwds_w.keys()[0]

    def getmsg(self, fnname):
        if self.num_kwds == 1:
            msg = "%s() got an unexpected keyword argument '%s'" % (
                fnname,
                self.kwd_name)
        else:
            msg = "%s() got %d unexpected keyword arguments" % (
                fnname,
                self.num_kwds)
        return msg
