from __future__ import generators
from pypy.interpreter import executioncontext
from pypy.interpreter.module import Module
from pypy.interpreter.extmodule import ExtModule
from pypy.interpreter.error import OperationError

import os.path
import sys
import types

#######################
####  __builtin__  ####
#######################

import __builtin__ as cpy_builtin

class _noarg: 
    """ use this class in interpreter level functions for default 
        values if you want to recognize that no specific value was
        passed. 
    """

class __builtin__(ExtModule):
    """ Template for PyPy's '__builtin__' module.
    """
    
    __name__ = '__builtin__'

    open = cpy_builtin.open
    file = cpy_builtin.file

##    def __init__(self, space):
##        #app level __import__ helpers
##        self.w_imp_modules = space.sys.w_modules
##        self.w_imp_path = space.sys.w_path
##        ExtModule.__init__(self, space)

    def __init__(self, space):
        self.w___debug__ = space.newbool(1)
        # Fix this later to show Ctrl-D on Unix
        self.w_quit = self.w_exit = space.wrap("Use Ctrl-Z (i.e. EOF) to exit.")
        # XXX To-do: Add copyright, credits, and license
        ExtModule.__init__(self, space)

    def _initcompiledbuiltins(self):
        """ add 'compiled' builtins to app-level dict and interp-level """
        self._eval_app_source(xrange_appsource)
        self._eval_app_source(newstyleclasses)

    def _actframe(self, index=-1):
        return self.space.getexecutioncontext().framestack.items[index]

    def globals(self):
        return self._actframe().w_globals

    def private_caller_locals(self):
        #print self.__dict__.keys()
        return self._actframe(-2).getdictscope()
        
    def locals(self):
        return self._actframe().getdictscope()

    def __import__(self, w_modulename, w_globals=None,
                   w_locals=None, w_fromlist=None):
        space = self.space
        w = space.wrap
        try:
            w_mod = space.getitem(space.sys.w_modules, w_modulename)
            return w_mod
        except OperationError,e:
            if not e.match(space, space.w_KeyError):
                raise
            w_mod = space.get_builtin_module(space.unwrap(w_modulename))
            if w_mod is not None:
                space.setitem(space.sys.w_modules, w_modulename, w_mod)
                return w_mod

            import os
            for path in space.unpackiterable(space.sys.w_path):
                f = os.path.join(space.unwrap(path), space.unwrap(w_modulename) + '.py')
                if os.path.exists(f):
                    w_mod = space.wrap(Module(space, w_modulename))
                    space.setitem(space.sys.w_modules, w_modulename, w_mod)
                    space.setattr(w_mod, w('__file__'), w(f))
                    w_dict = space.getattr(w_mod, w('__dict__'))
                    self.execfile(w(f), w_dict, w_dict)
                    return w_mod
            
            w_exc = space.call_function(space.w_ImportError, w_modulename)
            raise OperationError(space.w_ImportError, w_exc)

