from __future__ import with_statement
import new
import py
from pypy.objspace.flow.model import Constant, Block, Link, Variable
from pypy.objspace.flow.model import mkentrymap, c_last_exception
from pypy.interpreter.argument import Arguments
from pypy.translator.simplify import simplify_graph
from pypy.objspace.flow.objspace import FlowObjSpace, error
from pypy.objspace.flow import objspace, flowcontext
from pypy import conftest
from pypy.tool.stdlib_opcode import bytecode_spec
from pypy.interpreter.pyframe import PyFrame

import os
import operator
is_operator = getattr(operator, 'is_', operator.eq) # it's not there 2.2

class Base:
    def codetest(self, func):
        import inspect
        try:
            func = func.im_func
        except AttributeError:
            pass
        #name = func.func_name
        graph = self.space.build_flow(func)
        graph.source = inspect.getsource(func)
        self.show(graph)
        return graph

    def show(self, graph):
        if conftest.option.view:
            graph.show()

    def setup_class(cls): 
        cls.space = FlowObjSpace() 

    def all_operations(self, graph):
        result = {}
        for node in graph.iterblocks():
            for op in node.operations:
                result.setdefault(op.opname, 0)
                result[op.opname] += 1
        return result


class TestFlowObjSpace(Base):

    def nothing():
        pass

    def test_nothing(self):
        x = self.codetest(self.nothing)
        assert len(x.startblock.exits) == 1
        link, = x.startblock.exits
        assert link.target == x.returnblock

    #__________________________________________________________
    def simplefunc(x):
        return x+1

    def test_simplefunc(self):
        graph = self.codetest(self.simplefunc)
        assert self.all_operations(graph) == {'add': 1}

    #__________________________________________________________
    def simplebranch(i, j):
        if i < 0:
            return i
        return j

    def test_simplebranch(self):
        x = self.codetest(self.simplebranch)

    #__________________________________________________________
    def ifthenelse(i, j):
        if i < 0:
            i = j
        return user_defined_function(i) + 1
    
    def test_ifthenelse(self):
        x = self.codetest(self.ifthenelse)

    #__________________________________________________________
    def loop(x):
        x = abs(x)
        while x:
            x = x - 1

    def test_loop(self):
        graph = self.codetest(self.loop)
        assert self.all_operations(graph) == {'abs': 1,
                                              'is_true': 1,
                                              'sub': 1}

    #__________________________________________________________
    def print_(i):
        print i
    
    def test_print(self):
        x = self.codetest(self.print_)

    #__________________________________________________________
    def while_(i):
        while i > 0:
            i = i - 1

    def test_while(self):
        x = self.codetest(self.while_)

    #__________________________________________________________
    def union_easy(i):
        if i:
            pass
        else:
            i = 5
        return i

    def test_union_easy(self):
        x = self.codetest(self.union_easy)

    #__________________________________________________________
    def union_hard(i):
        if i:
            i = 5
        return i
    
    def test_union_hard(self):
        x = self.codetest(self.union_hard)

    #__________________________________________________________
    def while_union(i):
        total = 0
        while i > 0:
            total += i
            i = i - 1
        return total
    
    def test_while_union(self):
        x = self.codetest(self.while_union)

    #__________________________________________________________
    def simple_for(lst):
        total = 0
        for i in lst:
            total += i
        return total
    
    def test_simple_for(self):
        x = self.codetest(self.simple_for)

    #__________________________________________________________
    def nested_whiles(i, j):
        s = ''
        z = 5
        while z > 0:
            z = z - 1
            u = i
            while u < j:
                u = u + 1
                s = s + '.'
            s = s + '!'
        return s

    def test_nested_whiles(self):
        x = self.codetest(self.nested_whiles)

    #__________________________________________________________
    def break_continue(x):
        result = []
        i = 0
        while 1:
            i = i + 1
            try:
                if i&1:
                    continue
                if i >= x:
                    break
            finally:
                result.append(i)
            i = i + 1
        return result

    def test_break_continue(self):
        x = self.codetest(self.break_continue)

    #__________________________________________________________
    def unpack_tuple(lst):
        a, b, c = lst

    def test_unpack_tuple(self):
        x = self.codetest(self.unpack_tuple)

    #__________________________________________________________
    def reverse_3(lst):
        try:
            a, b, c = lst
        except:
            return 0, 0, 0
        else:
            return c, b, a

    def test_reverse_3(self):
        x = self.codetest(self.reverse_3)

    #__________________________________________________________
    def finallys(lst):
        x = 1
        try:
            x = 2
            try:
                x = 3
                a, = lst
                x = 4
            except KeyError:
                return 5
            except ValueError:
                return 6
            b, = lst
            x = 7
        finally:
            x = 8
        return x

    def test_finallys(self):
        x = self.codetest(self.finallys)

    #__________________________________________________________
    def const_pow():
        return 2 ** 5

    def test_const_pow(self):
        x = self.codetest(self.const_pow)

    #__________________________________________________________
    def implicitException(lst):
        try:
            x = lst[5]
        except Exception:
            return 'catch'
        return lst[3]   # not caught

    def test_implicitException(self):
        x = self.codetest(self.implicitException)
        simplify_graph(x)
        self.show(x)
        for link in x.iterlinks():
            assert link.target is not x.exceptblock

    def implicitAttributeError(x):
        try:
            x = getattr(x, "y")
        except AttributeError:
            return 'catch'
        return getattr(x, "z")   # not caught

    def test_implicitAttributeError(self):
        x = self.codetest(self.implicitAttributeError)
        simplify_graph(x)
        self.show(x)
        for link in x.iterlinks():
            assert link.target is not x.exceptblock

    #__________________________________________________________
    def implicitException_int_and_id(x):
        try:
            return int(x) + id(x)
        except TypeError:   # not captured by the flow graph!
            return 0

    def test_implicitException_int_and_id(self):
        x = self.codetest(self.implicitException_int_and_id)
        simplify_graph(x)
        self.show(x)
        assert len(x.startblock.exits) == 1
        assert x.startblock.exits[0].target is x.returnblock

    #__________________________________________________________
    def implicitException_os_stat(x):
        try:
            return os.stat(x)
        except OSError:   # *captured* by the flow graph!
            return 0

    def test_implicitException_os_stat(self):
        x = self.codetest(self.implicitException_os_stat)
        simplify_graph(x)
        self.show(x)
        assert len(x.startblock.exits) == 3
        d = {}
        for link in x.startblock.exits:
            d[link.exitcase] = True
        assert d == {None: True, OSError: True, Exception: True}

    #__________________________________________________________
    def reraiseAnythingDicCase(dic):
        try:
            dic[5]
        except:
            raise

    def test_reraiseAnythingDicCase(self):
        x = self.codetest(self.reraiseAnythingDicCase)
        simplify_graph(x)
        self.show(x)
        found = {}
        for link in x.iterlinks():
                if link.target is x.exceptblock:
                    if isinstance(link.args[0], Constant):
                        found[link.args[0].value] = True
                    else:
                        found[link.exitcase] = None
        assert found == {IndexError: True, KeyError: True, Exception: None}
    
    def reraiseAnything(x):
        try:
            pow(x, 5)
        except:
            raise

    def test_reraiseAnything(self):
        x = self.codetest(self.reraiseAnything)
        simplify_graph(x)
        self.show(x)
        found = {}
        for link in x.iterlinks():
                if link.target is x.exceptblock:
                    assert isinstance(link.args[0], Constant)
                    found[link.args[0].value] = True
        assert found == {ValueError: True, ZeroDivisionError: True, OverflowError: True}

    def loop_in_bare_except_bug(lst):
        try:
            for x in lst:
                pass
        except:
            lst.append(5)
            raise

    def test_loop_in_bare_except_bug(self):
        x = self.codetest(self.loop_in_bare_except_bug)
        simplify_graph(x)
        self.show(x)

    #__________________________________________________________
    def freevar(self, x):
        def adder(y):
            return x+y
        return adder

    def test_freevar(self):
        x = self.codetest(self.freevar(3))

    #__________________________________________________________
    def raise1(msg):
        raise IndexError
    
    def test_raise1(self):
        x = self.codetest(self.raise1)
        simplify_graph(x)
        self.show(x)
        ops = x.startblock.operations
        assert len(ops) == 2
        assert ops[0].opname == 'simple_call'
        assert ops[0].args == [Constant(IndexError)]
        assert ops[1].opname == 'type'
        assert ops[1].args == [ops[0].result]
        assert x.startblock.exits[0].args == [ops[1].result, ops[0].result]
        assert x.startblock.exits[0].target is x.exceptblock

    #__________________________________________________________
    def raise2(msg):
        raise IndexError, msg
    
    def test_raise2(self):
        x = self.codetest(self.raise2)
        # XXX can't check the shape of the graph, too complicated...

    #__________________________________________________________
    def raise3(msg):
        raise IndexError(msg)
    
    def test_raise3(self):
        x = self.codetest(self.raise3)
        # XXX can't check the shape of the graph, too complicated...

    #__________________________________________________________
    def raise4(stuff):
        raise stuff
    
    def test_raise4(self):
        x = self.codetest(self.raise4)

    #__________________________________________________________
    def raisez(z, tb):
        raise z.__class__,z, tb

    def test_raisez(self):
        x = self.codetest(self.raisez)

    #__________________________________________________________
    def raise_and_catch_1(exception_instance):
        try:
            raise exception_instance
        except IndexError:
            return -1
        return 0
    
    def test_raise_and_catch_1(self):
        x = self.codetest(self.raise_and_catch_1)

    #__________________________________________________________
    def catch_simple_call():
        try:
            user_defined_function()
        except IndexError:
            return -1
        return 0
    
    def test_catch_simple_call(self):
        x = self.codetest(self.catch_simple_call)

    #__________________________________________________________
    def multiple_catch_simple_call():
        try:
            user_defined_function()
        except (IndexError, OSError):
            return -1
        return 0
    
    def test_multiple_catch_simple_call(self):
        graph = self.codetest(self.multiple_catch_simple_call)
        simplify_graph(graph)
        assert self.all_operations(graph) == {'simple_call': 1}
        entrymap = mkentrymap(graph)
        links = entrymap[graph.returnblock]
        assert len(links) == 3
        assert (dict.fromkeys([link.exitcase for link in links]) ==
                dict.fromkeys([None, IndexError, OSError]))
        links = entrymap[graph.exceptblock]
        assert len(links) == 1
        assert links[0].exitcase is Exception

    #__________________________________________________________
    def dellocal():
        x = 1
        del x
        for i in range(10):
            pass
    
    def test_dellocal(self):
        x = self.codetest(self.dellocal)

    #__________________________________________________________
    def globalconstdict(name):
        x = DATA['x']
        z = DATA[name]
        return x, z
    
    def test_globalconstdict(self):
        x = self.codetest(self.globalconstdict)

    #__________________________________________________________
    def dictliteral(name):
        x = {'x': 1}
        return x
    
    def test_dictliteral(self):
        x = self.codetest(self.dictliteral)

    #__________________________________________________________
    
    def specialcases(x):
        operator.lt(x,3)
        operator.le(x,3)
        operator.eq(x,3)
        operator.ne(x,3)
        operator.gt(x,3)
        operator.ge(x,3)
        is_operator(x,3)
        operator.__lt__(x,3)
        operator.__le__(x,3)
        operator.__eq__(x,3)
        operator.__ne__(x,3)
        operator.__gt__(x,3)
        operator.__ge__(x,3)
        operator.xor(x,3)
        # the following ones are constant-folded
        operator.eq(2,3)
        operator.__gt__(2,3)
    
    def test_specialcases(self):
        x = self.codetest(self.specialcases)
        from pypy.translator.simplify import join_blocks
        join_blocks(x)
        assert len(x.startblock.operations) == 14
        for op in x.startblock.operations:
            assert op.opname in ['lt', 'le', 'eq', 'ne',
                                       'gt', 'ge', 'is_', 'xor']
            assert len(op.args) == 2
            assert op.args[1].value == 3

    #__________________________________________________________

    def wearetranslated(x):
        from pypy.rlib.objectmodel import we_are_translated
        if we_are_translated():
            return x
        else:
            some_name_error_here

    def test_wearetranslated(self):
        x = self.codetest(self.wearetranslated)
        from pypy.translator.simplify import join_blocks
        join_blocks(x)
        # check that 'x' is an empty graph
        assert len(x.startblock.operations) == 0
        assert len(x.startblock.exits) == 1
        assert x.startblock.exits[0].target is x.returnblock

    #__________________________________________________________
    def jump_target_specialization(x):
        if x:
            n = 5
        else:
            n = 6
        return n*2

    def test_jump_target_specialization(self):
        x = self.codetest(self.jump_target_specialization)
        for block in x.iterblocks():
            for op in block.operations:
                assert op.opname != 'mul', "mul should have disappeared"

    #__________________________________________________________
    def highly_branching_example(a,b,c,d,e,f,g,h,i,j):
        if a:
            x1 = 1
        else:
            x1 = 2
        if b:
            x2 = 1
        else:
            x2 = 2
        if c:
            x3 = 1
        else:
            x3 = 2
        if d:
            x4 = 1
        else:
            x4 = 2
        if e:
            x5 = 1
        else:
            x5 = 2
        if f:
            x6 = 1
        else:
            x6 = 2
        if g:
            x7 = 1
        else:
            x7 = 2
        if h:
            x8 = 1
        else:
            x8 = 2
        if i:
            x9 = 1
        else:
            x9 = 2
        if j:
            x10 = 1
        else:
            x10 = 2
        return (x1, x2, x3, x4, x5, x6, x7, x8, x9, x10)

    def test_highly_branching_example(self):
        x = self.codetest(self.highly_branching_example)
        # roughly 20 blocks + 30 links
        assert len(list(x.iterblocks())) + len(list(x.iterlinks())) < 60

    #__________________________________________________________
    def test_unfrozen_user_class1(self):
        class C:
            def __nonzero__(self):
                return True
        c = C()
        def f():
            if c:
                return 1
            else:
                return 2
        graph = self.codetest(f)

        results = []
        for link in graph.iterlinks():
            if link.target == graph.returnblock:
                results.extend(link.args)
        assert len(results) == 2

    def test_unfrozen_user_class2(self):
        class C:
            def __add__(self, other):
                return 4
        c = C()
        d = C()
        def f():
            return c+d
        graph = self.codetest(f)

        results = []
        for link in graph.iterlinks():
            if link.target == graph.returnblock:
                results.extend(link.args)
        assert not isinstance(results[0], Constant)

    def test_frozen_user_class1(self):
        class C:
            def __nonzero__(self):
                return True
            def _freeze_(self):
                return True
        c = C()
        def f():
            if c:
                return 1
            else:
                return 2

        graph = self.codetest(f)

        results = []
        for link in graph.iterlinks():
            if link.target == graph.returnblock:
                results.extend(link.args)
        assert len(results) == 1

    def test_frozen_user_class2(self):
        class C:
            def __add__(self, other):
                return 4
            def _freeze_(self):
                return True
        c = C()
        d = C()
        def f():
            return c+d
        graph = self.codetest(f)

        results = []
        for link in graph.iterlinks():
            if link.target == graph.returnblock:
                results.extend(link.args)
        assert results == [Constant(4)]

    def test_const_star_call(self):
        def g(a=1,b=2,c=3):
            pass
        def f():
            return g(1,*(2,3))
        graph = self.codetest(f)
        for block in graph.iterblocks():
            for op in block.operations:
                assert not op.opname == "call_args"

    def test_catch_importerror_1(self):
        def f():
            try:
                import pypy.this_does_not_exist
            except ImportError:
                return 1
        graph = self.codetest(f)
        simplify_graph(graph)
        self.show(graph)
        assert not graph.startblock.operations
        assert len(graph.startblock.exits) == 1
        assert graph.startblock.exits[0].target is graph.returnblock

    def test_catch_importerror_2(self):
        def f():
            try:
                from pypy import this_does_not_exist
            except ImportError:
                return 1
        graph = self.codetest(f)
        simplify_graph(graph)
        self.show(graph)
        assert not graph.startblock.operations
        assert len(graph.startblock.exits) == 1
        assert graph.startblock.exits[0].target is graph.returnblock

    def test_importerror_1(self):
        def f():
            import pypy.this_does_not_exist
        py.test.raises(ImportError, 'self.codetest(f)')

    def test_importerror_2(self):
        def f():
            from pypy import this_does_not_exist
        py.test.raises(ImportError, 'self.codetest(f)')

    def test_mergeable(self):
        def myfunc(x):
            if x:
                from pypy.interpreter.error import OperationError
                s = 12
            else:
                s = x.abc
            return x[s]
        graph = self.codetest(myfunc)

    def test_unichr_constfold(self):
        py.test.skip("not working")
        def myfunc():
            return unichr(1234)
        graph = self.codetest(myfunc)
        assert graph.startblock.exits[0].target is graph.returnblock

    def test_unicode_constfold(self):
        py.test.skip("not working for now")
        def myfunc():
            return unicode("1234")
        graph = self.codetest(myfunc)
        assert graph.startblock.exits[0].target is graph.returnblock

    def test_unicode(self):
        def myfunc(n):
            try:
                return unicode(chr(n))
            except UnicodeDecodeError:
                return None
        graph = self.codetest(myfunc)
        simplify_graph(graph)
        assert graph.startblock.exitswitch == c_last_exception
        assert graph.startblock.exits[0].target is graph.returnblock
        assert graph.startblock.exits[1].target is graph.returnblock

    def test_getitem(self):
        def f(c, x):
            try:
                return c[x]
            except Exception:
                raise
        graph = self.codetest(f)
        simplify_graph(graph)
        assert self.all_operations(graph) == {'getitem_idx_key': 1}

        g = lambda: None
        def f(c, x):
            try:
                return c[x]
            finally:
                g()
        graph = self.codetest(f)
        simplify_graph(graph)
        assert self.all_operations(graph) == {'getitem_idx_key': 1,
                                              'simple_call': 2}

        def f(c, x):
            try:
                return c[x]
            except IndexError:
                raise
        graph = self.codetest(f)
        simplify_graph(graph)
        assert self.all_operations(graph) == {'getitem_idx': 1}        

        def f(c, x):
            try:
                return c[x]
            except KeyError:
                raise
        graph = self.codetest(f)
        simplify_graph(graph)
        assert self.all_operations(graph) == {'getitem_key': 1}
        
        def f(c, x):
            try:
                return c[x]
            except ValueError:
                raise
        graph = self.codetest(f)
        simplify_graph(graph)
        assert self.all_operations(graph) == {'getitem': 1}

        def f(c, x):
            try:
                return c[x]
            except Exception:
                return -1
        graph = self.codetest(f)
        simplify_graph(graph)
        self.show(graph)
        assert self.all_operations(graph) == {'getitem_idx_key': 1}
        
        def f(c, x):
            try:
                return c[x]
            except IndexError:
                return -1
        graph = self.codetest(f)
        simplify_graph(graph)
        assert self.all_operations(graph) == {'getitem_idx': 1}

        def f(c, x):
            try:
                return c[x]
            except KeyError:
                return -1
        graph = self.codetest(f)
        simplify_graph(graph)
        assert self.all_operations(graph) == {'getitem_key': 1}
  
        def f(c, x):
            try:
                return c[x]
            except ValueError:
                return -1
        graph = self.codetest(f)
        simplify_graph(graph)
        assert self.all_operations(graph) == {'getitem': 1}

    def test_context_manager(self):
        def f(c, x):
            with x:
                pass
        graph = self.codetest(f)
        # 2 method calls: x.__enter__() and x.__exit__(None, None, None)
        assert self.all_operations(graph) == {'getattr': 2,
                                              'simple_call': 2}
        #
        def g(): pass
        def f(c, x):
            with x:
                res = g()
            return res
        graph = self.codetest(f)
        assert self.all_operations(graph) == {
            'getattr': 2,     # __enter__ and __exit__
            'simple_call': 4, # __enter__, g and 2 possible calls to __exit__
            }

    def monkey_patch_code(self, code, stacksize, flags, codestring, names, varnames):
        c = code
        return new.code(c.co_argcount, c.co_nlocals, stacksize, flags,
                        codestring, c.co_consts, names, varnames,
                        c.co_filename, c.co_name, c.co_firstlineno,
                        c.co_lnotab)

    def test_callmethod_opcode(self):
        """ Tests code generated by pypy-c compiled with CALL_METHOD
        bytecode
        """
        flow_meth_names = flowcontext.FlowSpaceFrame.opcode_method_names
        pyframe_meth_names = PyFrame.opcode_method_names
        for name in ['CALL_METHOD', 'LOOKUP_METHOD']:
            num = bytecode_spec.opmap[name]
            locals()['old_' + name] = flow_meth_names[num]
            flow_meth_names[num] = pyframe_meth_names[num]
        try:
            class X:
                def m(self):
                    return 3

            def f():
                x = X()
                return x.m()

            # this code is generated by pypy-c when compiling above f
            pypy_code = 't\x00\x00\x83\x00\x00}\x00\x00|\x00\x00\xc9\x01\x00\xca\x00\x00S'
            new_c = self.monkey_patch_code(f.func_code, 3, 3, pypy_code, ('X', 'x', 'm'), ('x',))
            f2 = new.function(new_c, locals(), 'f')

            graph = self.codetest(f2)
            all_ops = self.all_operations(graph)
            assert all_ops['simple_call'] == 2
            assert all_ops['getattr'] == 1
        finally:
            for name in ['CALL_METHOD', 'LOOKUP_METHOD']:
                num = bytecode_spec.opmap[name]
                flow_meth_names[num] = locals()['old_' + name]

    def test_dont_capture_RuntimeError(self):
        class Foo:
            def __hash__(self):
                return hash(self)
        foolist = [Foo()]
        def f():
            return foolist[0]
        py.test.raises(RuntimeError, "self.codetest(f)")

    def test_getslice_constfold(self):
        def check(f, expected):
            graph = self.codetest(f)
            assert graph.startblock.operations == []
            [link] = graph.startblock.exits
            assert link.target is graph.returnblock
            assert isinstance(link.args[0], Constant)
            assert link.args[0].value == expected

        def f1():
            s = 'hello'
            return s[:-2]
        check(f1, 'hel')

        def f2():
            s = 'hello'
            return s[:]
        check(f2, 'hello')

        def f3():
            s = 'hello'
            return s[-3:]
        check(f3, 'llo')

    def test_propagate_attribute_error(self):
        def f(x):
            try:
                "".invalid
            finally:
                if x and 0:
                    raise TypeError()
        py.test.raises(Exception, self.codetest, f)

    def test__flowspace_rewrite_directly_as_(self):
        def g(x):
            pass
        def f(x):
            pass
        f._flowspace_rewrite_directly_as_ = g
        def h(x):
            f(x)
        graph = self.codetest(h)
        assert self.all_operations(graph) == {'simple_call': 1}
        for block in graph.iterblocks():
            if block.operations:
                op = block.operations[0]
                assert op.opname == 'simple_call'
                assert op.args[0] == Constant(g)


    def test_cannot_catch_special_exceptions(self):
        def f():
            try:
                f()
            except NotImplementedError:
                pass
        py.test.raises(error.FlowingError, "self.codetest(f)")
        #
        def f():
            try:
                f()
            except AssertionError:
                pass
        py.test.raises(error.FlowingError, "self.codetest(f)")


