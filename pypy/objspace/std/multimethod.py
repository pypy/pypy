from pypy.interpreter.baseobjspace import OperationError


class FailedToImplement(Exception):
    "Signals the dispatcher to try harder."

class W_ANY:
    "Catch-all in case multimethods don't find anything else."
    typedef = None


# This file defines three major classes:
#
#   MultiMethod is the class you instanciate explicitly.
#   It is essentially just a collection of registered functions.
#   If xxx is a MultiMethod, StdObjSpace.xxx is xxx again,
#   and space.xxx is a BoundMultiMethod.
#
#   BoundMultiMethod is a MultiMethod or UnboundMultiMethod which
#   has been found to a specific object space. It is obtained by
#   'space.xxx' or explicitely by calling 'xxx.get(space)'.
#
#   UnboundMultiMethod is a MultiMethod on which one argument
#   (typically the first one) has been restricted to be of some
#   statically known type. It is obtained by the syntax
#   W_XxxType.yyy, where W_XxxType is the static type class,
#   or explicitely by calling 'xxx.slice(typeclass, arg_position)'.
#   Its dispatch table is always a subset of the dispatch table of
#   the original MultiMethod; a new function registered in either
#   one may be automatically registered in the other one to keep
#   them in sync.


class AbstractMultiMethod(object):
    """Abstract base class for MultiMethod and UnboundMultiMethod
    i.e. the classes that are not bound to a specific space instance."""

    def __init__(self, operatorsymbol, arity):
        self.arity = arity
        self.operatorsymbol = operatorsymbol
        self.dispatch_table = {}
        self.cache_table = {}
        self.cache_delegator_key = None

    def __repr__(self):
        return '<%s %s>' % (self.__class__.__name__, self.operatorsymbol)

    def register(self, function, *types):
        functions = self.dispatch_table.setdefault(types, [])
        if function not in functions:
            functions.append(function)
            self.cache_table.clear()

    def compile_calllist(self, argclasses, delegate):
        """Compile a list of calls to try for the given classes of the
        arguments. Return a function that should be called with the
        actual arguments."""
        if delegate.key is not self.cache_delegator_key:
            self.cache_table.clear()
            self.cache_delegator_key = delegate.key
        try:
            return self.cache_table[argclasses]
        except KeyError:
            calllist = []
            self.internal_buildcalllist(argclasses, delegate, calllist)
            result = self.internal_compilecalllist(argclasses, calllist)
            self.cache_table[argclasses] = result
            return result

    def internal_compilecalllist(self, argclasses, calllist):
        source, glob = self.internal_sourcecalllist(argclasses, calllist)
        # compile the function
        exec source in glob
        return glob['do']

    def internal_sourcecalllist(self, argclasses, calllist):
        """Translate a call list into the source of a Python function
        which is optimized and doesn't do repeated conversions on the
        same arguments."""
        if len(calllist) == 1:
            fn, conversions = calllist[0]
            if conversions.count([]) == len(conversions):
                # no conversion, just calling a single function: return
                # that function directly
                return '', {'do': fn}
        
        #print '**** compile **** ', self.operatorsymbol, [
        #    t.__name__ for t in argclasses]
        arglist = ['a%d'%i for i in range(len(argclasses))] + ['*extraargs']
        source = ['def do(space,%s):' % ','.join(arglist)]
        converted = [{(): ('a%d'%i, False)} for i in range(len(argclasses))]

        def make_conversion(argi, convlist):
            if tuple(convlist) in converted[argi]:
                return converted[argi][tuple(convlist)]
            else:
                prev, can_fail = make_conversion(argi, convlist[:-1])
                new = '%s_%d' % (prev, len(converted[argi]))
                fname = all_functions.setdefault(convlist[-1],
                                                 'd%d' % len(all_functions))
                if can_fail:
                    source.append(' if isinstance(%s, FailedToImplement):' % prev)
                    source.append('  %s = %s' % (new, prev))
                    source.append(' else:')
                    indent = '  '
                else:
                    indent = ' '
                source.append('%s%s = %s(space,%s)' % (indent, new, fname, prev))
                can_fail = can_fail or getattr(convlist[-1], 'can_fail', False)
                converted[argi][tuple(convlist)] = new, can_fail
                return new, can_fail

        all_functions = {}
        has_firstfailure = False
        for fn, conversions in calllist:
            # make the required conversions
            fname = all_functions.setdefault(fn, 'f%d' % len(all_functions))
            arglist = []
            failcheck = []
            for i in range(len(argclasses)):
                argname, can_fail = make_conversion(i, conversions[i])
                arglist.append(argname)
                if can_fail:
                    failcheck.append(argname)
            arglist.append('*extraargs')
            source.append(    ' try:')
            for argname in failcheck:
                source.append('  if isinstance(%s, FailedToImplement):' % argname)
                source.append('   raise %s' % argname)
            source.append(    '  return %s(space,%s)' % (
                fname, ','.join(arglist)))
            if has_firstfailure:
                source.append(' except FailedToImplement:')
            else:
                source.append(' except FailedToImplement, firstfailure:')
                has_firstfailure = True
            source.append(    '  pass')

        # complete exhaustion
        if has_firstfailure:
            source.append(' raise firstfailure')
        else:
            source.append(' raise FailedToImplement()')
        source.append('')

        glob = {'FailedToImplement': FailedToImplement}
        for fn, fname in all_functions.items():
            glob[fname] = fn
        return '\n'.join(source), glob

    def internal_buildcalllist(self, argclasses, delegate, calllist):
        """Build a list of calls to try for the given classes of the
        arguments. The list contains 'calls' of the following form:
        (function-to-call, list-of-list-of-converters)
        The list of converters contains a list of converter functions per
        argument, with [] meaning that no conversion is needed for
        that argument."""
        # look for an exact match first
        arity = self.arity
        assert arity == len(argclasses)
        dispatchclasses = tuple([(c,) for c in argclasses])
        choicelist = self.buildchoices(dispatchclasses)
        seen_functions = {}
        no_conversion = [[]] * arity
        for signature, function in choicelist:
            calllist.append((function, no_conversion))
            seen_functions[function] = 1

        # proceed by expanding the last argument by delegation, step by step
        # until no longer possible, and then the previous argument, and so on.
        expanded_args = ()
        expanded_dispcls = ()

        for argi in range(arity-1, -1, -1):
            # growing tuple of dispatch classes we can delegate to
            curdispcls = dispatchclasses[argi]
            assert len(curdispcls) == 1
            # maps each dispatch class to a list of converters
            curargs = {curdispcls[0]: []}
            # reduce dispatchclasses to the arguments before this one
            # (on which no delegation has been tried yet)
            dispatchclasses = dispatchclasses[:argi]
            no_conversion = no_conversion[:argi]
            
            while 1:
                choicelist = delegate.buildchoices((curdispcls,))
                # the list is sorted by priority
                progress = False
                for (t,), function in choicelist:
                    if function is None:
                        # this marks a decrease in the priority.
                        # Don't try delegators with lower priority if
                        # we have already progressed.
                        if progress:
                            break
                    else:
                        assert hasattr(function, 'result_class'), (
                            "delegator %r must have a result_class" % function)
                        nt = function.result_class
                        if nt not in curargs:
                            curdispcls += (nt,)
                            srcconvs = curargs[t]
                            if not getattr(function, 'trivial_delegation',False):
                                srcconvs = srcconvs + [function]
                            curargs[nt] = srcconvs
                            progress = True
                else:
                    if not progress:
                        break  # no progress, and delegators list exhausted

                # progress: try again to dispatch with this new set of types
                choicelist = self.buildchoices(
                    dispatchclasses + (curdispcls,) + expanded_dispcls)
                for signature, function in choicelist:
                    if function not in seen_functions:
                        seen_functions[function] = 1
                        # collect arguments: arguments after position argi...
                        after_argi = [expanded_args[j][signature[j]]
                                      for j in range(argi+1-arity, 0)]  # nb. j<0
                        # collect arguments: argument argi...
                        arg_argi = curargs[signature[argi]]
                        # collect all arguments
                        newargs = no_conversion + [arg_argi] + after_argi
                        # record the call
                        calllist.append((function, newargs))
                # end of while 1: try on delegating the same argument i

            # proceed to the next argument
            expanded_args = (curargs,) + expanded_args
            expanded_dispcls = (curdispcls,) + expanded_dispcls

    def buildchoices(self, allowedtypes):
        """Build a list of all possible implementations we can dispatch to,
        sorted best-first, ignoring delegation."""
        # 'types' is a tuple of tuples of classes, one tuple of classes per
        # argument. (After delegation, we need to call buildchoice() with
        # more than one possible class for a single argument.)
        result = []
        self.internal_buildchoices(allowedtypes, (), result)
        self.postprocessresult(allowedtypes, result)
        #print self.operatorsymbol, allowedtypes, result
        # the result is a list a tuples (function, signature).
        return result

    def postprocessresult(self, allowedtypes, result):
        pass

    def internal_buildchoices(self, initialtypes, currenttypes, result):
        if len(currenttypes) == self.arity:
            for func in self.dispatch_table.get(currenttypes, []):
                if func not in result:   # ignore duplicates
                    result.append((currenttypes, func))
        else:
            classtuple = initialtypes[len(currenttypes)]
            for nexttype in classtuple:
                self.internal_buildchoices(initialtypes,
                                           currenttypes + (nexttype,),
                                           result)

    def is_empty(self):
        return not self.dispatch_table


