from pypy.interpreter.baseobjspace import OperationError


class FailedToImplement(Exception):
    "Signals the dispatcher to try harder."


# This file defines three major classes:
#
#   MultiMethod is the class you instanciate explicitely.
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

    class BASE_TYPE_OBJECT: pass

    def __init__(self, operatorsymbol, arity):
        self.arity = arity
        self.operatorsymbol = operatorsymbol
        self.dispatch_table = {}
        self.cache_table = {}

    def register(self, function, *types):
        # W_ANY can be used as a placeholder to dispatch on any value.
        functions = self.dispatch_table.setdefault(types, [])
        if function not in functions:
            functions.append(function)
            self.cache_table.clear()

    def buildchoices(self, allowedtypes):
        """Build a list of all possible implementations we can dispatch to,
        sorted best-first, ignoring delegation."""
        # 'types' is a tuple of tuples of classes, one tuple of classes per
        # argument. (Delegation needs to call buildchoice() with than one
        # class for a single argument.)
        try:
            result = self.cache_table[allowedtypes]  # try from the cache first
        except KeyError:
            result = self.cache_table[allowedtypes] = []
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
            for i, nexttype in zip(range(len(classtuple)), classtuple):
                self.internal_buildchoices(initialtypes,
                                           currenttypes + (nexttype,),
                                           result)

    def is_empty(self):
        return not self.dispatch_table


class MultiMethod(AbstractMultiMethod):

    def __init__(self, operatorsymbol, arity, specialnames=None, defaults=()):
        "MultiMethod dispatching on the first 'arity' arguments."
        AbstractMultiMethod.__init__(self, operatorsymbol, arity)
        if arity < 1:
            raise ValueError, "multimethods cannot dispatch on nothing"
        if specialnames is None:
            specialnames = [operatorsymbol]
        self.specialnames = specialnames  # e.g. ['__xxx__', '__rxxx__']
        self.defaults = defaults
        self.unbound_versions = {}

    def __get__(self, space, cls=object):
        if issubclass(cls, self.BASE_TYPE_OBJECT):
            return self.slice(cls).get(space)
        elif space is None:
            return self  # hack for "StdObjSpace.xyz" returning xyz
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
    
    def postprocessresult(self, allowedtypes, result):
        # add the Ellipsis catch-all delegator(s)
        for function in self.dispatch_table[Ellipsis,]:
            for t in allowedtypes[0]:
                result.append(((t,), function))
        
        # sort the results in priority order, and insert None marks
        # between jumps in the priority values. Higher priority values
        # first.
        by_priority = {} # classify delegators by priority
        for signature, function in result:
            assert hasattr(function, 'priority'), (
                "delegator function must have a priority")
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
        t = types[self.bound_position].statictype
        return t is self.typeclass

    def __get__(self, space, cls=None):
        if space is None:
            return self
        else:
            return BoundMultiMethod(space, self)

    get = __get__


class BoundMultiMethod:

    def __init__(self, space, multimethod):
        self.space = space
        self.multimethod = multimethod

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
        arity = self.multimethod.arity
        extraargs = args[arity:]

        # look for an exact match first
        firstfailure = None
        types = tuple([(a.__class__,) for a in args])
        choicelist = self.multimethod.buildchoices(types)
        for signature, function in choicelist:
            try:
                return function(self.space, *args)
            except FailedToImplement, e:
                # we got FailedToImplement, record the first such error
                firstfailure = firstfailure or e

        seen_functions = {}
        for signature, function in choicelist:
            seen_functions[function] = 1

        # proceed by expanding the last argument by delegation, step by step
        # until no longer possible, and then the previous argument, and so on.
        expanded_args = ()
        expanded_types = ()
        delegate  = self.space.delegate.multimethod

        for argi in range(arity-1, -1, -1):
            curtypes = types[argi] # growing tuple of types we can delegate to
            curobjs = {curtypes[0]: args[argi]} # maps them to actual objects
            args = args[:argi]   # initial segments of arguments before this one
            types = types[:argi] # same with types (no deleg tried on them yet)
            while 1:
                choicelist = delegate.buildchoices((curtypes,))
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
                        converted = function(self.space, curobjs[t])
                        if not isinstance(converted, list):
                            converted = [(converted.__class__, converted)]
                        for t, a in converted:
                            if t not in curobjs:
                                curtypes += (t,)
                                curobjs[t] = a
                                progress = True
                else:
                    if not progress:
                        break  # no progress, and delegators list exhausted

                # progress: try again to dispatch with this new set of types
                choicelist = self.multimethod.buildchoices(
                    types + (curtypes,) + expanded_types)
                for signature, function in choicelist:
                    if function not in seen_functions:
                        seen_functions[function] = 1
                        # collect arguments: arguments after position i...
                        tail = [expanded_args[j][signature[j]]
                                for j in range(argi+1-arity, 0)]  # nb. j<0
                        # argments before and up to position i...
                        newargs= args + (curobjs[signature[argi]],) + tuple(tail)
                        try:
                            return function(self.space, *newargs+extraargs)
                        except FailedToImplement, e:
                            # record the first FailedToImplement
                            firstfailure = firstfailure or e
                # end of while 1: try on delegating the same argument i

            # proceed to the next argument
            expanded_args = (curobjs,) + expanded_args
            expanded_types = (curtypes,) + expanded_types

        # complete exhaustion
        raise firstfailure or FailedToImplement()

    def is_empty(self):
        return self.multimethod.is_empty()


class error(Exception):
    "Thrown to you when you do something wrong with multimethods."