##    def app___import__(self, *args):
##        # NOTE: No import statements can be done in this function,
##        # as that would involve a recursive call to this function ...
##
##        # args => (name[, globals[, locals[, fromlist]]])
##        
##        l = len(args)
##        if l >= 1:
##            modulename = args[0]
##        else:
##            raise TypeError('__import__() takes at least 1 argument (0 given)')
##        if l >= 2:
##            globals = args[1]
##            try:
##                local_context = self.imp_dirname(globals['__file__'])
##            except KeyError:
##                local_context = ''
##        else:
##            local_context = ''
##        if l >= 4:
##            fromlist = args[3]
##        else:
##            fromlist = []
##        if l > 4:
##            raise TypeError('__import__() takes at most 4 arguments (%i given)' % l)
##            
##        def inner_load(f, fullname):
##            """Load module from file `f` with canonical name `fullname`.
##            """
##            mod = self.imp_module(fullname) # XXX - add in docstring
##            self.imp_modules[fullname] = mod
##            mod.__file__ = f
##            dict = mod.__dict__
##            execfile(f, dict, dict)
##            return mod
##
##        def load(path, modulename, fullname):
##            """Create a module.
##
##            Create a mnodule with canonical name `fullname` from file
##            `modulename`+'.py' in path `path`, if it exist.
##            Or alternatively from the package
##            `path`/`modulename`/'__init__.py'.
##            If neither are found, return None.
##            """
##                
##            f = self.imp_join(path, modulename + '.py')
##            if self.imp_exists(f):
##                return inner_load(f, fullname)
##            f = self.imp_join(path, modulename, '__init__.py')
##            if self.imp_exists(f):
##                return inner_load(f, fullname)
##            else:
##                return None
##
##        names = modulename.split('.')
##
##        if not names:
##            raise ValueError("Cannot import an empty module name.")
##        if len(names) == 1:
##            if self.imp_modules.has_key(modulename):
##                return self.imp_modules[modulename]
##            #Relative Import
##            if local_context:
##                #Regular Module
##                module = load(local_context, modulename, modulename)
##                if module:
##                    return module
##            #Standard Library Module Import
##            for path in self.imp_path:
##                #Regular Module
##                module = load(path, modulename, modulename)
##                if module:
##                    return module                
##            #Module Not Found
##            raise ImportError(modulename)
##        else:
##            #Find most specific module already imported.
##            for i in range(len(names),0,-1):
##                base_name = '.'.join(names[0:i])
##                if self.imp_modules.has_key(base_name):
##                    break
##            #Top level package not imported - import it.
##            else:
##                base_name = names[0]
##                i = 1
##                #Relative Import
##                if ((not local_context) or
##                    not load(local_context, base_name, base_name)):
##                     #Standard Module Import
##                    for path in self.imp_path:
##                        if load(path, base_name, base_name):
##                            break
##                    else:
##                        #Module Not Found
##                        raise ImportError(base_name)                
##            path = self.imp_dirname(self.imp_modules[base_name].__file__)
##            full_name = base_name
##            for j in range(i,len(names)):
##                path = self.imp_join(path, names[j])
##                full_name = '.'.join((full_name, names[j]))
##                if not load(path, '__init__', full_name):
##                    raise ImportError(full_name)
##                ### load module from path
##            if fromlist:
##                return self.imp_modules[modulename]
##            else:
##                return self.imp_modules[names[0]]
##            
##    # Interpreter level helpers for app level import
##    def imp_dirname(self, *args_w):
##        return self.space.wrap(os.path.dirname(*self.space.unwrap(args_w)))
##
##    def imp_join(self, *args_w):
##        return self.space.wrap(os.path.join(*self.space.unwrap(args_w)))
##
##    def imp_exists(self, *args_w):
##        return self.space.wrap(os.path.exists(*self.space.unwrap(args_w)))
##    
##    def imp_module(self, w_name):
##        return self.space.wrap(Module(self.space, w_name))
        
    def compile(self, w_str, w_filename, w_startstr,
                w_supplied_flags=None, w_dont_inherit=None):
        space = self.space
        str_ = space.unwrap(w_str)
        filename = space.unwrap(w_filename)
        startstr = space.unwrap(w_startstr)
        if w_supplied_flags is None:
            supplied_flags = 0
        else:
            supplied_flags = space.unwrap(w_supplied_flags)
            if supplied_flags is None:
                supplied_flags = 0
        if w_dont_inherit is None:
            dont_inherit = 0
        else:
            dont_inherit = space.unwrap(w_dont_inherit)
            if dont_inherit is None:
                dont_inherit = 0

        #print (str_, filename, startstr, supplied_flags, dont_inherit)
        # XXX we additionally allow GENERATORS because compiling some builtins
        #     requires it. doesn't feel quite right to do that here. 
        try:
            c = cpy_builtin.compile(str_, filename, startstr, supplied_flags|4096, dont_inherit)
        # It would be nice to propagate all exceptions to app level,
        # but here we only propagate the 'usual' ones, until we figure
        # out how to do it generically.
        except ValueError,e:
            raise OperationError(space.w_ValueError,space.wrap(str(e)))
        except TypeError,e:
            raise OperationError(space.w_TypeError,space.wrap(str(e)))
        from pypy.interpreter.pycode import PyCode
        return space.wrap(PyCode()._from_code(c))

    def app_execfile(self, filename, glob=None, loc=None):
        if glob is None:
            glob = globals()
            if loc is None:
                loc = locals()
        elif loc is None:
            loc = glob
        f = file(filename)
        try:
            source = f.read()
        finally:
            f.close()
        #Don't exec the source directly, as this loses the filename info
        co = compile(source, filename, 'exec')
        exec co in glob, loc

    ####essentially implemented by the objectspace
    def abs(self, w_val):
        return self.space.abs(w_val)

    def chr(self, w_ascii):
        w_character = self.space.newstring([w_ascii])
        return w_character

    def len(self, w_obj):
        return self.space.len(w_obj)

    def delattr(self, w_object, w_name):
        self.space.delattr(w_object, w_name)
        return self.space.w_None

    def getattr(self, w_object, w_name, w_defvalue = _noarg): 
        try:
            return self.space.getattr(w_object, w_name)
        except OperationError, e:
            if e.match(self.space, self.space.w_AttributeError):
                if w_defvalue is not _noarg:
                    return w_defvalue
            raise

    def hash(self, w_object):
        return self.space.hash(w_object)

    def oct(self, w_val):
        # XXX does this need to be a space operation? 
        return self.space.oct(w_val)

    def hex(self, w_val):
        return self.space.hex(w_val)

    def round(self, w_val, w_n=None):
        if w_n is None:
            w_n = self.space.wrap(0)
        return self.space.round(w_val, w_n)
    
    def id(self, w_object):
        return self.space.id(w_object)

    def app_sum(self, sequence, total=0):
        for item in sequence:
            total = total + item
        return total

    # This function was not in the original builtins,
    # but is quite useful for some aspects of PyPy
    # implementation.
    def app_sign(self, a):
        if a > 0:
            return 1
        elif a < 0:
            return -1
        else:
            return 0

    #XXX works only for new-style classes.
    #So we have to fix it, when we add support for old-style classes
    def issubclass(self, w_cls1, w_cls2):
        return self.space.issubtype(w_cls1, w_cls2)

    def iter(self, w_collection_or_callable, w_sentinel = _noarg):
        if w_sentinel is _noarg:
            return self.space.iter(w_collection_or_callable)
        else:
            if not self.space.is_true(self.callable(w_collection_or_callable)):
                raise OperationError(self.space.w_TypeError,
                        self.space.wrap('iter(v, w): v must be callable'))
            return self._iter_generator(w_collection_or_callable, w_sentinel)

    def app__iter_generator(self, callable_, sentinel):
        """ This generator implements the __iter__(callable,sentinel) protocol """
        while 1:
            result = callable_()
            if result == sentinel:
                raise StopIteration
            yield result

    def app_enumerate(self, collection):
        'Generates an indexed series:  (0,coll[0]), (1,coll[1]) ...'     
        i = 0
        it = iter(collection)
        while 1:
            yield (i, it.next())
            i += 1

    def ord(self, w_val):
        return self.space.ord(w_val)

    def pow(self, w_base, w_exponent, w_modulus=None):
        if w_modulus is None:
            w_modulus = self.space.w_None
        return self.space.pow(w_base, w_exponent, w_modulus)

    def repr(self, w_object):
        return self.space.repr(w_object)

    def setattr(self, w_object, w_name, w_val):
        self.space.setattr(w_object, w_name, w_val)
        return self.space.w_None

    # app-level functions

    def app_apply(self, function, args, kwds={}):
        """call a function (or other callable object) and return its result"""
        return function(*args, **kwds)

    def app_map(self, function, *collections):
        """does 3 separate things, hence this enormous docstring.
           1.  if function is None, return a list of tuples, each with one
               item from each collection.  If the collections have different
               lengths,  shorter ones are padded with None.

           2.  if function is not None, and there is only one collection,
               apply function to every item in the collection and return a
               list of the results.

           3.  if function is not None, and there are several collections,
               repeatedly call the function with one argument from each
               collection.  If the collections have different lengths,
               shorter ones are padded with None"""

        if len(collections) == 0:
            raise TypeError, "map() requires at least one sequence"

        elif len(collections) == 1:
           #it's the most common case, so make it faster
           if function is None:
              return collections[0]
           else:
              return [function(x) for x in collections[0]]
        else:
           res = []
           idx = 0   
           while 1:
              cont = 0     #is any collection not empty?
              args = []
              for collection in collections:
                  try:
                     elem = collection[idx]
                     cont = cont + 1
                  except IndexError:
                     elem = None
                  args.append(elem)
              if cont:
                  if function is None:
                     res.append(tuple(args))
                  else:
                     res.append(function(*args))
              else:
                  return res
              idx = idx + 1

    def app_filter(self, function, collection):
        """construct a list of those elements of collection for which function
           is True.  If function is None, then return the items in the sequence
           which are True."""

        if function is None:
            res = [item for item in collection if item]
        else:
            res = [item for item in collection if function(item)]

        if type(collection) is tuple:
           return tuple(res)
        elif type(collection) is str:
           return "".join(res)
        else:
           return res

    def app_zip(self, *collections):
        """return a list of tuples, where the nth tuple contains every
           nth item of each collection.  If the collections have different
           lengths, zip returns a list as long as the shortest collection,
           ignoring the trailing items in the other collections."""

        if len(collections) == 0:
           raise TypeError, "zip() requires at least one sequence"
        res = []
        idx = 0
        while 1:
           try:
              elems = []
              for collection in collections:
                 elems.append(collection[idx])
              res.append(tuple(elems))
           except IndexError:
              break
           idx = idx + 1
        return res

    def app_reduce(self, function, l, *initialt):
        """ Apply function of two arguments cumulatively to the items of
            sequence, from left to right, so as to reduce the sequence to a
            single value.  Optionally begin with an initial value."""

        if initialt:
           initial, = initialt
           idx = 0
        else:
           try:
              initial = l[0]
           except IndexError:
              raise TypeError, "reduce() of empty sequence with no initial value"
           idx = 1
        while 1:
           try:
             initial = function(initial, l[idx])
             idx = idx + 1
           except IndexError:
             break
        return initial

    def app_isinstance(self, obj, klass_or_tuple):
        objcls = obj.__class__
        if issubclass(klass_or_tuple.__class__, tuple):
           for klass in klass_or_tuple:
               if issubclass(objcls, klass):
                  return 1
           return 0
        else:
           try:
               return issubclass(objcls, klass_or_tuple)
           except TypeError:
               raise TypeError, "isinstance() arg 2 must be a class or type"

    def app_range(self, x, y=None, step=1):
        """ returns a list of integers in arithmetic position from start (defaults
            to zero) to stop - 1 by step (defaults to 1).  Use a negative step to
            get a list in decending order."""

        if y is None: 
                start = 0
                stop = x
        else:
                start = x
                stop = y

        if step == 0:
            raise ValueError, 'range() arg 3 must not be zero'

        elif step > 0:
            if stop <= start: # no work for us
                return []
            howmany = (stop - start + step - 1)/step

        else:  # step must be < 0, or we would have raised ValueError
            if stop >= start: # no work for us
                return []
            howmany = (start - stop - step  - 1)/-step

        arr = [None] * howmany  # this is to avoid using append.

        i = start
        n = 0
        while n < howmany:
            arr[n] = i
            i += step
            n += 1

        return arr

    # min and max could be one function if we had operator.__gt__ and
    # operator.__lt__  Perhaps later when we have operator.

    def app_min(self, *arr):
        """return the smallest number in a list"""

        if not arr:
            raise TypeError, 'min() takes at least one argument'

        if len(arr) == 1:
            arr = arr[0]

        iterator = iter(arr)
        try:
            min = iterator.next()
        except StopIteration:
            raise ValueError, 'min() arg is an empty sequence'

        for i in iterator:
            if min > i:
                min = i
        return min

    def app_max(self, *arr):
        """return the largest number in a list"""

        if not arr:
            raise TypeError, 'max() takes at least one argument'

        if len(arr) == 1:
            arr = arr[0]

        iterator = iter(arr)
        try:
            max = iterator.next()
        except StopIteration:
            raise ValueError, 'max() arg is an empty sequence'

        for i in iterator:
            if max < i:
                max = i
        return max

    def app_divmod(self, x, y):
        return x//y, x%y

    def app_cmp(self, x, y):
        """return 0 when x == y, -1 when x < y and 1 when x > y """
        if x < y:
            return -1
        elif x == y:
            return 0
        else:
            return 1

    def app_vars(self, *obj):
        """return a dictionary of all the attributes currently bound in obj.  If
        called with no argument, return the variables bound in local scope."""

        if len(obj) == 0:
            return _caller_locals()
        elif len(obj) != 1:
            raise TypeError, "vars() takes at most 1 argument."
        else:
            try:
                return obj[0].__dict__
            except AttributeError:
                raise TypeError, "vars() argument must have __dict__ attribute"

    def app_hasattr(self, ob, attr):
        try:
            getattr(ob, attr)
            return True
        except AttributeError:
            return False

    def app_callable(self, ob):
        return hasattr(ob, '__call__')

    def app_dir(self, *args):
        """dir([object]) -> list of strings
        
        Return an alphabetized list of names comprising (some of) the attributes
        of the given object, and of attributes reachable from it:
        
        No argument:  the names in the current scope.
        Module object:  the module attributes.
        Type or class object:  its attributes, and recursively the attributes of
            its bases.
        Otherwise:  its attributes, its class's attributes, and recursively the
            attributes of its class's base classes.
        """
        if len(args) > 1:
            raise TypeError("dir expected at most 1 arguments, got %d"
                            % len(args))
        if len(args) == 0:
            local_names = _caller_locals().keys() # 2 stackframes away
            local_names.sort()
            return local_names
        
        import types
        def _classdir(klass):
            """Return a dict of the accessible attributes of class/type klass.

            This includes all attributes of klass and all of the
            base classes recursively.

            The values of this dict have no meaning - only the keys have
            meaning.  
            """
            Dict = {}
            try:
                Dict.update(klass.__dict__)
            except AttributeError: pass 
            try:
                # XXX - Use of .__mro__ would be suggested, if the existance
                #   of that attribute could be guarranted.
                bases = klass.__bases__
            except AttributeError: pass
            else:
                try:
                    #Note that since we are only interested in the keys,
                    #  the order we merge classes is unimportant
                    for base in bases:
                        Dict.update(_classdir(base))
                except TypeError: pass
            return Dict
        #End _classdir

        obj = args[0]
        
        if isinstance(obj, types.ModuleType):
            try:
                result = obj.__dict__.keys()
                result.sort()
                return result
            except AttributeError:
                return []

        elif isinstance(obj, (types.TypeType, types.ClassType)):
            #Don't look at __class__, as metaclass methods would be confusing.
            result = _classdir(obj).keys()
            result.sort()
            return result

        else: #(regular item)
            Dict = {}
            try:
                Dict.update(obj.__dict__)
            except AttributeError: pass
            try:
                Dict.update(_classdir(obj.__class__))
            except AttributeError: pass
            
            ## Comment from object.c:
            ## /* Merge in __members__ and __methods__ (if any).
            ## XXX Would like this to go away someday; for now, it's
            ## XXX needed to get at im_self etc of method objects. */
            for attr in ['__members__','__methods__']:
                try:
                    for item in getattr(obj, attr):
                        if isinstance(item, types.StringTypes):
                            Dict[item] = None
                except (AttributeError, TypeError): pass
                
            result = Dict.keys()
            result.sort()
            return result

    def app_intern(self, s):
        """
        We don't have a string table, making intern a null operation.
        This is here for backwards compatibility.
        """
        if not isinstance(s, str):
            raise TypeError("intern() argument 1 must be string.")
        return s

    def app_copyright(self):
        print 'Copyright 2002-2004 Pypy development team.\nAll rights reserved.\nFor further information see http://www.codespaek.net/pypy.\nSome materials may have a different copyright.\nIn these cases, this is explicitly noted in the source code file.'

    def app_license(self):
        print \