class TestFlowObjSpaceDelay(Base):
    def setup_class(cls):
        cls.space = FlowObjSpace()
        cls.space.do_imports_immediately = False

    def test_import_something(self):
        def f():
            from some.unknown.module import stuff
        g = self.codetest(f)


class TestGenInterpStyle(Base):
    def setup_class(cls):
        cls.space = FlowObjSpace()
        cls.space.config.translation.builtins_can_raise_exceptions = True

    def reraiseAttributeError(v):
        try:
            x = getattr(v, "y")
        except AttributeError:
            raise

    def test_reraiseAttributeError(self):
        x = self.codetest(self.reraiseAttributeError)
        simplify_graph(x)
        self.show(x)
        excfound = []
        for link in x.iterlinks():
            if link.target is x.exceptblock:
                excfound.append(link.exitcase)
        assert len(excfound) == 2
        excfound.sort()
        expected = [Exception, AttributeError]
        expected.sort()
        assert excfound == expected

    def reraiseTypeError(dic):
        try:
            x = dic[5]
        except TypeError:
            raise

    def test_reraiseTypeError(self):
        x = self.codetest(self.reraiseTypeError)
        simplify_graph(x)
        self.show(x)
        excfound = []
        for link in x.iterlinks():
            if link.target is x.exceptblock:
                excfound.append(link.exitcase)
        assert len(excfound) == 2
        excfound.sort()
        expected = [Exception, TypeError]
        expected.sort()
        assert excfound == expected

    def test_can_catch_special_exceptions(self):
        def f():
            try:
                f()
            except NotImplementedError:
                pass
        graph = self.codetest(f)
        # assert did not crash


DATA = {'x': 5,
        'y': 6}

def user_defined_function():
    pass


def test_extract_cell_content():
    class Strange(object):
        def __cmp__(self, other):
            assert False, "should not be called"
    strange = Strange()
    def f():
        return strange
    res = objspace.extract_cell_content(f.func_closure[0])
    assert res is strange
