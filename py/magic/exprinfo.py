from compiler import parse, ast, pycodegen
from py import magic 
from py.__impl__.magic import dyncode
import __builtin__, sys

passthroughex = (KeyboardInterrupt, SystemExit, MemoryError) 

class Failure:
    def __init__(self, node):
        self.exc, self.value, self.tb = sys.exc_info()
        self.node = node
        #import traceback
        #traceback.print_exc()


class RunnerFrame:
    """Wrapper around a Python frame holding f_locals and f_globals
    in which expressions can be evaluated."""
    
    def __init__(self, f_globals, f_locals):
        self.f_globals = f_globals
        self.f_locals = f_locals

    def eval(self, code, **vars):
        self.f_locals.update(vars)
        return eval(code, self.f_globals, self.f_locals)

    def exec_(self, code, **vars):
        self.f_locals.update(vars)
        exec code in self.f_globals, self.f_locals

    def repr(self, object):
        return repr(object)

    def is_true(self, object):
        return object


class Interpretable(magic.View):
    """A parse tree node with a few extra methods."""
    explanation = None

    def is_builtin(self, frame):
        return False

    def eval(self, frame):
        # fall-back for unknown expression nodes
        try:
            expr = ast.Expression(self.__obj__)
            expr.filename = '<eval>'
            self.__obj__.filename = '<eval>'
            co = pycodegen.ExpressionCodeGenerator(expr).getCode()
            result = frame.eval(co)
        except passthroughex: 
            raise 
        except:
            raise Failure(self)
        self.result = result
        self.explanation = self.explanation or frame.repr(self.result)

    def run(self, frame):
        # fall-back for unknown statement nodes
        try:
            expr = ast.Module(None, ast.Stmt([self.__obj__]))
            expr.filename = '<run>'
            co = pycodegen.ModuleCodeGenerator(expr).getCode()
            frame.exec_(co)
        except passthroughex: 
            raise 
        except:
            raise Failure(self)

    def nice_explanation(self):
        # uck!  See CallFunc for where \n{ and \n} escape sequences are used
        lines = (self.explanation or '').split('\n')
        result = lines[:1]
        stack = [0]
        stackcnt = [0]
        for line in lines[1:]:
            if line.startswith('{'):
                if stackcnt[-1]:
                    s = 'and   '
                else:
                    s = 'where '
                stack.append(len(result))
                stackcnt[-1] += 1
                stackcnt.append(0)
                result.append(' +' + '  '*(len(stack)-1) + s + line[1:])
            else:
                assert line.startswith('}')
                stack.pop()
                stackcnt.pop()
                result[stack[-1]] += line[1:]
        assert len(stack) == 1
        return '\n'.join(result)

class Name(Interpretable):
    __view__ = ast.Name

    def is_local(self, frame):
        co = compile('%r in locals() is not globals()' % self.name, '?', 'eval')
        try:
            return frame.is_true(frame.eval(co))
        except passthroughex:
            raise
        except:
            return False

    def is_global(self, frame):
        co = compile('%r in globals()' % self.name, '?', 'eval')
        try:
            return frame.is_true(frame.eval(co))
        except passthroughex:
            raise
        except:
            return False

    def is_builtin(self, frame):
        co = compile('%r not in locals() and %r not in globals()' % (
            self.name, self.name), '?', 'eval')
        try:
            return frame.is_true(frame.eval(co))
        except passthroughex:
            raise
        except:
            return False

    def eval(self, frame):
        super(Name, self).eval(frame)
        if not self.is_local(frame):
            self.explanation = self.name

class Compare(Interpretable):
    __view__ = ast.Compare

    def eval(self, frame):
        expr = Interpretable(self.expr)
        expr.eval(frame)
        for operation, expr2 in self.ops:
            expr2 = Interpretable(expr2)
            expr2.eval(frame)
            self.explanation = "%s %s %s" % (
                expr.explanation, operation, expr2.explanation)
            co = compile("__exprinfo_left %s __exprinfo_right" % operation,
                         '?', 'eval')
            try:
                self.result = frame.eval(co, __exprinfo_left=expr.result,
                                             __exprinfo_right=expr2.result)
            except passthroughex:
                raise
            except:
                raise Failure(self)
            if not frame.is_true(self.result):
                break
            expr = expr2

class And(Interpretable):
    __view__ = ast.And

    def eval(self, frame):
        explanations = []
        for expr in self.nodes:
            expr = Interpretable(expr)
            expr.eval(frame)
            explanations.append(expr.explanation)
            self.result = expr.result
            if not frame.is_true(expr.result):
                break
        self.explanation = '(' + ' and '.join(explanations) + ')'

class Or(Interpretable):
    __view__ = ast.Or

    def eval(self, frame):
        explanations = []
        for expr in self.nodes:
            expr = Interpretable(expr)
            expr.eval(frame)
            explanations.append(expr.explanation)
            self.result = expr.result
            if frame.is_true(expr.result):
                break
        self.explanation = '(' + ' or '.join(explanations) + ')'