"""
Copyright (c) <2002-2004> <Pypy development team>
        
Permission is hereby granted, free of charge, to any person obtaining a copy of this software and associated documentation files (the "Software"), to deal in the Software without restriction, including without limitation the rights to use, copy, modify, merge, publish, distribute, sublicense, and/or sell copies of the Software, and to permit persons to whom the Software is furnished to do so, subject to the following conditions:
        
The above copyright notice and this permission notice shall be included in all copies or substantial portions of the Software.
        
THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.
"""

    def app_help(self):
        print "You must be joking."
    
# source code for the builtin xrange-class

xrange_appsource = """if 1: 
    class xrange:
        def __init__(self, start, stop=None, step=1):
            if stop is None: 
                self.start = 0
                self.stop = start
            else:
                self.start = start
                self.stop = stop
            if step == 0:
                raise ValueError, 'xrange() step-argument (arg 3) must not be zero'
            self.step = step

        def __iter__(self):
            def gen(self):
                start, stop, step = self.start, self.stop, self.step
                i = start
                if step > 0:
                    while i < stop:
                        yield i
                        i+=step
                else:
                    while i > stop:
                        yield i
                        i+=step
            return gen(self)
"""

newstyleclasses = """

class property(object):

    def __init__(self, fget=None, fset=None, fdel=None, doc=None):
        self.fget = fget
        self.fset = fset
        self.fdel = fdel
        self.__doc__ = doc or ""

    def __get__(self, obj, objtype=None):
        if obj is None:
            return self         
        if self.fget is None:
            raise AttributeError, "unreadable attribute"
        return self.fget(obj)

    def __set__(self, obj, value):
        if self.fset is None:
            raise AttributeError, "can't set attribute"
        self.fset(obj, value)

    def __delete__(self, obj):
        if self.fdel is None:
            raise AttributeError, "can't delete attribute"
        self.fdel(obj, value)


class staticmethod(object):

    def __init__(self, f):
        self.f = f

    def __get__(self, obj, objtype=None):
        return self.f


class classmethod(object):

    def __init__(self, f):
        self.f = f

    def __get__(self, obj, klass=None):
        if klass is None:
            klass = type(obj)
        def newfunc(*args):
            return self.f(klass, *args)
        return newfunc
"""
