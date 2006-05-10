
from pypy.tool.sourcetools import compile2

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
        self.argnames_before = list(argnames_before)
        self.argnames_after = list(argnames_after)

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
# Installer version 1

class InstallerVersion1:
    """NOT_RPYTHON"""

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
                convert_callargs = (self.multimethod.argnames_before +
                                    [callargs[to_convert]])
                callargs[to_convert] = '%s(%s)' % (
                    invent_name(conversion), ', '.join(convert_callargs))
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

# ____________________________________________________________
# Installer version 2

class MMDispatcher:
    """NOT_RPYTHON
    Explicit dispatcher class.  This is not used in normal execution, which
    uses the complex Installer below to install single-dispatch methods to
    achieve the same result.  The MMDispatcher is only used by
    rpython.lltypesystem.rmultimethod.  It is also nice for documentation.
    """
    def __init__(self, multimethod, list_of_typeorders):
        self.multimethod = multimethod
        self.list_of_typeorders = list_of_typeorders

    def __call__(self, *args):
        # for testing only: this is slow
        i = len(self.multimethod.argnames_before)
        j = i + self.multimethod.arity
        k = j + len(self.multimethod.argnames_after)
        assert len(args) == k
        prefixargs = args[:i]
        dispatchargs = args[i:j]
        suffixargs = args[j:]
        return self.dispatch([x.__class__ for x in dispatchargs],
                             prefixargs,
                             dispatchargs,
                             suffixargs)

    def dispatch(self, argtypes, prefixargs, args, suffixargs):
        # for testing only: this is slow
        def expr(v):
            if isinstance(v, Call):
                return v.function(*[expr(w) for w in v.arguments])
            else:
                return v
        e = None
        for v in self.expressions(argtypes, prefixargs, args, suffixargs):
            try:
                return expr(v)
            except FailedToImplement, e:
                pass
        else:
            raise e or FailedToImplement()

    def expressions(self, argtypes, prefixargs, args, suffixargs):
        """Lists the possible expressions that call the appropriate
        function for the given argument types.  Each expression is a Call
        object.  The intent is that at run-time the first Call that doesn't
        cause FailedToImplement to be raised is the good one.
        """
        prefixargs = tuple(prefixargs)
        suffixargs = tuple(suffixargs)

        def walktree(node, args_so_far):
            if isinstance(node, list):
                for func in node:
                    if func is not None:
                        result.append(Call(func, prefixargs +
                                                 args_so_far +
                                                 suffixargs))
            else:
                index = len(args_so_far)
                typeorder = self.list_of_typeorders[index]
                next_type = argtypes[index]
                for target_type, converter in typeorder[next_type]:
                    if target_type not in node:
                        continue
                    next_arg = args[index]
                    if converter:
                        next_arg = Call(converter, prefixargs + (next_arg,))
                    walktree(node[target_type], args_so_far + (next_arg,))

        result = []
        walktree(self.multimethod.dispatch_tree, ())
        return result


class Call(object):
    """ Represents a call expression.
    The arguments may themselves be Call objects.
    """
    def __init__(self, function, arguments):
        self.function = function
        self.arguments = arguments


class CompressedArray:
    def __init__(self, null_value, reserved_count):
        self.null_value = null_value
        self.reserved_count = reserved_count
        self.items = [null_value] * reserved_count

    def insert_subarray(self, array):
        # insert the given array of numbers into the indexlist,
        # allowing null values to become non-null
        initial_nulls = 0
        for item in array:
            if item != self.null_value:
                break
            initial_nulls += 1
        test = max(self.reserved_count - initial_nulls, 0)
        while True:
            while test+len(array) > len(self.items):
                self.items.append(self.null_value)
            for i in range(len(array)):
                if not (array[i] == self.items[test+i] or
                        array[i] == self.null_value or
                        self.items[test+i] == self.null_value):
                    break
            else:
                # success
                for i in range(len(array)):
                    if array[i] != self.null_value:
                        self.items[test+i] = array[i]
                return test
            test += 1

    def _freeze_(self):
        return True