class MultiMethod(AbstractMultiMethod):

    def __init__(self, operatorsymbol, arity, specialnames=None, **extras):
        "MultiMethod dispatching on the first 'arity' arguments."
        AbstractMultiMethod.__init__(self, operatorsymbol, arity)
        if arity < 1:
            raise ValueError, "multimethods cannot dispatch on nothing"
        if specialnames is None:
            specialnames = [operatorsymbol]
        self.specialnames = specialnames  # e.g. ['__xxx__', '__rxxx__']
        self.extras = extras
        self.unbound_versions = {}


    def __get__(self, space, cls=None):
        if space is None:
            return self
        else:
            return BoundMultiMethod(space, self)

    get = __get__

    def slice(self, typeclass, bound_position=0):
        try:
            return self.unbound_versions[typeclass, bound_position]
        except KeyError:
            m = UnboundMultiMethod(self, typeclass, bound_position)
            self.unbound_versions[typeclass, bound_position] = m
            return m

    def register(self, function, *types):
        AbstractMultiMethod.register(self, function, *types)
        # register the function is unbound versions that match
        for m in self.unbound_versions.values():
            if m.match(types):
                AbstractMultiMethod.register(m, function, *types)


class DelegateMultiMethod(MultiMethod):

    def __init__(self):
        MultiMethod.__init__(self, 'delegate', 1, [])
        self.key = object()

    def register(self, function, *types):
        AbstractMultiMethod.register(self, function, *types)
        self.key = object()   # change the key to force recomputation

    def postprocessresult(self, allowedtypes, result):
        # add delegation from a class to the *first* immediate parent class
        # and to W_ANY
        arg1types, = allowedtypes
        for t in arg1types:
            if t.__bases__:
                base = t.__bases__[0]
                def delegate_to_parent_class(space, a):
                    return a
                delegate_to_parent_class.trivial_delegation = True
                delegate_to_parent_class.result_class = base
                delegate_to_parent_class.priority = 0
                # hard-wire it at priority 0
                result.append(((t,), delegate_to_parent_class))

                def delegate_to_any(space, a):
                    return a
                delegate_to_any.trivial_delegation = True
                delegate_to_any.result_class = W_ANY
                delegate_to_any.priority = -999
                # hard-wire it at priority -999
                result.append(((t,), delegate_to_any))

        # sort the results in priority order, and insert None marks
        # between jumps in the priority values. Higher priority values
        # first.
        by_priority = {} # classify delegators by priority
        for signature, function in result:
            assert hasattr(function, 'priority'), (
                "delegator %r must have a priority" % function)
            sublist = by_priority.setdefault(function.priority, [])
            sublist.append((signature, function))
        delegators = by_priority.items()
        delegators.sort()
        delegators.reverse()
        del result[:]
        for priority, sublist in delegators:
            if result:
                result.append(((None,), None))
            result += sublist