# == Unary operations ==
keepalive = []
for astclass, astpattern in {
    ast.Not    : 'not __exprinfo_expr',
    ast.Invert : '(~__exprinfo_expr)',
    }.items():
    
    class UnaryArith(Interpretable):
        __view__ = astclass
        
        def eval(self, frame, astpattern=astpattern,
                              co=compile(astpattern, '?', 'eval')):
            expr = Interpretable(self.expr)
            expr.eval(frame)
            self.explanation = astpattern.replace('__exprinfo_expr',
                                                  expr.explanation)
            try:
                self.result = frame.eval(co, __exprinfo_expr=expr.result)
            except passthroughex:
                raise
            except:
                raise Failure(self)

    keepalive.append(UnaryArith)

# == Binary operations ==
for astclass, astpattern in {
    ast.Add    : '(__exprinfo_left + __exprinfo_right)',
    ast.Sub    : '(__exprinfo_left - __exprinfo_right)',
    ast.Mul    : '(__exprinfo_left * __exprinfo_right)',
    ast.Div    : '(__exprinfo_left / __exprinfo_right)',
    ast.Mod    : '(__exprinfo_left % __exprinfo_right)',
    ast.Power  : '(__exprinfo_left ** __exprinfo_right)',
    }.items():
    
    class BinaryArith(Interpretable):
        __view__ = astclass

        def eval(self, frame, astpattern=astpattern,
                              co=compile(astpattern, '?', 'eval')):
            left = Interpretable(self.left)
            left.eval(frame)
            right = Interpretable(self.right)
            right.eval(frame)
            self.explanation = (astpattern
                                .replace('__exprinfo_left',  left .explanation)
                                .replace('__exprinfo_right', right.explanation))
            try:
                self.result = frame.eval(co, __exprinfo_left=left.result,
                                             __exprinfo_right=right.result)
            except passthroughex:
                raise
            except:
                raise Failure(self)
    
    keepalive.append(BinaryArith)


class CallFunc(Interpretable):
    __view__ = ast.CallFunc

    def eval(self, frame):
        node = Interpretable(self.node)
        node.eval(frame)
        explanations = []
        vars = {'__exprinfo_fn': node.result}
        source = '__exprinfo_fn('
        for a in self.args:
            a = Interpretable(a)
            a.eval(frame)
            argname = '__exprinfo_%d' % len(vars)
            vars[argname] = a.result
            source += argname + ','
            explanations.append(a.explanation)
        if self.star_args:
            star_args = Interpretable(self.star_args)
            star_args.eval(frame)
            argname = '__exprinfo_star'
            vars[argname] = star_args.result
            source += '*' + argname + ','
            explanations.append('*' + star_args.explanation)
        if self.dstar_args:
            dstar_args = Interpretable(self.dstar_args)
            dstar_args.eval(frame)
            argname = '__exprinfo_kwds'
            vars[argname] = dstar_args.result
            source += '**' + argname + ','
            explanations.append('**' + dstar_args.explanation)
        self.explanation = "%s(%s)" % (
            node.explanation, ', '.join(explanations))
        if source.endswith(','):
            source = source[:-1]
        source += ')'
        co = compile(source, '?', 'eval')
        try:
            self.result = frame.eval(co, **vars)
        except passthroughex:
            raise
        except:
            raise Failure(self)
        if not node.is_builtin(frame):
            r = frame.repr(self.result)
            self.explanation = '%s\n{%s = %s\n}' % (r, r, self.explanation)

class Getattr(Interpretable):
    __view__ = ast.Getattr

    def eval(self, frame):
        expr = Interpretable(self.expr)
        expr.eval(frame)
        co = compile('__exprinfo_expr.%s' % self.attrname, '?', 'eval')
        try:
            self.result = frame.eval(co, __exprinfo_expr=expr.result)
        except passthroughex: 
            raise
        except:
            raise Failure(self)
        self.explanation = '%s.%s' % (expr.explanation, self.attrname)
        # if the attribute comes from the instance, its value is interesting
        co = compile('hasattr(__exprinfo_expr, "__dict__") and '
                     '%r in __exprinfo_expr.__dict__' % self.attrname,
                     '?', 'eval')
        try:
            from_instance = frame.is_true(
                frame.eval(co, __exprinfo_expr=expr.result))
        except passthroughex:
            raise 
        except:
            from_instance = True
        if from_instance:
            r = frame.repr(self.result)
            self.explanation = '%s\n{%s = %s\n}' % (r, r, self.explanation)

# == Re-interpretation of full statements ==
import __builtin__
BuiltinAssertionError = __builtin__.AssertionError

