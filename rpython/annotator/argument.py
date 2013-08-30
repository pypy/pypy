"""
Arguments objects.
"""
from rpython.annotator.model import SomeTuple, SomeObject

# for parsing call arguments
class RPythonCallsSpace(object):
    """Pseudo Object Space providing almost no real operation.
    For the Arguments class: if it really needs other operations, it means
    that the call pattern is too complex for R-Python.
    """
    def newtuple(self, items_s):
        if len(items_s) == 1 and items_s[0] is Ellipsis:
            res = SomeObject()   # hack to get a SomeObject as the *arg
            res.from_ellipsis = True
            return res
        else:
            return SomeTuple(items_s)

    def unpackiterable(self, s_obj, expected_length=None):
        if isinstance(s_obj, SomeTuple):
            return list(s_obj.items)
        if (s_obj.__class__ is SomeObject and
            getattr(s_obj, 'from_ellipsis', False)):    # see newtuple()
            return [Ellipsis]
        raise CallPatternTooComplex("'*' argument must be SomeTuple")

    def bool(self, s_tup):
        assert isinstance(s_tup, SomeTuple)
        return bool(s_tup.items)


class CallPatternTooComplex(Exception):
    pass


class ArgumentsForTranslation(object):
    w_starstararg = None
    def __init__(self, space, args_w, keywords=None, keywords_w=None,
                 w_stararg=None, w_starstararg=None):
        self.w_stararg = w_stararg
        assert w_starstararg is None
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

    @property
    def positional_args(self):
        if self.w_stararg is not None:
            args_w = self.space.unpackiterable(self.w_stararg)
            return self.arguments_w + args_w
        else:
            return self.arguments_w

    def fixedunpack(self, argcount):
        """The simplest argument parsing: get the 'argcount' arguments,
        or raise a real ValueError if the length is wrong."""
        if self.keywords:
            raise ValueError("no keyword arguments expected")
        if len(self.arguments_w) > argcount:
            raise ValueError("too many arguments (%d expected)" % argcount)
        elif len(self.arguments_w) < argcount:
            raise ValueError("not enough arguments (%d expected)" % argcount)
        return self.arguments_w

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
        co_argcount = signature.num_argnames() # expected formal arguments, without */**

        args_w = self.positional_args
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

        assert not signature.has_kwarg() # XXX should not happen?

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
            num_remainingkwds = len(keywords)
            for i, name in enumerate(keywords):
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

            if num_remainingkwds:
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
        kwds_w = dict(zip(self.keywords, self.keywords_w)) if self.keywords else {}
        return self.positional_args, kwds_w

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
        need_cnt = len(self.positional_args)
        need_kwds = self.keywords or []
        space = self.space
        argnames, varargname, kwargname = signature
        assert kwargname is None
        cnt = len(argnames)
        data_args_w = data_w[:cnt]
        if varargname:
            data_w_stararg = data_w[cnt]
            cnt += 1
        else:
            data_w_stararg = space.newtuple([])
        assert len(data_w) == cnt

        unfiltered_kwds_w = {}
        if len(data_args_w) >= need_cnt:
            args_w = data_args_w[:need_cnt]
            for argname, w_arg in zip(argnames[need_cnt:], data_args_w[need_cnt:]):
                unfiltered_kwds_w[argname] = w_arg
            assert not space.bool(data_w_stararg)
        else:
            stararg_w = space.unpackiterable(data_w_stararg)
            args_w = data_args_w + stararg_w
            assert len(args_w) == need_cnt

        keywords = []
        keywords_w = []
        for key in need_kwds:
            keywords.append(key)
            keywords_w.append(unfiltered_kwds_w[key])

        return ArgumentsForTranslation(self.space, args_w, keywords, keywords_w)

    @staticmethod
    def fromshape(space, (shape_cnt, shape_keys, shape_star, shape_stst), data_w):
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
        shape_cnt = len(self.arguments_w) + nextra       # Number of positional args
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
