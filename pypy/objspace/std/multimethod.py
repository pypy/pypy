
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

    def install(self, prefix, list_of_typeorders, baked_perform_call=True,
                base_typeorder=None, installercls=None):
        "NOT_RPYTHON: initialization-time only"
        assert len(list_of_typeorders) == self.arity
        installercls = installercls or Installer
        installer = installercls(self, prefix, list_of_typeorders,
                                 baked_perform_call=baked_perform_call,
                                 base_typeorder=base_typeorder)
        return installer.install()

    def install_if_not_empty(self, prefix, list_of_typeorders,
                             base_typeorder=None, installercls=None):
        "NOT_RPYTHON: initialization-time only"
        assert len(list_of_typeorders) == self.arity
        installercls = installercls or Installer
        installer = installercls(self, prefix, list_of_typeorders,
                                 base_typeorder=base_typeorder)
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

    instance_counter = 0

    mmfunccache = {}

    prefix_memo = {}

    def __init__(self, multimethod, prefix, list_of_typeorders,
                 baked_perform_call=True, base_typeorder=None):
        self.__class__.instance_counter += 1
        self.multimethod = multimethod
        # avoid prefix clashes, user code should supply different prefixes
        # itself for nice names in tracebacks
        base_prefix = prefix
        n = 1
        while prefix in self.prefix_memo:
            n += 1
            prefix = "%s%d" % (base_prefix, n)
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

class MMDispatcher(object):
    """NOT_RPYTHON
    Explicit dispatcher class.  This is not used in normal execution, which
    uses the complex Installer below to install single-dispatch methods to
    achieve the same result.  The MMDispatcher is only used by
    rpython.lltypesystem.rmultimethod.  It is also nice for documentation.
    """
    _revcache = None

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

    def anychance(self, typesprefix):
        # is there any chance that a list of types starting with typesprefix
        # could lead to a successful dispatch?
        # (START-UP TIME OPTIMIZATION ONLY)
        if self._revcache is None:

            def build_tree(types_so_far, dispatch_node):
                non_empty = False
                typeorder = self.list_of_typeorders[len(types_so_far)]
                for next_type in typeorder:
                    if build_single_method(typeorder, types_so_far, next_type,
                                           dispatch_node):
                        non_empty = True
                if non_empty:
                    self._revcache[types_so_far] = True
                return non_empty

            def build_single_method(typeorder, types_so_far, next_type,
                                    dispatch_node):
                order = typeorder[next_type]
                things_to_call = False
                for type, conversion in order:
                    if type not in dispatch_node:
                        # there is no possible completion of
                        # types_so_far+[type] that could lead to a
                        # registered function.
                        continue
                    match = dispatch_node[type]
                    if isinstance(match, dict):
                        if build_tree(types_so_far+(next_type,), match):
                            things_to_call = True
                    elif match:
                        things_to_call = True
                return things_to_call

            self._revcache = {}
            build_tree((), self.multimethod.dispatch_tree)
        return tuple(typesprefix) in self._revcache


class Call(object):
    """ Represents a call expression.
    The arguments may themselves be Call objects.
    """
    def __init__(self, function, arguments):
        self.function = function
        self.arguments = arguments


class CompressedArray(object):
    def __init__(self, null_value):
        self.null_value = null_value
        self.items = [null_value]

    def ensure_length(self, newlen):
        if newlen > len(self.items):
            self.items.extend([self.null_value] * (newlen - len(self.items)))

    def insert_subarray(self, array):
        # insert the given array of numbers into the indexlist,
        # allowing null values to become non-null
        if array.count(self.null_value) == len(array):
            return 0
        test = 1
        while True:
            self.ensure_length(test+len(array))
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


class MRDTable(object):
    # Multi-Method Dispatch Using Multiple Row Displacement,
    # Candy Pang, Wade Holst, Yuri Leontiev, and Duane Szafron
    # University of Alberta, Edmonton AB T6G 2H1 Canada
    # can be found on http://web.cs.ualberta.ca/~yuri/publ.htm

    Counter = 0

    def __init__(self, list_of_types):
        self.id = MRDTable.Counter
        MRDTable.Counter += 1
        self.list_of_types = list_of_types
        self.typenum = dict(zip(list_of_types, range(len(list_of_types))))
        self.attrname = '__mrd%d_typenum' % self.id
        for t1, num in self.typenum.items():
            setattr(t1, self.attrname, num)
        self.indexarray = CompressedArray(0)
        self.strict_subclasses = {}
        for cls1 in list_of_types:
            lst = []
            for cls2 in list_of_types:
                if cls1 is not cls2 and issubclass(cls2, cls1):
                    lst.append(cls2)
            self.strict_subclasses[cls1] = lst

    def normalize_length(self, next_array):
        # make sure that the indexarray is not smaller than any funcarray
        self.indexarray.ensure_length(len(next_array.items))


