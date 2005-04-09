
from pypy.tool.compile import compile2

class FailedToImplement(Exception):
    def __init__(self, w_type=None, w_value=None):
        self.w_type  = w_type
        self.w_value = w_value


def raiseFailedToImplement():
    raise FailedToImplement


class MultiMethodTable:

    def __init__(self, arity, root_class, argnames_before=[], argnames_after=[]):
        """NOT_RPYTHON: cannot create new multimethods dynamically.
        MultiMethod-maker dispatching on exactly 'arity' arguments.
        """
        if arity < 1:
            raise ValueError, "multimethods cannot dispatch on nothing"
        self.arity = arity
        self.root_class = root_class
        self.dispatch_tree = {}
        self.argnames_before = argnames_before
        self.argnames_after = argnames_after

    def register(self, function, *types, **kwds):
        assert len(types) == self.arity
        assert kwds.keys() == [] or kwds.keys() == ['order']
        order = kwds.get('order', 0)
        node = self.dispatch_tree
        for type in types[:-1]:
            node = node.setdefault(type, {})
        lst = node.setdefault(types[-1], [])
        if order >= len(lst):
            lst += [None] * (order+1 - len(lst))
        assert lst[order] is None, "duplicate function for %r@%d" % (
            types, order)
        lst[order] = function

    def install(self, prefix, list_of_typeorders, baked_perform_call=True):
        "NOT_RPYTHON: initialization-time only"
        assert len(list_of_typeorders) == self.arity
        installer = Installer(self, prefix, list_of_typeorders,
                              baked_perform_call=baked_perform_call)
        return installer.install()

    def install_if_not_empty(self, prefix, list_of_typeorders):
        "NOT_RPYTHON: initialization-time only"
        assert len(list_of_typeorders) == self.arity
        installer = Installer(self, prefix, list_of_typeorders)
        if installer.is_empty():
            return None
        else:
            return installer.install()        
        
    

    # ____________________________________________________________
    # limited dict-like interface to the dispatch table

    def getfunctions(self, types):
        assert len(types) == self.arity
        node = self.dispatch_tree
        for type in types:
            node = node[type]
        return [fn for fn in node if fn is not None]

    def has_signature(self, types):
        try:
            self.getfunctions(types)
        except KeyError:
            return False
        else:
            return True

    def signatures(self):
        """NOT_RPYTHON"""
        result = []
        def enum_keys(types_so_far, node):
            for type, subnode in node.items():
                next_types = types_so_far+(type,)
                if isinstance(subnode, dict):
                    enum_keys(next_types, subnode)
                else:
                    assert len(next_types) == self.arity
                    result.append(next_types)
        enum_keys((), self.dispatch_tree)
        return result


# ____________________________________________________________

