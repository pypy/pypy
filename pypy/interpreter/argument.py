"""
Arguments objects.
"""
from rpython.rlib.debug import make_sure_not_resized
from rpython.rlib import jit
from rpython.rlib.objectmodel import enforceargs
from rpython.rlib.rstring import StringBuilder

from pypy.interpreter.error import OperationError, oefmt


class Arguments(object):
    """
    Collects the arguments of a function call.

    Instances should be considered immutable.

    Some parts of this class are written in a slightly convoluted style to help
    the JIT. It is really crucial to get this right, because Python's argument
    semantics are complex, but calls occur everywhere.
    """

    ###  Construction  ###
    #@enforceargs(keywords=[unicode])
    def __init__(self, space, args_w, keywords=None, keywords_w=None,
                 w_stararg=None, w_starstararg=None, keyword_names_w=None,
                 methodcall=False):
        self.space = space
        assert isinstance(args_w, list)
        self.arguments_w = args_w
        self.keywords = keywords
        self.keywords_w = keywords_w
        self.keyword_names_w = keyword_names_w  # matches the tail of .keywords
        if keywords is not None:
            assert keywords_w is not None
            assert len(keywords_w) == len(keywords)
            assert (keyword_names_w is None or
                    len(keyword_names_w) <= len(keywords))
            make_sure_not_resized(self.keywords)
            make_sure_not_resized(self.keywords_w)

        make_sure_not_resized(self.arguments_w)
        self._combine_wrapped(w_stararg, w_starstararg)
        # a flag that specifies whether the JIT can unroll loops that operate
        # on the keywords
        self._jit_few_keywords = self.keywords is None or jit.isconstant(len(self.keywords))
        # a flag whether this is likely a method call, which doesn't change the
        # behaviour but produces better error messages
        self.methodcall = methodcall

    def __repr__(self):
        """ NOT_RPYTHON """
        name = self.__class__.__name__
        if not self.keywords:
            return '%s(%s)' % (name, self.arguments_w,)
        else:
            return '%s(%s, %s, %s)' % (name, self.arguments_w,
                                       self.keywords, self.keywords_w)


    ###  Manipulation  ###

    @jit.look_inside_iff(lambda self: self._jit_few_keywords)
    def unpack(self): # slowish
        "Return a ([w1,w2...], {'kw':w3...}) pair."
        kwds_w = {}
        if self.keywords:
            for i in range(len(self.keywords)):
                kwds_w[self.keywords[i]] = self.keywords_w[i]
        return self.arguments_w, kwds_w

    def replace_arguments(self, args_w):
        "Return a new Arguments with a args_w as positional arguments."
        return Arguments(self.space, args_w, self.keywords, self.keywords_w,
                         keyword_names_w = self.keyword_names_w)

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
        except OperationError as e:
            if (e.match(space, space.w_TypeError) and
                    not space.is_generator(w_stararg)):
                raise oefmt(space.w_TypeError,
                            "argument after * must be an iterable, not %T",
                            w_stararg)
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
        is_dict = False
        if space.isinstance_w(w_starstararg, space.w_dict):
            is_dict = True
            keys_w = space.unpackiterable(w_starstararg)
        else:
            try:
                w_keys = space.call_method(w_starstararg, "keys")
            except OperationError as e:
                if e.match(space, space.w_AttributeError):
                    raise oefmt(space.w_TypeError,
                                "argument after ** must be a mapping, not %T",
                                w_starstararg)
                raise
            keys_w = space.unpackiterable(w_keys)
        keywords_w = [None] * len(keys_w)
        keywords = [None] * len(keys_w)
        _do_combine_starstarargs_wrapped(
            space, keys_w, w_starstararg, keywords, keywords_w, self.keywords,
            is_dict)
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
            raise ValueError("no keyword arguments expected")
        if len(self.arguments_w) > argcount:
            raise ValueError("too many arguments (%d expected)" % argcount)
        elif len(self.arguments_w) < argcount:
            raise ValueError("not enough arguments (%d expected)" % argcount)
        return self.arguments_w

    def firstarg(self):
        "Return the first argument for inspection."
        if self.arguments_w:
            return self.arguments_w[0]
        return None

    ###  Parsing for function calls  ###

    @jit.unroll_safe
    def _match_signature(self, w_firstarg, scope_w, signature, defaults_w=None,
                         w_kw_defs=None, blindargs=0):
        """Parse args and kwargs according to the signature of a code object,
        or raise an ArgErr in case of failure.
        """
        #   w_firstarg = a first argument to be inserted (e.g. self) or None
        #   args_w = list of the normal actual parameters, wrapped
        #   scope_w = resulting list of wrapped values
        #

        # some comments about the JIT: it assumes that signature is a constant,
        # so all values coming from there can be assumed constant. It assumes
        # that the length of the defaults_w does not vary too much.
        co_argcount = signature.num_argnames() # expected formal arguments, without */**
        co_kwonlyargcount = signature.num_kwonlyargnames()
        too_many_args = False

        # put the special w_firstarg into the scope, if it exists
        if w_firstarg is not None:
            upfront = 1
            if co_argcount > 0:
                scope_w[0] = w_firstarg
        else:
            upfront = 0

        args_w = self.arguments_w
        num_args = len(args_w)
        avail = num_args + upfront

        keywords = self.keywords
        num_kwds = 0
        if keywords is not None:
            num_kwds = len(keywords)

        # put as many positional input arguments into place as available
        input_argcount = upfront
        if input_argcount < co_argcount:
            take = min(num_args, co_argcount - upfront)

            # letting the JIT unroll this loop is safe, because take is always
            # smaller than co_argcount
            for i in range(take):
                scope_w[i + input_argcount] = args_w[i]
            input_argcount += take

        # collect extra positional arguments into the *vararg
        if signature.has_vararg():
            args_left = co_argcount - upfront
            if args_left < 0:  # check required by rpython
                starargs_w = [w_firstarg]
                if num_args:
                    starargs_w = starargs_w + args_w
            elif num_args > args_left:
                starargs_w = args_w[args_left:]
            else:
                starargs_w = []
            loc = co_argcount + co_kwonlyargcount
            scope_w[loc] = self.space.newtuple(starargs_w)
        elif avail > co_argcount:
            too_many_args = True

        # if a **kwargs argument is needed, create the dict
        w_kwds = None
        if signature.has_kwarg():
            w_kwds = self.space.newdict(kwargs=True)
            scope_w[co_argcount + co_kwonlyargcount + signature.has_vararg()] = w_kwds

        # handle keyword arguments
        num_remainingkwds = 0
        keywords_w = self.keywords_w
        kwds_mapping = None
        if num_kwds:
            # kwds_mapping maps target indexes in the scope (minus input_argcount)
            # to positions in the keywords_w list
            kwds_mapping = [0] * (co_argcount + co_kwonlyargcount - input_argcount)
            # initialize manually, for the JIT :-(
            for i in range(len(kwds_mapping)):
                kwds_mapping[i] = -1
            # match the keywords given at the call site to the argument names
            # the called function takes
            # this function must not take a scope_w, to make the scope not
            # escape
            num_remainingkwds = _match_keywords(
                    signature, blindargs, input_argcount, keywords,
                    kwds_mapping, self._jit_few_keywords)
            if num_remainingkwds:
                if w_kwds is not None:
                    # collect extra keyword arguments into the **kwarg
                    _collect_keyword_args(
                            self.space, keywords, keywords_w, w_kwds,
                            kwds_mapping, self.keyword_names_w, self._jit_few_keywords)
                else:
                    raise ArgErrUnknownKwds(self.space, num_remainingkwds, keywords,
                                            kwds_mapping, self.keyword_names_w)

        # check for missing arguments and fill them from the kwds,
        # or with defaults, if available
        missing_positional = []
        missing_kwonly = []
        more_filling = (input_argcount < co_argcount + co_kwonlyargcount)
        def_first = 0
        if more_filling:
            def_first = co_argcount - (0 if defaults_w is None else len(defaults_w))
            j = 0
            kwds_index = -1
            # first, fill the arguments from the kwds
            for i in range(input_argcount, co_argcount + co_kwonlyargcount):
                if kwds_mapping is not None:
                    kwds_index = kwds_mapping[j]
                    j += 1
                    if kwds_index >= 0:
                        scope_w[i] = keywords_w[kwds_index]

        if too_many_args:
            kwonly_given = 0
            for i in range(co_argcount, co_argcount + co_kwonlyargcount):
                if scope_w[i] is not None:
                    kwonly_given += 1
            if self.methodcall:
                cls = ArgErrTooManyMethod
            else:
                cls = ArgErrTooMany
            raise cls(signature,
                                0 if defaults_w is None else len(defaults_w),
                                avail, kwonly_given)

        if more_filling:
            # then, fill the normal arguments with defaults_w (if needed)
            for i in range(input_argcount, co_argcount):
                if scope_w[i] is not None:
                    continue
                defnum = i - def_first
                if defnum >= 0:
                    scope_w[i] = defaults_w[defnum]
                else:
                    missing_positional.append(signature.argnames[i])

            # finally, fill kwonly arguments with w_kw_defs (if needed)
            for i in range(co_argcount, co_argcount + co_kwonlyargcount):
                if scope_w[i] is not None:
                    continue
                name = signature.kwonlyargnames[i - co_argcount]
                if w_kw_defs is None:
                    missing_kwonly.append(name)
                    continue
                w_def = self.space.finditem_str(w_kw_defs, name)
                if w_def is not None:
                    scope_w[i] = w_def
                else:
                    missing_kwonly.append(name)

        if missing_positional:
            raise ArgErrMissing(missing_positional, True)
        if missing_kwonly:
            raise ArgErrMissing(missing_kwonly, False)


    def parse_into_scope(self, w_firstarg,
                         scope_w, fnname, signature, defaults_w=None,
                         w_kw_defs=None):
        """Parse args and kwargs to initialize a frame
        according to the signature of code object.
        Store the argumentvalues into scope_w.
        scope_w must be big enough for signature.
        """
        try:
            self._match_signature(w_firstarg,
                                  scope_w, signature, defaults_w,
                                  w_kw_defs, 0)
        except ArgErr as e:
            raise oefmt(self.space.w_TypeError, "%s() %8", fnname, e.getmsg())
        return signature.scope_length()

    def _parse(self, w_firstarg, signature, defaults_w, w_kw_defs, blindargs=0):
        """Parse args and kwargs according to the signature of a code object,
        or raise an ArgErr in case of failure.
        """
        scopelen = signature.scope_length()
        scope_w = [None] * scopelen
        self._match_signature(w_firstarg, scope_w, signature, defaults_w,
                              w_kw_defs, blindargs)
        return scope_w


    def parse_obj(self, w_firstarg,
                  fnname, signature, defaults_w=None, w_kw_defs=None,
                  blindargs=0):
        """Parse args and kwargs to initialize a frame
        according to the signature of code object.
        """
        try:
            return self._parse(w_firstarg, signature, defaults_w, w_kw_defs,
                               blindargs)
        except ArgErr as e:
            raise oefmt(self.space.w_TypeError, "%s() %8", fnname, e.getmsg())

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
            limit = len(self.keywords)
            if self.keyword_names_w is not None:
                limit -= len(self.keyword_names_w)
            for i in range(len(self.keywords)):
                if i < limit:
                    key = self.keywords[i]
                    space.setitem_str(w_kwds, key, self.keywords_w[i])
                else:
                    w_key = self.keyword_names_w[i - limit]
                    space.setitem(w_kwds, w_key, self.keywords_w[i])
        return w_args, w_kwds

