"""
Arguments objects.
"""

from pypy.interpreter.error import OperationError, operationerrfmt
from pypy.rlib.debug import make_sure_not_resized
from pypy.rlib import jit


class Signature(object):
    _immutable_ = True
    _immutable_fields_ = ["argnames[*]"]
    __slots__ = ("argnames", "varargname", "kwargname")

    def __init__(self, argnames, varargname=None, kwargname=None):
        self.argnames = argnames
        self.varargname = varargname
        self.kwargname = kwargname

    @jit.purefunction
    def find_argname(self, name):
        try:
            return self.argnames.index(name)
        except ValueError:
            return -1

    def num_argnames(self):
        return len(self.argnames)

    def has_vararg(self):
        return self.varargname is not None

    def has_kwarg(self):
        return self.kwargname is not None

    def scope_length(self):
        scopelen = len(self.argnames)
        scopelen += self.has_vararg()
        scopelen += self.has_kwarg()
        return scopelen

    def getallvarnames(self):
        argnames = self.argnames
        if self.varargname is not None:
            argnames = argnames + [self.varargname]
        if self.kwargname is not None:
            argnames = argnames + [self.kwargname]
        return argnames

    def __repr__(self):
        return "Signature(%r, %r, %r)" % (
                self.argnames, self.varargname, self.kwargname)

    def __eq__(self, other):
        if not isinstance(other, Signature):
            return NotImplemented
        return (self.argnames == other.argnames and
                self.varargname == other.varargname and
                self.kwargname == other.kwargname)

    def __ne__(self, other):
        if not isinstance(other, Signature):
            return NotImplemented
        return not self == other


    # make it look tuply for its use in the annotator

    def __len__(self):
        return 3

    def __getitem__(self, i):
        if i == 0:
            return self.argnames
        if i == 1:
            return self.varargname
        if i == 2:
            return self.kwargname
        raise IndexError