def invent_name(miniglobals, obj):
    if isinstance(obj, str):
        return obj
    name = obj.__name__
    n = 1
    while name in miniglobals:
        n += 1
        name = '%s%d' % (obj.__name__, n)
    miniglobals[name] = obj
    return name


class FuncEntry(object):

    def __init__(self, bodylines, miniglobals, fallback):
        self.body = '\n    '.join(bodylines)
        self.miniglobals = miniglobals
        self.fallback = fallback
        self.possiblenames = []
        self.typetree = {}
        self._function = None

    def key(self):
        lst = self.miniglobals.items()
        lst.sort()
        return self.body, tuple(lst)

    def get_function_name(self):
        # pick a name consistently based on self.possiblenames
        length = min([len(parts) for parts in self.possiblenames])
        result = []
        for i in range(length):
            choices = {}
            for parts in self.possiblenames:
                choices[parts[i]] = True
            parts = choices.keys()
            res = str(len(parts))
            for part in parts:
                if type(part) is str:     # there is a string at this pos
                    if '0_fail' in choices:
                        res = '0_fail'
                    elif len(parts) == 1:
                        res = part
                    break
            else:
                # only types at this location, try to find a common base
                basecls = parts[0]
                for cls in parts[1:]:
                    if issubclass(basecls, cls):
                        basecls = cls
                for cls in parts[1:]:
                    if not issubclass(cls, basecls):
                        break   # no common base
                else:
                    res = basecls.__name__
            result.append(res)
        return '_'.join(result)

    def make_function(self, fnargs, nbargs_before, mrdtable):
        if self._function is not None:
            return self._function
        name = self.get_function_name()
        self.compress_typechecks(mrdtable)
        checklines = self.generate_typechecks(fnargs[nbargs_before:])
        if not checklines:
            body = self.body
        else:
            checklines.append(self.body)
            body = '\n    '.join(checklines)
        source = 'def %s(%s):\n    %s\n' % (name, ', '.join(fnargs), body)

        if 0:    # for debugging the generated mm sources
            f = open('/tmp/mm-source/%s' % name, 'a')
            for possiblename in self.possiblenames:
                print >> f, '#',
                for part in possiblename:
                    print >> f, getattr(part, '__name__', part),
                print >> f
            print >> f
            print >> f, source
            f.close()

        exec compile2(source) in self.miniglobals
        self._function = self.miniglobals[name]
        return self._function

    def register_valid_types(self, types):
        node = self.typetree
        for t1 in types[:-1]:
            if node is True:
                return
            node = node.setdefault(t1, {})
        if node is True:
            return
        node[types[-1]] = True

    def no_typecheck(self):
        self.typetree = True

    def compress_typechecks(self, mrdtable):
        def full(node):
            if node is True:
                return 1
            fulls = 0
            for key, subnode in node.items():
                if full(subnode):
                    node[key] = True
                    fulls += 1
            if fulls == types_total:
                return 1

            # a word about subclasses: we are using isinstance() to do
            # the checks in generate_typechecks(), which is a
            # compromize.  In theory we should check the type ids
            # instead.  But using isinstance() is better because the
            # annotator can deduce information from that.  It is still
            # correct to use isinstance() instead of type ids in
            # "reasonable" cases, though -- where "reasonable" means
            # that classes always have a delegate to their superclasses,
            # e.g. W_IntObject delegates to W_Root.  If this is true
            # then both kind of checks are good enough to spot
            # mismatches caused by the compression table.

            # Based on this reasoning, we can compress the typechecks a
            # bit more - if we accept W_Root, for example, then we
            # don't have to specifically accept W_IntObject too.
            for cls, subnode in node.items():
                for cls2 in mrdtable.strict_subclasses[cls]:
                    if cls2 in node and node[cls2] == subnode:
                        del node[cls2]

            return 0

        types_total = len(mrdtable.list_of_types)
        if full(self.typetree):
            self.typetree = True

    def generate_typechecks(self, args):
        def generate(node, level=0):
            indent = '    '*level
            if node is True:
                result.append('%s_failedtoimplement = False' % (indent,))
                return
            if not node:
                result.append('%s_failedtoimplement = True' % (indent,))
                return
            keyword = 'if'
            for key, subnode in node.items():
                typename = invent_name(self.miniglobals, key)
                result.append('%s%s isinstance(%s, %s):' % (indent, keyword,
                                                            args[level],
                                                            typename))
                generate(subnode, level+1)
                keyword = 'elif'
            result.append('%selse:' % (indent,))
            result.append('%s    _failedtoimplement = True' % (indent,))

        result = []
        if self.typetree is not True:
            generate(self.typetree)
            result.append('if _failedtoimplement:')
            result.append('    raise FailedToImplement')
        return result