# JIT helper functions
# these functions contain functionality that the JIT is not always supposed to
# look at. They should not get a self arguments, which makes the amount of
# arguments annoying :-(

@jit.look_inside_iff(lambda space, existingkeywords, keywords, keywords_w:
        jit.isconstant(len(keywords) and
        jit.isconstant(existingkeywords)))
def _check_not_duplicate_kwargs(space, existingkeywords, keywords, keywords_w):
    # looks quadratic, but the JIT should remove all of it nicely.
    # Also, all the lists should be small
    for key in keywords:
        for otherkey in existingkeywords:
            if otherkey == key:
                raise oefmt(space.w_TypeError,
                            "got multiple values for keyword argument '%s'",
                            key)

def _do_combine_starstarargs_wrapped(space, keys_w, w_starstararg, keywords,
        keywords_w, existingkeywords, is_dict):
    i = 0
    for w_key in keys_w:
        try:
            key = space.identifier_w(w_key)
        except OperationError as e:
            if e.match(space, space.w_TypeError):
                raise oefmt(space.w_TypeError,
                            "keywords must be strings, not '%T'",
                            w_key)
            if e.match(space, space.w_UnicodeEncodeError):
                # Allow this to pass through
                key = None
            else:
                raise
        else:
            if existingkeywords and key in existingkeywords:
                raise oefmt(space.w_TypeError,
                            "got multiple values for keyword argument '%s'",
                            key)
        keywords[i] = key
        if is_dict:
            # issue 2435: bug-to-bug compatibility with cpython. for a subclass of
            # dict, just ignore the __getitem__ and access the underlying dict
            # directly
            from pypy.objspace.descroperation import dict_getitem
            w_descr = dict_getitem(space)
            w_value = space.get_and_call_function(w_descr, w_starstararg, w_key)
        else:
            w_value = space.getitem(w_starstararg, w_key)
        keywords_w[i] = w_value
        i += 1

