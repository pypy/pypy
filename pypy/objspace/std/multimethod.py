from pypy.interpreter.baseobjspace import OperationError


class FailedToImplement(Exception):
    "Signals the dispatcher to try harder."


class MultiMethod(object):

    ASSERT_BASE_TYPE = None

    def __init__(self, operatorsymbol, arity, specialnames=None, defaults=()):
        "MultiMethod dispatching on the first 'arity' arguments."
        self.arity = arity
        self.operatorsymbol = operatorsymbol
        self.dispatch_table = {}
        if specialnames is None:
            specialnames = [operatorsymbol]
        self.specialnames = specialnames  # list like ['__xxx__', '__rxxx__']
        self.defaults = defaults
        self.cache_dependencies = {}
        self.cache_table = {}

    def register(self, function, *types):
        # W_ANY can be used as a placeholder to dispatch on any value.
        if types in self.dispatch_table:
            raise error, "we already got an implementation for %r %r" % (
                self.operatorsymbol, types)
        self.dispatch_table[types] = function
        # clear caches
        self.cache_table.clear()
        for cache in self.cache_dependencies:
            cache.cleardependency()
        self.cache_dependencies.clear()

    def __get__(self, space, cls):
        if space is None:
            return self  # <-------------------------- Hack
        return BoundMultiMethod(space, self)

    def cache_dependency(self, cache):
        self.cache_dependencies[cache] = 1

    def buildchoices(self, types):
        """Build a list of all possible combinations of delegated types,
        sorted by cost."""
        try:
            result = self.cache_table[types]  # try from the cache first
        except KeyError:
            result = self.cache_table[types] = []
            self.internal_buildchoices(types, (), (), result)
            # the result is sorted by costs by construction.
            # it is a list of (delegator, function) pairs.
        return result

    def internal_buildchoices(self, initialtypes, currenttypes,
                              currentdelegators, result):
        if len(currenttypes) == self.arity:
            try:
                function = self.dispatch_table[currenttypes]
            except KeyError:
                pass
            else:
                newentry = (currentdelegators, function)
                if newentry not in result:      # don't add duplicates
                    result.append(newentry)
        else:
            nexttype = initialtypes[len(currenttypes)]
            delegators = {}
            while 1:
                self.internal_buildchoices(initialtypes,
                                           currenttypes + (nexttype,),
                                           currentdelegators + (None,), result)
                #assert "delegate_once" in nexttype.__dict__, (
                #    "you must call registerimplementation() to initialize %r" %
                #    nexttype)
                if "delegate_once" in nexttype.__dict__:
                    for key, value in nexttype.__dict__["delegate_once"].items():
                        if key not in delegators:
                            delegators[key] = value
                # before general delegation, try superclasses
                if not nexttype.__bases__:
                    # debugging assertion
                    if self.ASSERT_BASE_TYPE:
                        assert nexttype is self.ASSERT_BASE_TYPE, (
                            "calling a multimethod with an argument "
                            "which is not wrapped")
                    break
                nexttype, = nexttype.__bases__ # no multiple inheritance pleeease
            for othertype, delegator in delegators.items():
                self.internal_buildchoices(initialtypes,
                                           currenttypes + (othertype,),
                                           currentdelegators + (delegator,),
                                           result)

    def slicetable(self, position, slicetype):
        m = MultiMethod(self.operatorsymbol, self.arity, self.specialnames)
        for key, value in self.dispatch_table.iteritems():
            if slicetype.acceptclass(key[position]):
                m.dispatch_table[key] = value
        return m

    def is_empty(self):
        return not self.dispatch_table


class BoundMultiMethod:

    def __init__(self, space, multimethod):
        self.space = space
        self.multimethod = multimethod

    def __call__(self, *args):
        if len(args) < self.multimethod.arity:
            raise TypeError, ("multimethod needs at least %d arguments" %
                              self.multimethod.arity)
        dispatchargs = args[:self.multimethod.arity]
        initialtypes = tuple([a.__class__ for a in dispatchargs])
        try:
            return self.perform_call(args, initialtypes)
        except FailedToImplement, e:
            if e.args:
                raise OperationError(*e.args)
            else:
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

    def perform_call(self, args, initialtypes, prepend_space_argument=True):
        extraargs = args[self.multimethod.arity:]
        choicelist = self.multimethod.buildchoices(initialtypes)
        firstfailure = None
        for delegators, function in choicelist:
            newargs = []
            for delegator, arg in zip(delegators, args):
                if delegator is not None:
                    arg = delegator(self.space, arg)
                newargs.append(arg)
            newargs = tuple(newargs) + extraargs
            # XXX 'prepend_space_argument' should now always be True anyway
            if prepend_space_argument:
                newargs = (self.space,) + newargs
            try:
                return function(*newargs)
            except FailedToImplement, e:
                # we got FailedToImplement, record the first such error
                if firstfailure is None:
                    firstfailure = e
        raise firstfailure or FailedToImplement()

    def is_empty(self):
        return self.multimethod.is_empty()


class error(Exception):
    "Thrown to you when you do something wrong with multimethods."