class UnboundMultiMethod(AbstractMultiMethod):

    def __init__(self, basemultimethod, typeclass, bound_position=0):
        AbstractMultiMethod.__init__(self,
                                     basemultimethod.operatorsymbol,
                                     basemultimethod.arity)
        self.basemultimethod = basemultimethod
        self.typeclass = typeclass
        self.bound_position = bound_position
        # get all the already-registered matching functions from parent
        for types, functions in basemultimethod.dispatch_table.iteritems():
            if self.match(types):
                self.dispatch_table[types] = functions
        #print basemultimethod.operatorsymbol, typeclass, self.dispatch_table

    def register(self, function, *types):
        AbstractMultiMethod.register(self, function, *types)
        # propagate the function registeration to the base multimethod
        # and possibly other UnboundMultiMethods
        self.basemultimethod.register(function, *types)

    def match(self, types):
        # check if the 'types' signature statically corresponds to the
        # restriction of the present UnboundMultiMethod.
        # Only accept an exact match; having merely subclass should
        # be taken care of by the general look-up rules.
        t = types[self.bound_position].typedef
        return t is self.typeclass or (
            getattr(t, 'could_also_match', None) is self.typeclass)

    def __get__(self, space, cls=None):
        if space is None:
            return self
        else:
            return BoundMultiMethod(space, self)

    get = __get__