class Arguments(object):
    """
    Collects the arguments of a function call.

    Instances should be considered immutable.
    """

    ###  Construction  ###

    def __init__(self, space, args_w, keywords=None, keywords_w=None,
                 w_stararg=None, w_starstararg=None):
        self.space = space
        assert isinstance(args_w, list)
        self.arguments_w = args_w
        self.keywords = keywords
        self.keywords_w = keywords_w
        if keywords is not None:
            assert keywords_w is not None
            assert len(keywords_w) == len(keywords)
            make_sure_not_resized(self.keywords)
            make_sure_not_resized(self.keywords_w)

        make_sure_not_resized(self.arguments_w)
        if w_stararg is not None:
            self._combine_starargs_wrapped(w_stararg)
        # if we have a call where **args are used at the callsite
        # we shouldn't let the JIT see the argument matching
        self._dont_jit = (w_starstararg is not None and
                          self._combine_starstarargs_wrapped(w_starstararg))

    def __repr__(self):
        """ NOT_RPYTHON """
        name = self.__class__.__name__
        if not self.keywords:
            return '%s(%s)' % (name, self.arguments_w,)
        else:
            return '%s(%s, %s, %s)' % (name, self.arguments_w,
                                       self.keywords, self.keywords_w)


    ###  Manipulation  ###

    def unpack(self): # slowish
        "Return a ([w1,w2...], {'kw':w3...}) pair."
        kwds_w = {}
        if self.keywords:
            for i in range(len(self.keywords)):
                kwds_w[self.keywords[i]] = self.keywords_w[i]
        return self.arguments_w, kwds_w

    def replace_arguments(self, args_w):
        "Return a new Arguments with a args_w as positional arguments."
        return Arguments(self.space, args_w, self.keywords, self.keywords_w)

    def prepend(self, w_firstarg):
        "Return a new Arguments with a new argument inserted first."
        return self.replace_arguments([w_firstarg] + self.arguments_w)

    def _combine_wrapped(self, w_stararg, w_starstararg):
        "unpack the *arg and **kwd into arguments_w and keywords_w"
        if w_stararg is not None:
            self._combine_starargs_wrapped(w_stararg)
        if w_starstararg is not None:
            self._combine_starstarargs_wrapped(w_starstararg)

    def _combine_starargs_wrapped(self, w_stararg):
        # unpack the * arguments
        space = self.space
        try:
            args_w = space.fixedview(w_stararg)
        except OperationError, e:
            if e.match(space, space.w_TypeError):
                w_type = space.type(w_stararg)
                typename = w_type.getname(space)
                raise OperationError(
                    space.w_TypeError,
                    space.wrap("argument after * must be "
                               "a sequence, not %s" % (typename,)))
            raise
        self.arguments_w = self.arguments_w + args_w

    def _combine_starstarargs_wrapped(self, w_starstararg):
        # unpack the ** arguments
        space = self.space
        if space.isinstance_w(w_starstararg, space.w_dict):
            if not space.is_true(w_starstararg):
                return False # don't call unpackiterable - it's jit-opaque
            keys_w = space.unpackiterable(w_starstararg)
        else:
            try:
                w_keys = space.call_method(w_starstararg, "keys")
            except OperationError, e:
                if e.match(space, space.w_AttributeError):
                    w_type = space.type(w_starstararg)
                    typename = w_type.getname(space)
                    raise OperationError(
                        space.w_TypeError,
                        space.wrap("argument after ** must be "
                                   "a mapping, not %s" % (typename,)))
                raise
            keys_w = space.unpackiterable(w_keys)
        if keys_w:
            self._do_combine_starstarargs_wrapped(keys_w, w_starstararg)
            return True
        else:
            return False    # empty dict; don't disable the JIT

    def _do_combine_starstarargs_wrapped(self, keys_w, w_starstararg):
        space = self.space
        keywords_w = [None] * len(keys_w)
        keywords = [None] * len(keys_w)
        i = 0
        for w_key in keys_w:
            try:
                key = space.str_w(w_key)
            except OperationError, e:
                if e.match(space, space.w_TypeError):
                    raise OperationError(
                        space.w_TypeError,
                        space.wrap("keywords must be strings"))
                if e.match(space, space.w_UnicodeEncodeError):
                    raise OperationError(
                        space.w_TypeError,
                        space.wrap("keyword cannot be encoded to ascii"))
                raise
            if self.keywords and key in self.keywords:
                raise operationerrfmt(self.space.w_TypeError,
                                      "got multiple values "
                                      "for keyword argument "
                                      "'%s'", key)
            keywords[i] = key
            keywords_w[i] = space.getitem(w_starstararg, w_key)
            i += 1
        if self.keywords is None:
            self.keywords = keywords
            self.keywords_w = keywords_w
        else:
            self.keywords = self.keywords + keywords
            self.keywords_w = self.keywords_w + keywords_w

    def fixedunpack(self, argcount):
        """The simplest argument parsing: get the 'argcount' arguments,
        or raise a real ValueError if the length is wrong."""
        if self.keywords:
            raise ValueError, "no keyword arguments expected"
        if len(self.arguments_w) > argcount:
            raise ValueError, "too many arguments (%d expected)" % argcount
        elif len(self.arguments_w) < argcount:
            raise ValueError, "not enough arguments (%d expected)" % argcount
        return self.arguments_w

    def firstarg(self):
        "Return the first argument for inspection."
        if self.arguments_w:
            return self.arguments_w[0]
        return None

    ###  Parsing for function calls  ###

    def _match_signature(self, w_firstarg, scope_w, signature, defaults_w=None,
                         blindargs=0):
        """Parse args and kwargs according to the signature of a code object,
        or raise an ArgErr in case of failure.
        Return the number of arguments filled in.
        """
        if jit.we_are_jitted() and self._dont_jit:
            return self._match_signature_jit_opaque(w_firstarg, scope_w,
                                                    signature, defaults_w,
                                                    blindargs)
        return self._really_match_signature(w_firstarg, scope_w, signature,
                                            defaults_w, blindargs)

    @jit.dont_look_inside
    def _match_signature_jit_opaque(self, w_firstarg, scope_w, signature,
                                    defaults_w, blindargs):
        return self._really_match_signature(w_firstarg, scope_w, signature,
                                            defaults_w, blindargs)

    @jit.unroll_safe
    def _really_match_signature(self, w_firstarg, scope_w, signature,
                                defaults_w=None, blindargs=0):
        #
        #   args_w = list of the normal actual parameters, wrapped
        #   kwds_w = real dictionary {'keyword': wrapped parameter}
        #   argnames = list of formal parameter names
        #   scope_w = resulting list of wrapped values
        #

        # some comments about the JIT: it assumes that signature is a constant,
        # so all values coming from there can be assumed constant. It assumes
        # that the length of the defaults_w does not vary too much.
        co_argcount = signature.num_argnames() # expected formal arguments, without */**
        has_vararg = signature.has_vararg()
        has_kwarg = signature.has_kwarg()
        extravarargs = None
        input_argcount =  0

        if w_firstarg is not None:
            upfront = 1
            if co_argcount > 0:
                scope_w[0] = w_firstarg
                input_argcount = 1
            else:
                extravarargs = [w_firstarg]
        else:
            upfront = 0

        args_w = self.arguments_w
        num_args = len(args_w)

        keywords = self.keywords
        keywords_w = self.keywords_w
        num_kwds = 0
        if keywords is not None:
            num_kwds = len(keywords)

        avail = num_args + upfront

        if input_argcount < co_argcount:
            # put as many positional input arguments into place as available
            if avail > co_argcount:
                take = co_argcount - input_argcount
            else:
                take = num_args

            # letting the JIT unroll this loop is safe, because take is always
            # smaller than co_argcount
            for i in range(take):
                scope_w[i + input_argcount] = args_w[i]
            input_argcount += take

        # collect extra positional arguments into the *vararg
        if has_vararg:
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
        elif avail > co_argcount:
            raise ArgErrCount(avail, num_kwds,
                              co_argcount, has_vararg, has_kwarg,
                              defaults_w, 0)

        # the code assumes that keywords can potentially be large, but that
        # argnames is typically not too large
        num_remainingkwds = num_kwds
        used_keywords = None
        if keywords:
            # letting JIT unroll the loop is *only* safe if the callsite didn't
            # use **args because num_kwds can be arbitrarily large otherwise.
            used_keywords = [False] * num_kwds
            for i in range(num_kwds):
                name = keywords[i]
                j = signature.find_argname(name)
                if j < 0:
                    continue
                elif j < input_argcount:
                    # check that no keyword argument conflicts with these. note
                    # that for this purpose we ignore the first blindargs,
                    # which were put into place by prepend().  This way,
                    # keywords do not conflict with the hidden extra argument
                    # bound by methods.
                    if blindargs <= j:
                        raise ArgErrMultipleValues(name)
                else:
                    assert scope_w[j] is None
                    scope_w[j] = keywords_w[i]
                    used_keywords[i] = True # mark as used
                    num_remainingkwds -= 1
        missing = 0
        if input_argcount < co_argcount:
            def_first = co_argcount - (0 if defaults_w is None else len(defaults_w))
            for i in range(input_argcount, co_argcount):
                if scope_w[i] is not None:
                    continue
                defnum = i - def_first
                if defnum >= 0:
                    scope_w[i] = defaults_w[defnum]
                else:
                    # error: not enough arguments.  Don't signal it immediately
                    # because it might be related to a problem with */** or
                    # keyword arguments, which will be checked for below.
                    missing += 1

        # collect extra keyword arguments into the **kwarg
        if has_kwarg:
            w_kwds = self.space.newdict()
            if num_remainingkwds:
                for i in range(len(keywords)):
                    if not used_keywords[i]:
                        key = keywords[i]
                        self.space.setitem(w_kwds, self.space.wrap(key), keywords_w[i])
            scope_w[co_argcount + has_vararg] = w_kwds
        elif num_remainingkwds:
            if co_argcount == 0:
                raise ArgErrCount(avail, num_kwds,
                              co_argcount, has_vararg, has_kwarg,
                              defaults_w, missing)
            raise ArgErrUnknownKwds(num_remainingkwds, keywords, used_keywords)

        if missing:
            raise ArgErrCount(avail, num_kwds,
                              co_argcount, has_vararg, has_kwarg,
                              defaults_w, missing)

        return co_argcount + has_vararg + has_kwarg



    def parse_into_scope(self, w_firstarg,
                         scope_w, fnname, signature, defaults_w=None):
        """Parse args and kwargs to initialize a frame
        according to the signature of code object.
        Store the argumentvalues into scope_w.
        scope_w must be big enough for signature.
        """
        try:
            return self._match_signature(w_firstarg,
                                         scope_w, signature, defaults_w, 0)
        except ArgErr, e:
            raise OperationError(self.space.w_TypeError,
                                 self.space.wrap(e.getmsg(fnname)))

    def _parse(self, w_firstarg, signature, defaults_w, blindargs=0):
        """Parse args and kwargs according to the signature of a code object,
        or raise an ArgErr in case of failure.
        """
        scopelen = signature.scope_length()
        scope_w = [None] * scopelen
        self._match_signature(w_firstarg, scope_w, signature, defaults_w,
                              blindargs)
        return scope_w


    def parse_obj(self, w_firstarg,
                  fnname, signature, defaults_w=None, blindargs=0):
        """Parse args and kwargs to initialize a frame
        according to the signature of code object.
        """
        try:
            return self._parse(w_firstarg, signature, defaults_w, blindargs)
        except ArgErr, e:
            raise OperationError(self.space.w_TypeError,
                                 self.space.wrap(e.getmsg(fnname)))

    @staticmethod
    def frompacked(space, w_args=None, w_kwds=None):
        """Convenience static method to build an Arguments
           from a wrapped sequence and a wrapped dictionary."""
        return Arguments(space, [], w_stararg=w_args, w_starstararg=w_kwds)

    def topacked(self):
        """Express the Argument object as a pair of wrapped w_args, w_kwds."""
        space = self.space
        w_args = space.newtuple(self.arguments_w)
        w_kwds = space.newdict()
        if self.keywords is not None:
            for i in range(len(self.keywords)):
                space.setitem(w_kwds, space.wrap(self.keywords[i]),
                                      self.keywords_w[i])
        return w_args, w_kwds