class InstallerVersion2(object):
    """NOT_RPYTHON"""

    instance_counter = 0
    mrdtables = {}

    def __init__(self, multimethod, prefix, list_of_typeorders,
                 baked_perform_call=True, base_typeorder=None):
        #print 'InstallerVersion2:', prefix
        self.__class__.instance_counter += 1
        self.multimethod = multimethod
        self.prefix = prefix
        self.list_of_typeorders = list_of_typeorders
        self.baked_perform_call = baked_perform_call
        self.mmfunccache = {}
        args = ['arg%d' % i for i in range(multimethod.arity)]
        self.fnargs = (multimethod.argnames_before + args +
                       multimethod.argnames_after)

        # compute the complete table
        base_typeorder = base_typeorder or list_of_typeorders[0]
        for typeorder in list_of_typeorders:
            for t1 in typeorder:
                assert t1 in base_typeorder

        lst = list(base_typeorder)
        lst.sort()
        key = tuple(lst)
        try:
            self.mrdtable = self.mrdtables[key]
        except KeyError:
            self.mrdtable = self.mrdtables[key] = MRDTable(key)

        dispatcher = MMDispatcher(multimethod, list_of_typeorders)
        self.table = {}
        def buildtable(prefixtypes):
            if len(prefixtypes) == multimethod.arity:
                calllist = dispatcher.expressions(prefixtypes,
                                                  multimethod.argnames_before,
                                                  args,
                                                  multimethod.argnames_after)
                if calllist:
                    self.table[prefixtypes] = calllist
            elif dispatcher.anychance(prefixtypes):
                typeorder = list_of_typeorders[len(prefixtypes)]
                for t1 in typeorder:
                    buildtable(prefixtypes + (t1,))
        buildtable(())
        self.dispatcher = dispatcher

    def is_empty(self):
        return len(self.table) == 0

    def install(self):
        nskip = len(self.multimethod.argnames_before)
        null_entry = self.build_funcentry([self.prefix, '0_fail'], [])
        null_entry.no_typecheck()
        if self.is_empty():
            return self.answer(null_entry)

        entryarray = CompressedArray(null_entry)
        indexarray = self.mrdtable.indexarray
        lst = self.mrdtable.list_of_types
        indexline = []

        def compress(typesprefix, typesnum):
            if len(typesprefix) == self.multimethod.arity:
                calllist = self.table.get(typesprefix, [])
                funcname = [self.prefix]
                funcname.extend(typesprefix)
                entry = self.build_funcentry(funcname, calllist)
                entry.register_valid_types(typesprefix)
                return entry
            elif self.dispatcher.anychance(typesprefix):
                flatline = []
                for num1, t1 in enumerate(lst):
                    item = compress(typesprefix + (t1,), typesnum + (num1,))
                    flatline.append(item)
                if len(typesprefix) == self.multimethod.arity - 1:
                    array = entryarray
                else:
                    array = indexarray
                return array.insert_subarray(flatline)
            else:
                return 0

        master_index = compress((), ())

        null_func = null_entry.make_function(self.fnargs, nskip, self.mrdtable)
        funcarray = CompressedArray(null_func)
        # round up the length to a power of 2
        N = 1
        while N < len(entryarray.items):
            N *= 2
        funcarray.ensure_length(N)
        for i, entry in enumerate(entryarray.items):
            func = entry.make_function(self.fnargs, nskip, self.mrdtable)
            funcarray.items[i] = func
        self.mrdtable.normalize_length(funcarray)

        #print master_index
        #print indexarray.items
        #print funcarray.items

        attrname = self.mrdtable.attrname
        exprfn = "%d" % master_index
        for n in range(self.multimethod.arity-1):
            exprfn = "hint(indexarray.items, deepfreeze=True)[%s + arg%d.%s]" % (exprfn, n, attrname)
        n = self.multimethod.arity-1
        exprfn = "hint(funcarray.items, deepfreeze=True)[(%s + arg%d.%s) & mmmask]" % (exprfn, n,
                                                                attrname)
        expr = Call(exprfn, self.fnargs)
        entry = self.build_funcentry([self.prefix, '0_perform_call'],
                                     [expr],
                                     indexarray = indexarray,
                                     funcarray = funcarray,
                                     mmmask = N-1)
        entry.no_typecheck()
        return self.answer(entry)

    def answer(self, entry):
        if self.baked_perform_call:
            nskip = len(self.multimethod.argnames_before)
            return entry.make_function(self.fnargs, nskip, self.mrdtable)
        else:
            assert entry.body.startswith('return ')
            expr = entry.body[len('return '):]
            return self.fnargs, expr, entry.miniglobals, entry.fallback

    def build_funcentry(self, funcnameparts, calllist, **extranames):
        def expr(v):
            if isinstance(v, Call):
                return '%s(%s)' % (invent_name(miniglobals, v.function),
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

        from pypy.rlib.jit import hint
        miniglobals['hint'] = hint
        entry = FuncEntry(bodylines, miniglobals, fallback)
        key = entry.key()
        try:
            entry = self.mmfunccache[key]
        except KeyError:
            self.mmfunccache[key] = entry
        entry.possiblenames.append(funcnameparts)
        return entry

# ____________________________________________________________
# Selection of the version to use

Installer = InstallerVersion1   # modified by translate.py targetpypystandalone
