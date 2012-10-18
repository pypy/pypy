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

    @jit.elidable
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

    Some parts of this class are written in a slightly convoluted style to help
    the JIT. It is really crucial to get this right, because Python's argument
    semantics are complex, but calls occur everywhere.
    """

    ###  Construction  ###


    ###  Manipulation  ###

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
        keywords, values_w = space.view_as_kwargs(w_starstararg)
        if keywords is not None: # this path also taken for empty dicts
            if self.keywords is None:
                self.keywords = keywords
                self.keywords_w = values_w
            else:
                _check_not_duplicate_kwargs(
                    self.space, self.keywords, keywords, values_w)
                self.keywords = self.keywords + keywords
                self.keywords_w = self.keywords_w + values_w
            return
        if space.isinstance_w(w_starstararg, space.w_dict):
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
        keywords_w = [None] * len(keys_w)
        keywords = [None] * len(keys_w)
        _do_combine_starstarargs_wrapped(space, keys_w, w_starstararg, keywords, keywords_w, self.keywords)
        self.keyword_names_w = keys_w
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

    def topacked(self):
        """Express the Argument object as a pair of wrapped w_args, w_kwds."""
        space = self.space
        w_args = space.newtuple(self.arguments_w)
        w_kwds = space.newdict()
        if self.keywords is not None:
            limit = len(self.keywords)
            if self.keyword_names_w is not None:
                limit -= len(self.keyword_names_w)
            for i in range(len(self.keywords)):
                if i < limit:
                    w_key = space.wrap(self.keywords[i])
                else:
                    w_key = self.keyword_names_w[i - limit]
                space.setitem(w_kwds, w_key, self.keywords_w[i])
        return w_args, w_kwds

# JIT helper functions
# these functions contain functionality that the JIT is not always supposed to
# look at. They should not get a self arguments, which makes the amount of
# arguments annoying :-(

def _check_not_duplicate_kwargs(space, existingkeywords, keywords, keywords_w):
    # looks quadratic, but the JIT should remove all of it nicely.
    # Also, all the lists should be small
    for key in keywords:
        for otherkey in existingkeywords:
            if otherkey == key:
                raise operationerrfmt(space.w_TypeError,
                                      "got multiple values "
                                      "for keyword argument "
                                      "'%s'", key)

def _do_combine_starstarargs_wrapped(space, keys_w, w_starstararg, keywords,
        keywords_w, existingkeywords):
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
                # Allow this to pass through
                key = None
            else:
                raise
        else:
            if existingkeywords and key in existingkeywords:
                raise operationerrfmt(space.w_TypeError,
                                      "got multiple values "
                                      "for keyword argument "
                                      "'%s'", key)
        keywords[i] = key
        keywords_w[i] = space.getitem(w_starstararg, w_key)
        i += 1

def _match_keywords(signature, input_argcount, keywords, kwds_mapping):
    # letting JIT unroll the loop is *only* safe if the callsite didn't
    # use **args because num_kwds can be arbitrarily large otherwise.
    num_kwds = num_remainingkwds = len(keywords)
    for i in range(num_kwds):
        name = keywords[i]
        # If name was not encoded as a string, it could be None. In that
        # case, it's definitely not going to be in the signature.
        if name is None:
            continue
        j = signature.find_argname(name)
        # if j == -1 nothing happens
        if j < input_argcount:
            # check that no keyword argument conflicts with these.
            if j >= 0:
                raise ArgErrMultipleValues(name)
        else:
            kwds_mapping[j - input_argcount] = i # map to the right index
            num_remainingkwds -= 1
    return num_remainingkwds

def _collect_keyword_args(space, keywords, keywords_w, w_kwds, kwds_mapping,
                          keyword_names_w):
    limit = len(keywords)
    if keyword_names_w is not None:
        limit -= len(keyword_names_w)
    for i in range(len(keywords)):
        # again a dangerous-looking loop that either the JIT unrolls
        # or that is not too bad, because len(kwds_mapping) is small
        for j in kwds_mapping:
            if i == j:
                break
        else:
            if i < limit:
                w_key = space.wrap(keywords[i])
            else:
                w_key = keyword_names_w[i - limit]
            space.setitem(w_kwds, w_key, keywords_w[i])

class ArgumentsForTranslation(Arguments):
    def __init__(self, space, args_w, keywords=None, keywords_w=None,
                 w_stararg=None, w_starstararg=None):
        self.w_stararg = w_stararg
        self.w_starstararg = w_starstararg
        self.combine_has_happened = False
        self.space = space
        assert isinstance(args_w, list)
        self.arguments_w = args_w
        self.keywords = keywords
        self.keywords_w = keywords_w
        self.keyword_names_w = None

    def __repr__(self):
        """ NOT_RPYTHON """
        name = self.__class__.__name__
        if not self.keywords:
            return '%s(%s)' % (name, self.arguments_w,)
        else:
            return '%s(%s, %s, %s)' % (name, self.arguments_w,
                                       self.keywords, self.keywords_w)

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

    def _match_signature(self, scope_w, signature, defaults_w=None):
        """Parse args and kwargs according to the signature of a code object,
        or raise an ArgErr in case of failure.
        """
        #   args_w = list of the normal actual parameters, wrapped
        #   scope_w = resulting list of wrapped values
        #
        self.combine_if_necessary()
        co_argcount = signature.num_argnames() # expected formal arguments, without */**

        args_w = self.arguments_w
        num_args = len(args_w)
        keywords = self.keywords or []
        num_kwds = len(keywords)

        # put as many positional input arguments into place as available
        take = min(num_args, co_argcount)
        scope_w[:take] = args_w[:take]
        input_argcount = take

        # collect extra positional arguments into the *vararg
        if signature.has_vararg():
            if num_args > co_argcount:
                starargs_w = args_w[co_argcount:]
            else:
                starargs_w = []
            scope_w[co_argcount] = self.space.newtuple(starargs_w)
        elif num_args > co_argcount:
            raise ArgErrCount(num_args, num_kwds, signature, defaults_w, 0)

        # if a **kwargs argument is needed, create the dict
        w_kwds = None
        if signature.has_kwarg():
            w_kwds = self.space.newdict(kwargs=True)
            scope_w[co_argcount + signature.has_vararg()] = w_kwds

        # handle keyword arguments
        num_remainingkwds = 0
        keywords_w = self.keywords_w
        kwds_mapping = None
        if num_kwds:
            # kwds_mapping maps target indexes in the scope (minus input_argcount)
            # to positions in the keywords_w list
            kwds_mapping = [-1] * (co_argcount - input_argcount)
            # match the keywords given at the call site to the argument names
            # the called function takes
            # this function must not take a scope_w, to make the scope not
            # escape
            num_remainingkwds = _match_keywords(signature, input_argcount,
                    keywords, kwds_mapping)
            if num_remainingkwds:
                if w_kwds is not None:
                    # collect extra keyword arguments into the **kwarg
                    _collect_keyword_args(self.space, keywords, keywords_w,
                            w_kwds, kwds_mapping, self.keyword_names_w)
                else:
                    if co_argcount == 0:
                        raise ArgErrCount(num_args, num_kwds, signature, defaults_w, 0)
                    raise ArgErrUnknownKwds(self.space, num_remainingkwds, keywords,
                                            kwds_mapping, self.keyword_names_w)

        # check for missing arguments and fill them from the kwds,
        # or with defaults, if available
        missing = 0
        if input_argcount < co_argcount:
            def_first = co_argcount - (0 if defaults_w is None else len(defaults_w))
            j = 0
            kwds_index = -1
            for i in range(input_argcount, co_argcount):
                if kwds_mapping is not None:
                    kwds_index = kwds_mapping[j]
                    j += 1
                    if kwds_index >= 0:
                        scope_w[i] = keywords_w[kwds_index]
                        continue
                defnum = i - def_first
                if defnum >= 0:
                    scope_w[i] = defaults_w[defnum]
                else:
                    missing += 1
            if missing:
                raise ArgErrCount(num_args, num_kwds, signature, defaults_w, missing)

    def unpack(self):
        "Return a ([w1,w2...], {'kw':w3...}) pair."
        self.combine_if_necessary()
        kwds_w = {}
        if self.keywords:
            for i in range(len(self.keywords)):
                kwds_w[self.keywords[i]] = self.keywords_w[i]
        return self.arguments_w, kwds_w


    def match_signature(self, signature, defaults_w):
        """Parse args and kwargs according to the signature of a code object,
        or raise an ArgErr in case of failure.
        """
        scopelen = signature.scope_length()
        scope_w = [None] * scopelen
        self._match_signature(scope_w, signature, defaults_w)
        return scope_w

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

    def getmsg(self):
        raise NotImplementedError

class ArgErrCount(ArgErr):

    def __init__(self, got_nargs, nkwds, signature,
                 defaults_w, missing_args):
        self.signature = signature

        self.num_defaults = 0 if defaults_w is None else len(defaults_w)
        self.missing_args = missing_args
        self.num_args = got_nargs
        self.num_kwds = nkwds

    def getmsg(self):
        n = self.signature.num_argnames()
        if n == 0:
            msg = "takes no arguments (%d given)" % (
                self.num_args + self.num_kwds)
        else:
            defcount = self.num_defaults
            has_kwarg = self.signature.has_kwarg()
            num_args = self.num_args
            num_kwds = self.num_kwds
            if defcount == 0 and not self.signature.has_vararg():
                msg1 = "exactly"
                if not has_kwarg:
                    num_args += num_kwds
                    num_kwds = 0
            elif not self.missing_args:
                msg1 = "at most"
            else:
                msg1 = "at least"
                has_kwarg = False
                n -= defcount
            if n == 1:
                plural = ""
            else:
                plural = "s"
            if has_kwarg or num_kwds > 0:
                msg2 = " non-keyword"
            else:
                msg2 = ""
            msg = "takes %s %d%s argument%s (%d given)" % (
                msg1,
                n,
                msg2,
                plural,
                num_args)
        return msg

class ArgErrMultipleValues(ArgErr):

    def __init__(self, argname):
        self.argname = argname

    def getmsg(self):
        msg = "got multiple values for keyword argument '%s'" % (
            self.argname)
        return msg

class ArgErrUnknownKwds(ArgErr):

    def __init__(self, space, num_remainingkwds, keywords, kwds_mapping,
                 keyword_names_w):
        name = ''
        self.num_kwds = num_remainingkwds
        if num_remainingkwds == 1:
            for i in range(len(keywords)):
                if i not in kwds_mapping:
                    name = keywords[i]
                    if name is None:
                        # We'll assume it's unicode. Encode it.
                        # Careful, I *think* it should not be possible to
                        # get an IndexError here but you never know.
                        try:
                            if keyword_names_w is None:
                                raise IndexError
                            # note: negative-based indexing from the end
                            w_name = keyword_names_w[i - len(keywords)]
                        except IndexError:
                            name = '?'
                        else:
                            w_enc = space.wrap(space.sys.defaultencoding)
                            w_err = space.wrap("replace")
                            w_name = space.call_method(w_name, "encode", w_enc,
                                                       w_err)
                            name = space.str_w(w_name)
                    break
        self.kwd_name = name

    def getmsg(self):
        if self.num_kwds == 1:
            msg = "got an unexpected keyword argument '%s'" % (
                self.kwd_name)
        else:
            msg = "got %d unexpected keyword arguments" % (
                self.num_kwds)
        return msg