@jit.look_inside_iff(
    lambda signature, blindargs, input_argcount,
           keywords, kwds_mapping, jiton: jiton)
def _match_keywords(signature, blindargs, input_argcount,
                    keywords, kwds_mapping, _):
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
        # if j == -1 nothing happens, because j < input_argcount and
        # blindargs > j
        if j < input_argcount:
            # check that no keyword argument conflicts with these. note
            # that for this purpose we ignore the first blindargs,
            # which were put into place by prepend().  This way,
            # keywords do not conflict with the hidden extra argument
            # bound by methods.
            if blindargs <= j:
                raise ArgErrMultipleValues(name)
        else:
            kwds_mapping[j - input_argcount] = i # map to the right index
            num_remainingkwds -= 1
    return num_remainingkwds

@jit.look_inside_iff(
    lambda space, keywords, keywords_w, w_kwds, kwds_mapping,
        keyword_names_w, jiton: jiton)
def _collect_keyword_args(space, keywords, keywords_w, w_kwds, kwds_mapping,
                          keyword_names_w, _):
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
                space.setitem_str(w_kwds, keywords[i], keywords_w[i])
            else:
                w_key = keyword_names_w[i - limit]
                space.setitem(w_kwds, w_key, keywords_w[i])

#
# ArgErr family of exceptions raised in case of argument mismatch.
# We try to give error messages following CPython's, which are very informative.
#