class Assert(Interpretable):
    __view__ = ast.Assert

    def run(self, frame):
        test = Interpretable(self.test)
        test.eval(frame)
        # simplify 'assert False where False = ...'
        if (test.explanation.startswith('False\n{False = ') and
            test.explanation.endswith('\n}')):
            test.explanation = test.explanation[15:-2]
        # print the result as  'assert <explanation>'
        self.result = test.result
        self.explanation = 'assert ' + test.explanation 
        if not frame.is_true(test.result):
            try:
                raise BuiltinAssertionError
            except passthroughex: 
                raise
            except:
                raise Failure(self)

class Assign(Interpretable):
    __view__ = ast.Assign

    def run(self, frame):
        expr = Interpretable(self.expr)
        expr.eval(frame)
        self.result = expr.result
        self.explanation = '... = ' + expr.explanation
        # fall-back-run the rest of the assignment
        ass = ast.Assign(self.nodes, ast.Name('__exprinfo_expr'))
        mod = ast.Module(None, ast.Stmt([ass]))
        mod.filename = '<run>'
        co = pycodegen.ModuleCodeGenerator(mod).getCode()
        try:
            frame.exec_(co, __exprinfo_expr=expr.result)
        except passthroughex: 
            raise
        except:
            raise Failure(self)

class Discard(Interpretable):
    __view__ = ast.Discard

    def run(self, frame):
        expr = Interpretable(self.expr)
        expr.eval(frame)
        self.result = expr.result
        self.explanation = expr.explanation

class Stmt(Interpretable):
    __view__ = ast.Stmt

    def run(self, frame):
        for stmt in self.nodes:
            stmt = Interpretable(stmt)
            stmt.run(frame)


def report_failure(e):
    explanation = e.node.nice_explanation()
    if explanation:
        explanation = ", in: " + explanation
    else:
        explanation = ""
    print "%s: %s%s" % (e.exc.__name__, e.value, explanation)

def check(s, frame=None):
    if frame is None:
        import sys
        frame = sys._getframe(1)
        frame = RunnerFrame(frame.f_globals, frame.f_locals)
    expr = parse(s, 'eval')
    assert isinstance(expr, ast.Expression)
    node = Interpretable(expr.node)
    try:
        node.eval(frame)
    except passthroughex: 
        raise
    except Failure, e:
        report_failure(e)
    else:
        if not frame.is_true(node.result):
            print "assertion failed:", node.nice_explanation()


###########################################################
# API / Entry points 
# #########################################################

def getframeline(f, lineno=None):
    if lineno is None:
        lineno = f.f_lineno
    co = f.f_code
    
    filename = co.co_filename
    line = magic.dyncode.getline(filename, lineno)
    if line:    
        line = line.strip()
    else: 
        line = None
    return line

def interpret(source, frame):
    module = Interpretable(parse(source, 'exec').node)
    #print "got module", module 
    frame = RunnerFrame(frame.f_globals, frame.f_locals)
    try:
        return module.run(frame)  # None if no exception generated
    except Failure, e:
        return getfailure(e)
    except passthroughex: 
        raise
    except:
        import traceback
        traceback.print_exc()

def gettbline(tb, index=-1):
    tb = magic.dyncode.listtb(tb)[-1] 
    f = tb.tb_frame
    return f, getframeline(f, tb.tb_lineno)

def getmsg((typ, val, tb)):
    #frame, line = gettbline(tb)
    #frame = RunnerFrame(frame.f_globals, frame.f_locals)
    #return interpret(line, frame)

    tb = magic.dyncode.listtb(tb)[-1] 
    source = dyncode.getparseablestartingblock(tb)
    frame = tb.tb_frame 
    x = interpret(source, frame)
    if not isinstance(x, str):
        raise TypeError, "interpret returned non-string %r" % (x,)
    return x

def getfailure(e):
    explanation = e.node.nice_explanation()
    if not str(e.value):
        return "%s: %s" % (e.exc.__name__, explanation)
    else:
        return "%s: %s  << %s" % (e.exc.__name__, explanation, e.value)

def run(s, frame=None):
    if frame is None:
        import sys
        frame = sys._getframe(1)
        frame = RunnerFrame(frame.f_globals, frame.f_locals)
    module = Interpretable(parse(s, 'exec').node)
    try:
        module.run(frame)
    except Failure, e:
        report_failure(e)


if __name__ == '__main__':
    # example:
    def f():
        return 5
    def g():
        return 3
    def h(x):
        return 'never'
    check("f() * g() == 5")
    check("not f()")
    check("not (f() and g() or 0)")
    check("f() == g()")
    i = 4
    check("i == f()")
    check("len(f()) == 0")
    check("isinstance(2+3+4, float)")

    run("x = i")
    check("x == 5")

    run("assert not f(), 'oops'")
    run("a, b, c = 1, 2")
    run("a, b, c = f()")

    check("max([f(),g()]) == 4")
    check("'hello'[g()] == 'h'")
    run("'guk%d' % h(f())")