class Installer:
    mmfunccache = {}

    prefix_memo = {}

    def __init__(self, multimethod, prefix, list_of_typeorders, baked_perform_call=True):
        self.multimethod = multimethod
        # avoid prefix clashes, user code should supply different prefixes
        # itself for nice names in tracebacks
        n = 1
        while prefix in self.prefix_memo:
            n += 1
            prefix = "%s%d" % (prefix,n)
        self.prefix = prefix
        self.prefix_memo[prefix] = 1
        self.list_of_typeorders = list_of_typeorders
        self.subtree_cache = {}
        self.to_install = []
        self.non_empty = self.build_tree([], multimethod.dispatch_tree)

        self.baked_perform_call = baked_perform_call
        
        if self.non_empty:
            perform = [(None, prefix, 0)]
        else:
            perform = []

        self.perform_call = self.build_function(None, prefix+'_perform_call',
                                                None, perform)

    def is_empty(self):
        return not self.non_empty

    def install(self):
        #f = open('LOGFILE', 'a')
        #print >> f, '_'*60
        #import pprint
        #pprint.pprint(self.list_of_typeorders, f)
        for target, funcname, func, source, fallback in self.to_install:
            if target is not None:
                if hasattr(target, funcname) and fallback:
                    continue
                #print >> f, target.__name__, funcname
                #if source:
                #    print >> f, source
                #else:
                #    print >> f, '*\n'
                setattr(target, funcname, func)
        #f.close()
        return self.perform_call

    def build_tree(self, types_so_far, dispatch_node):
        key = tuple(types_so_far)
        if key in self.subtree_cache:
            return self.subtree_cache[key]
        non_empty = False
        typeorder = self.list_of_typeorders[len(types_so_far)]
        for next_type in typeorder:
            if self.build_single_method(typeorder, types_so_far, next_type,
                                        dispatch_node):
                non_empty = True
        self.subtree_cache[key] = non_empty
        return non_empty

    def build_single_method(self, typeorder, types_so_far, next_type,
                            dispatch_node):
        funcname = '__'.join([self.prefix] + [t.__name__ for t in types_so_far])

        order = typeorder[next_type]
        #order = [(next_type, None)] + order

        things_to_call = []
        for type, conversion in order:
            if type not in dispatch_node:
                # there is no possible completion of types_so_far+[type]
                # that could lead to a registered function.
                continue
            match = dispatch_node[type]
            if isinstance(match, dict):
                if self.build_tree(types_so_far+[type], match):
                    call = funcname + '__' + type.__name__
                    call_selfarg_index = len(types_so_far) + 1
                    things_to_call.append((conversion, call,
                                           call_selfarg_index))
            else:
                for func in match:   # list of functions
                    if func is not None:
                        things_to_call.append((conversion, func, None))

        if things_to_call:
            funcname = intern(funcname)
            self.build_function(next_type, funcname, len(types_so_far),
                                things_to_call)
            return True
        else:
            return False

    def build_function(self, target, funcname, func_selfarg_index,
                       things_to_call):
        # support for inventing names for the entries in things_to_call
        # which are real function objects instead of strings
        miniglobals = {'FailedToImplement': FailedToImplement}
        def invent_name(obj):
            if isinstance(obj, str):
                return obj
            name = obj.__name__
            n = 1
            while name in miniglobals:
                n += 1
                name = '%s%d' % (obj.__name__, n)
            miniglobals[name] = obj
            return name

        funcargs = ['arg%d' % i for i in range(self.multimethod.arity)]

        bodylines = []
        for conversion, call, call_selfarg_index in things_to_call:
            callargs = funcargs[:]
            if conversion is not None:
                to_convert = func_selfarg_index
                callargs[to_convert] = '%s(%s)' % (
                    invent_name(conversion), callargs[to_convert])
            callname = invent_name(call)
            if call_selfarg_index is not None:
                # fallback on root_class
                self.build_function(self.multimethod.root_class,
                                    callname, call_selfarg_index, [])
                callname = '%s.%s' % (callargs.pop(call_selfarg_index), callname)
            callargs = (self.multimethod.argnames_before +
                        callargs + self.multimethod.argnames_after)
            bodylines.append('return %s(%s)' % (callname, ', '.join(callargs)))

        fallback = False
        if not bodylines:
            miniglobals['raiseFailedToImplement'] = raiseFailedToImplement
            bodylines = ['return raiseFailedToImplement()']
            fallback = True


        # protect all lines apart from the last one by a try:except:
        for i in range(len(bodylines)-2, -1, -1):
            bodylines[i:i+1] = ['try:',
                                '    ' + bodylines[i],
                                'except FailedToImplement:',
                                '    pass']

        if func_selfarg_index is not None:
            selfargs = [funcargs.pop(func_selfarg_index)]
        else:
            selfargs = []
        funcargs = (selfargs + self.multimethod.argnames_before +
                    funcargs + self.multimethod.argnames_after)

        if target is None and not self.baked_perform_call:
            return funcargs, bodylines[0][len('return '):], miniglobals, fallback

        # indent mode
        bodylines = ['    ' + line for line in bodylines]

        bodylines.insert(0, 'def %s(%s):' % (funcname, ', '.join(funcargs)))
        bodylines.append('')
        source = '\n'.join(bodylines)

        # XXX find a better place (or way) to avoid duplicate functions 
        l = miniglobals.items()
        l.sort()
        l = tuple(l)
        key = (source, l)
        try: 
            func = self.mmfunccache[key]
        except KeyError: 
            exec compile2(source) in miniglobals
            func = miniglobals[funcname]
            self.mmfunccache[key] = func 
        #else: 
        #    print "avoided duplicate function", func
        self.to_install.append((target, funcname, func, source, fallback))
        return func