class ArgErr(Exception):

    def getmsg(self):
        raise NotImplementedError


class ArgErrMissing(ArgErr):
    def __init__(self, missing, positional):
        self.missing = missing
        self.positional = positional  # keyword-only otherwise

    def getmsg(self):
        arguments_str = StringBuilder()
        for i, arg in enumerate(self.missing):
            if i == 0:
                pass
            elif i == len(self.missing) - 1:
                if len(self.missing) == 2:
                    arguments_str.append(" and ")
                else:
                    arguments_str.append(", and ")
            else:
                arguments_str.append(", ")
            arguments_str.append("'%s'" % arg)
        msg = "missing %s required %s argument%s: %s" % (
            len(self.missing),
            "positional" if self.positional else "keyword-only",
            "s" if len(self.missing) != 1 else "",
            arguments_str.build())
        return msg


class ArgErrTooMany(ArgErr):
    def __init__(self, signature, num_defaults, given, kwonly_given):
        self.signature = signature
        self.num_defaults = num_defaults
        self.given = given
        self.kwonly_given = kwonly_given

    def getmsg(self):
        num_args = self.signature.num_argnames()
        num_defaults = self.num_defaults
        if num_defaults:
            takes_str = "from %d to %d positional arguments" % (
                num_args - num_defaults, num_args)
        else:
            takes_str = "%d positional argument%s" % (
                num_args, "s" if num_args != 1 else "")
        if self.kwonly_given:
            given_str = ("%s positional argument%s "
                         "(and %s keyword-only argument%s) were") % (
                self.given, "s" if self.given != 1 else "",
                self.kwonly_given, "s" if self.kwonly_given != 1 else "")
        else:
            given_str = "%s %s" % (
                self.given, "were" if self.given != 1 else "was")
        msg = "takes %s but %s given" % (takes_str, given_str)
        return msg

class ArgErrTooManyMethod(ArgErrTooMany):
    """ A subclass of ArgErrCount that is used if the argument matching is done
    as part of a method call, in which case more information is added to the
    error message, if the cause of the error is likely a forgotten `self`
    argument.
    """

    def getmsg(self):
        msg = ArgErrTooMany.getmsg(self)
        n = self.signature.num_argnames()
        if (self.given == n + 1 and
                (n == 0 or self.signature.argnames[0] != "self")):
            msg += ". Did you forget 'self' in the function definition?"
        return msg


class ArgErrMultipleValues(ArgErr):

    def __init__(self, argname):
        self.argname = argname

    def getmsg(self):
        msg = "got multiple values for argument '%s'" % self.argname
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
                            name = space.identifier_w(w_name)
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