class ArgumentsForTranslation(Arguments):
    def __init__(self, space, args_w, keywords=None, keywords_w=None,
                 w_stararg=None, w_starstararg=None):
        self.w_stararg = w_stararg
        self.w_starstararg = w_starstararg
        self.combine_has_happened = False
        Arguments.__init__(self, space, args_w, keywords, keywords_w)

    def combine_if_necessary(self):
        if self.combine_has_happened:
            return
        self._combine_wrapped(self.w_stararg, self.w_starstararg)
        self.combine_has_happened = True

    def prepend(self, w_firstarg): # used often
        "Return a new Arguments with a new argument inserted first."
        return ArgumentsForTranslation(self.space, [w_firstarg] + self.arguments_w,
                                       self.keywords, self.keywords_w, self.w_stararg,
                                       self.w_starstararg)

    def copy(self):
        return ArgumentsForTranslation(self.space, self.arguments_w,
                                       self.keywords, self.keywords_w, self.w_stararg,
                                       self.w_starstararg)



    def _match_signature(self, w_firstarg, scope_w, signature, defaults_w=None,
                         blindargs=0):
        self.combine_if_necessary()
        # _match_signature is destructive
        return Arguments._match_signature(
               self, w_firstarg, scope_w, signature,
               defaults_w, blindargs)

    def unpack(self):
        self.combine_if_necessary()
        return Arguments.unpack(self)

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

        keywords = []
        keywords_w = []
        for key in need_kwds:
            keywords.append(key)
            keywords_w.append(unfiltered_kwds_w[key])

        return ArgumentsForTranslation(self.space, args_w, keywords, keywords_w)

    @staticmethod
    def frompacked(space, w_args=None, w_kwds=None):
        raise NotImplementedError("go away")

    @staticmethod
    def fromshape(space, (shape_cnt,shape_keys,shape_star,shape_stst), data_w):
        args_w = data_w[:shape_cnt]
        p = end_keys = shape_cnt + len(shape_keys)
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
        return ArgumentsForTranslation(space, args_w, list(shape_keys),
                                       data_w[shape_cnt:end_keys], w_star,
                                       w_starstar)

    def flatten(self):
        """ Argument <-> list of w_objects together with "shape" information """
        shape_cnt, shape_keys, shape_star, shape_stst = self._rawshape()
        data_w = self.arguments_w + [self.keywords_w[self.keywords.index(key)]
                                         for key in shape_keys]
        if shape_star:
            data_w.append(self.w_stararg)
        if shape_stst:
            data_w.append(self.w_starstararg)
        return (shape_cnt, shape_keys, shape_star, shape_stst), data_w

    def _rawshape(self, nextra=0):
        assert not self.combine_has_happened
        shape_cnt  = len(self.arguments_w)+nextra        # Number of positional args
        if self.keywords:
            shape_keys = self.keywords[:]                # List of keywords (strings)
            shape_keys.sort()
        else:
            shape_keys = []
        shape_star = self.w_stararg is not None   # Flag: presence of *arg
        shape_stst = self.w_starstararg is not None # Flag: presence of **kwds
        return shape_cnt, tuple(shape_keys), shape_star, shape_stst # shape_keys are sorted

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

    def __init__(self, got_nargs, nkwds, expected_nargs, has_vararg, has_kwarg,
                 defaults_w, missing_args):
        self.expected_nargs = expected_nargs
        self.has_vararg = has_vararg
        self.has_kwarg = has_kwarg

        self.num_defaults = 0 if defaults_w is None else len(defaults_w)
        self.missing_args = missing_args
        self.num_args = got_nargs
        self.num_kwds = nkwds

    def getmsg(self, fnname):
        n = self.expected_nargs
        if n == 0:
            msg = "%s() takes no arguments (%d given)" % (
                fnname,
                self.num_args + self.num_kwds)
        else:
            defcount = self.num_defaults
            if defcount == 0 and not self.has_vararg:
                msg1 = "exactly"
            elif not self.missing_args:
                msg1 = "at most"
            else:
                msg1 = "at least"
                n -= defcount
            if n == 1:
                plural = ""
            else:
                plural = "s"
            if self.has_kwarg or self.num_kwds > 0:
                msg2 = " non-keyword"
            else:
                msg2 = ""
            msg = "%s() takes %s %d%s argument%s (%d given)" % (
                fnname,
                msg1,
                n,
                msg2,
                plural,
                self.num_args)
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

    def __init__(self, num_remainingkwds, keywords, used_keywords):
        self.kwd_name = ''
        self.num_kwds = num_remainingkwds
        if num_remainingkwds == 1:
            for i in range(len(keywords)):
                if not used_keywords[i]:
                    self.kwd_name = keywords[i]
                    break

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