class BoundMultiMethod:
    ASSERT_BASE_TYPE = object

    def __init__(self, space, multimethod):
        self.space = space
        self.multimethod = multimethod

    def __eq__(self, other):
        return (self.__class__ == other.__class__ and
                self.space == other.space and
                self.multimethod == other.multimethod)

    def __ne__(self, other):
        return self != other

    def __hash__(self):
        return hash((self.__class__, self.space, self.multimethod))

    def __call__(self, *args):
        if len(args) < self.multimethod.arity:
            raise TypeError, ("multimethod needs at least %d arguments" %
                              self.multimethod.arity)
        try:
            return self.perform_call(args)
        except FailedToImplement, e:
            if e.args:
                raise OperationError(*e.args)
            else:
                # raise a TypeError for a FailedToImplement
                initialtypes = [a.__class__
                                for a in args[:self.multimethod.arity]]
                if len(initialtypes) <= 1:
                    plural = ""
                else:
                    plural = "s"
                debugtypenames = [t.__name__ for t in initialtypes]
                message = "unsupported operand type%s for %s (%s)" % (
                    plural, self.multimethod.operatorsymbol,
                    ', '.join(debugtypenames))
                w_value = self.space.wrap(message)
                raise OperationError(self.space.w_TypeError, w_value)

    def perform_call(self, args):
        for a in args:
            assert isinstance(a, self.ASSERT_BASE_TYPE), (
                "'%s' multimethod got a non-wrapped argument: %r" % (
                self.multimethod.operatorsymbol, a))
        arity = self.multimethod.arity
        argclasses = tuple([a.__class__ for a in args[:arity]])
        delegate = self.space.delegate.multimethod
        fn = self.multimethod.compile_calllist(argclasses, delegate)
        return fn(self.space, *args)

    def is_empty(self):
        return self.multimethod.is_empty()


class error(Exception):
    "Thrown to you when you do something wrong with multimethods."