class MRDTable:
    # Multi-Method Dispatch Using Multiple Row Displacement,
    # Candy Pang, Wade Holst, Yuri Leontiev, and Duane Szafron
    # University of Alberta, Edmonton AB T6G 2H1 Canada

    Counter = 0

    def __init__(self, list_of_types):
        self.id = MRDTable.Counter
        MRDTable.Counter += 1
        self.list_of_types = list_of_types
        self.typenum = dict(zip(list_of_types, range(len(list_of_types))))
        self.attrname = '__mrd%d_typenum' % self.id
        for t1, num in self.typenum.items():
            setattr(t1, self.attrname, num)
        self.indexarray = CompressedArray(0, 1)


class InstallerVersion2:
    """NOT_RPYTHON"""

    mrdtables = {}

    def __init__(self, multimethod, prefix, list_of_typeorders,
                 baked_perform_call=True):
        print 'InstallerVersion2:', prefix
        self.multimethod = multimethod
        self.prefix = prefix
        self.list_of_typeorders = list_of_typeorders
        self.baked_perform_call = baked_perform_call
        self.mmfunccache = {}
        args = ['arg%d' % i for i in range(multimethod.arity)]
        self.fnargs = (multimethod.argnames_before + args +
                       multimethod.argnames_after)

        # compute the complete table
        assert multimethod.arity == 2
        assert list_of_typeorders[0] == list_of_typeorders[1]

        lst = list(list_of_typeorders[0])
        lst.sort()
        key = tuple(lst)
        try:
            self.mrdtable = self.mrdtables[key]
        except KeyError:
            self.mrdtable = self.mrdtables[key] = MRDTable(key)

        dispatcher = MMDispatcher(multimethod, list_of_typeorders)
        self.table = {}
        for t0 in list_of_typeorders[0]:
            for t1 in list_of_typeorders[1]:
                calllist = dispatcher.expressions([t0, t1],
                                                  multimethod.argnames_before,
                                                  args,
                                                  multimethod.argnames_after)
                if calllist:
                    self.table[t0, t1] = calllist

    def is_empty(self):
        return len(self.table) == 0

    def install(self):
        null_func = self.build_function(self.prefix + '_fail', [], True)
        if self.is_empty():
            return null_func

        funcarray = CompressedArray(null_func, 1)
        indexarray = self.mrdtable.indexarray
        lst = self.mrdtable.list_of_types
        indexline = []
        for t0 in lst:
            flatline = []
            for t1 in lst:
                calllist = self.table.get((t0, t1), [])
                funcname = '_'.join([self.prefix, t0.__name__, t1.__name__])
                fn = self.build_function(funcname, calllist)
                flatline.append(fn)
            index = funcarray.insert_subarray(flatline)
            indexline.append(index)

        master_index = indexarray.insert_subarray(indexline)

        print master_index
        print indexarray.items
        print funcarray.items

        attrname = self.mrdtable.attrname
        exprfn = "funcarray.items[indexarray.items[%d + arg0.%s] + arg1.%s]" %(
            master_index, attrname, attrname)
        expr = Call(exprfn, self.fnargs)
        return self.build_function(self.prefix + '_perform_call',
                                   [expr], True,
                                   indexarray = indexarray,
                                   funcarray = funcarray)

    def build_function(self, funcname, calllist, is_perform_call=False,
                       **extranames):
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

        def expr(v):
            if isinstance(v, Call):
                return '%s(%s)' % (invent_name(v.function),
                                   ', '.join([expr(w) for w in v.arguments]))
            else:
                return v

        fallback = len(calllist) == 0
        if fallback:
            miniglobals = {'raiseFailedToImplement': raiseFailedToImplement}
            bodylines = ['return raiseFailedToImplement()']
        else:
            miniglobals = {'FailedToImplement': FailedToImplement}
            miniglobals.update(extranames)
            bodylines = []
            for v in calllist[:-1]:
                bodylines.append('try:')
                bodylines.append('    return %s' % expr(v))
                bodylines.append('except FailedToImplement:')
                bodylines.append('    pass')
            bodylines.append('return %s' % expr(calllist[-1]))

        if is_perform_call and not self.baked_perform_call:
            return self.fnargs, bodylines[0][len('return '):], miniglobals, fallback

        # indent mode
        bodylines = ['    ' + line for line in bodylines]
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
            source = 'def %s(%s):\n%s' % (funcname, ', '.join(self.fnargs),
                                          source)
            exec compile2(source) in miniglobals
            func = miniglobals[funcname]
            self.mmfunccache[key] = func 
        #else: 
        #    print "avoided duplicate function", func
        return func

# ____________________________________________________________
# Selection of the version to use

Installer = InstallerVersion1
