
import sys
from StringIO import StringIO

import py.test

from pypy.lang.js import interpreter
from pypy.lang.js.jsparser import parse
from pypy.lang.js.interpreter import *
from pypy.lang.js.jsobj import W_Number, W_Object, ExecutionContext


def js_is_on_path():
    if py.path.local.sysfind("js") is None:
        py.test.skip("js binary not found")

js_is_on_path()

class TestInterp(object):
    def test_simple(self):
        p = Plus()
        n1 = Number()
        n2 = Number()
        n1.num = 2
        n2.num = 4
        p.left = n1
        p.right = n2
        assert p.eval(ExecutionContext()).GetValue().ToNumber() == 6
        l = []
        interpreter.writer = l.append
        # Script([Semicolon(Call(Identifier('print', None), 
        #                 List([Number(1), Number(2)])))],[],[]).execute(ExecutionContext())
        #         assert l == ['1,2']

    def assert_prints(self, code, assval):
        l = []
        interpreter.writer = l.append
        js_int = interpreter.Interpreter()
        try:
            if isinstance(code, str):
                js_int.run(load_source(code))
            else:
                for codepiece in code:
                    js_int.run(load_source(codepiece))
        except ThrowException, excpt:
            l.append("uncaught exception: "+str(excpt.exception))
        print l, assval
        assert l == assval
    
    def assert_result(self, code, result):
        inter = interpreter.Interpreter()
        r = inter.run(load_source(code))
        assert r.ToString() == result.ToString()
        
    def test_interp_parse(self):
        self.assert_prints("print(1+1)", ["2"])
        self.assert_prints("print(1+2+3); print(1)", ["6", "1"])
        self.assert_prints("print(1,2,3);\n", ["1,2,3"])

    def test_var_assign(self):
        self.assert_prints("x=3;print(x);", ["3"])
        self.assert_prints("x=3;y=4;print(x+y);", ["7"])

    def test_minus(self):
        self.assert_prints("print(2-1)", ["1"])
    
    def test_string_var(self):
        self.assert_prints('print(\"sss\");', ["sss"])
    
    def test_string_concat(self):
        self.assert_prints('x="xxx"; y="yyy"; print(x+y);', ["xxxyyy"])
    
    def test_string_num_concat(self):
        self.assert_prints('x=4; y="x"; print(x+y, y+x);', ["4x,x4"])

    def test_to_string(self):
        self.assert_prints("x={}; print(x);", ["[object Object]"])

    def test_object_access(self):
        self.assert_prints("x={d:3}; print(x.d);", ["3"])
        self.assert_prints("x={d:3}; print(x.d.d);", ["undefined"])
        self.assert_prints("x={d:3, z:4}; print(x.d+x.z);", ["7"])

    def test_object_access_index(self):
        self.assert_prints('x={d:"x"}; print(x["d"]);', ["x"])
    
    def test_function_prints(self):
        self.assert_prints('x=function(){print(3);}; x();', ["3"])
    
    def test_function_returns(self):
        self.assert_prints('x=function(){return 1;}; print(x()+x());', ["2"])
        self.assert_prints('function x() { return }', [])
    
    def test_var_declaration(self):
        self.assert_prints('var x = 3; print(x);', ["3"])
        self.assert_prints('var x = 3; print(x+x);', ["6"])

    def test_var_scoping(self):
        self.assert_prints("""
        var y;
        var p;
        p = 0;
        x = function() {
            var p;
            p = 1;
            y = 3; return y + z;
        };
        var z = 2;
        print(x(), y, p);
        """, ["5,3,0"])

    def test_function_args(self):
        self.assert_prints("""
        x = function (t,r) {
               return t+r;
        };
        print(x(2,3));
        """, ["5"])

    def test_function_less_args(self):
        self.assert_prints("""
        x = function (t, r) {
                return t + r;
        };
        print(x(2));
        """, ["NaN"])

    def test_function_more_args(self):
        self.assert_prints("""
        x = function (t, r) {
                return t + r;
        };
        print(x(2,3,4));
        """, ["5"])

    def test_function_has_var(self):
        self.assert_prints("""
        x = function () {
                var t = 'test';
                return t;
        };
        print(x());
        """, ["test"])

    def test_function_arguments(self):
        self.assert_prints("""
        x = function () {
                r = arguments[0];
                t = arguments[1];
                return t + r;
        };
        print(x(2,3));
        """, ["5"])


    def test_index(self):
        self.assert_prints("""
        x = {1:"test"};
        print(x[1]);
        """, ["test"])

    def test_array_initializer(self):
        self.assert_prints("""
        x = [];
        print(x);
        """, [""])

    def test_throw(self):
        self.assert_prints("throw(3)", ["uncaught exception: 3"])
        
    def test_group(self):
        self.assert_prints("print((2+1))", ["3"])

    def test_comma(self):
        self.assert_prints("print((500,3))", ["3"])
    
    def test_try_catch(self):
        self.assert_prints("""
        try {
            throw(3);
        }
        catch (x) {
            print(x);
        }
        """, ["3"])
    
    def test_block(self):
        self.assert_result("{ 5}", W_Number(5))
        self.assert_result("{3; 5}", W_Number(5))
    
    def test_try_catch_finally(self):
        self.assert_prints("""
        try {
            throw(3);
        }
        catch (x) {
            print(x);
        }
        finally {
            print(5)
        }
        """, ["3", "5"])
        
    def test_if_then(self):
        self.assert_prints("""
        if (1) {
            print(1);
        }
        """, ["1"])

    def test_if_then_else(self):
        self.assert_prints("""
        if (0) {
            print(1);
        } else {
            print(2);
        }
        """, ["2"])

    def test_compare(self):
        self.assert_prints("print(1>0)",["true"])
        self.assert_prints("print(0>1)",["false"])
        self.assert_prints("print(0>0)",["false"])
        self.assert_prints("print(1<0)",["false"])
        self.assert_prints("print(0<1)",["true"])
        self.assert_prints("print(0<0)",["false"])
        self.assert_prints("print(1>=0)",["true"])
        self.assert_prints("print(1>=1)",["true"])
        self.assert_prints("print(1>=2)",["false"])
        self.assert_prints("print(0<=1)",["true"])
        self.assert_prints("print(1<=1)",["true"])
        self.assert_prints("print(1<=0)",["false"])
        self.assert_prints("print(0==0)",["true"])
        self.assert_prints("print(1==1)",["true"])
        self.assert_prints("print(0==1)",["false"])
        self.assert_prints("print(0!=1)",["true"])
        self.assert_prints("print(1!=1)",["false"])

    def test_binary_op(self):
        self.assert_prints("print(0||0); print(1||0)",["0", "1"])
        self.assert_prints("print(0&&1); print(1&&1)",["0", "1"])
    
    def test_while(self):
        self.assert_prints("""
        i = 0;
        while (i<3) {
            print(i);
            i = i+1;
        }
        print(i);
        """, ["0","1","2","3"])

    def test_object_creation(self):
        self.assert_prints("""
        o = new Object();
        print(o);
        """, ["[object Object]"])

    def test_var_decl(self):
        self.assert_prints("print(x); var x;", ["undefined"])
        self.assert_prints("""
        try {
            print(z);
        }
        catch (e) {
            print(e)
        }
        """, ["ReferenceError: z is not defined"])

    def test_function_name(self):
        self.assert_prints("""
        function x() {
            print("my name is x");
        }
        x();
        """, ["my name is x"])
            
    def test_new_with_function(self):
        c= """
        x = function() {this.info = 'hello';};
        o = new x();
        print(o.info);
        """
        print c
        self.assert_prints(c, ["hello"])

    def test_vars(self):
        self.assert_prints("""
        var x;x=3; print(x)""", ["3"])

    def test_minus(self):
        self.assert_prints("""
        x = {y:3};
        print("y" in x);
        print("z" in x);
        """, ["true", "false"])
    
    def test_append_code(self):
        self.assert_prints(["""
        var x; x=3;
        """, """
        print(x);
        z = 2;
        ""","""
        print(z)
        """]
        ,["3", "2"])
    
    def test_for(self):
        self.assert_prints("""
        for (i=0; i<3; i++) {
            print(i);
        }
        print(i);
        """, ["0","1","2","3"])
    
    def test_eval(self):
        self.assert_prints("""
        var x = 2;
        eval('x=x+1; print(x); z=2');
        print(z);
        """, ["3","2"])

    def test_arrayobject(self):
        self.assert_prints("""var x = new Array();
        print(x.length == 0)""", ['true'])
         
    def test_break(self):
        self.assert_prints("""
        while(1){
            break;
        }
        for(x=0;1==1;x++) {
            break;
        }
        print('out')""", ["out"])

    def test_typeof(self):
        self.assert_result("""
        var x = 3;
        typeof x == 'number'
        """, W_Boolean(True))
        
    def test_semicolon(self):
        self.assert_prints(';', [])

    def test_newwithargs(self):
        self.assert_prints("""
        var x = new Object(1,2,3,4);
        print(x)
        """, ["[object Object]"])

    def test_increment(self):
        self.assert_prints("""
        var x;
        x = 1
        x++
        print(x)""", ["2"])
        
    def test_ternaryop(self):
        self.assert_prints([
        "( 1 == 1 ) ? print('yep') : print('nope');",
        "( 1 == 0 ) ? print('yep') : print('nope');"],
        ["yep","nope"])

    def test_booleanliterals(self):
        self.assert_prints("""
        var x = false;
        var y = true;
        print(y)
        print(x)""", ["true", "false"])
        
    def test_unarynot(self):
        self.assert_prints("""
        var x = false;
        print(!x)
        print(!!x)""", ["true", "false"])

    def test_equals(self):
        self.assert_prints("""
        var x = 5;
        y = z = x
        print(y)""", ["5"])
    
    def test_math_stuff(self):
        self.assert_prints("""
        var x = 5;
        var z = 2;
        print(x*z)
        print(4/z)
        print(isNaN(z))
        print(Math.abs(z-x))
        print(Number.NaN)
        print(Number.POSITIVE_INFINITY)
        print(Number.NEGATIVE_INFINITY)
        print(Math.floor(3.2))
        print(null)
        print(-z)
        """, ['10', '2', 'false', '3', 'NaN', 'inf', '-inf', '3', '', '-2'])
        
    def test_globalproperties(self):
        self.assert_prints( """
        print(NaN)
        print(Infinity)
        print(undefined)
        """, ['NaN', 'inf', 'undefined'])

    def test_strangefunc(self):
        self.assert_prints("""function f1() { var z; var t;}""", [])
        self.assert_prints(""" "'t'" """, [])
        
    def test_null(self):
        self.assert_result("null", w_Null)

    def test_void(self):
        self.assert_prints("print(void print('hello'))",
                            ["hello", "undefined"])

    def test_activationprob(self):
        self.assert_prints( """
        function intern (int1){
            print(int1);
            return int1;
        }
        function x (v1){
            this.p1 = v1
            this.p2 = intern(this.p1)
        }
        var ins = new x(1)
        print(ins.p1)
        print(ins.p2)
        """, ['1','1', '1'])

    def test_array_acess(self):
        self.assert_prints("""
        var x = new Array()
        x[0] = 1;
        x[x[0]] = 2;
        x[2] = x[0]+x[1];
        for(i=0; i<3; i++){
            print(x[i]);
        }
        """, ['1', '2', '3'])
    
    def test_array_length(self):
        self.assert_prints("""
        var testcases = new Array();
        var tc = testcases.length;
        print('tc'+tc) 
        """, ['tc0'])
    
    def test_mod_op(self):
        self.assert_prints("print(2%2)", ['0'])
    
    def test_unary_plus(self):
        self.assert_prints("print(+1)", ['1'])

    def test_delete(self):
        self.assert_prints("""
        var x = {}
        x.y = 1;
        delete x.y
        print(x.y)
        """, ['undefined'])

    def test_forin(self):
        self.assert_prints("""
        var x = {a:5}
        for(y in x){
            print(y)
        }
        """, ['5',])

    def test_stricteq(self):
        self.assert_prints("""
        print(2 === 2)
        print(2 === 3)
        print(2 !== 3)
        print(2 !== 2)    
        """, ['true', 'false', 'true', 'false'])
