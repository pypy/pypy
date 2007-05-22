
import sys
from StringIO import StringIO

import py

from pypy.lang.js import interpreter
from pypy.lang.js.operations import AEC, Number, Position, Plus
from pypy.lang.js.jsobj import W_Number, W_Object, \
    ExecutionContext, W_Root, ThrowException, w_Null

def test_simple():
    n1 = Number(Position(), 2.0)
    n2 = Number(Position(), 4.0)
    p = Plus(Position(), n1, n2)
    assert p.eval(ExecutionContext()).GetValue().ToNumber() == 6.0
    l = []
    interpreter.writer = l.append

def assert_prints(code, assval):
    l = []
    interpreter.writer = l.append
    js_int = interpreter.Interpreter()
    try:
        if isinstance(code, str):
            js_int.run(interpreter.load_source(code))
        else:
            for codepiece in code:
                js_int.run(interpreter.load_source(codepiece))
    except ThrowException, excpt:
        l.append("uncaught exception: "+str(excpt.exception.ToString()))
    print l, assval
    assert l == assval

def assertp(code, prints):
    l = []
    interpreter.writer = l.append
    jsint = interpreter.Interpreter()
    try:
        jsint.run(interpreter.load_source(code))
    except ThrowException, excpt:
        l.append("uncaught exception: "+str(excpt.exception.ToString()))
    print l, prints
    if isinstance(prints, list):
        assert l == prints
    else:
        assert l[0] == prints

def assertv(code, value):
    jsint = interpreter.Interpreter()
    try:
        code_val = jsint.run(interpreter.load_source(code)).GetValue()
    except ThrowException, excpt:
        code_val = excpt
    print code_val, value
    if isinstance(value, W_Root):
        assert AEC(jsint.global_context, code_val, value) == True
    elif isinstance(value, bool):
        assert code_val.ToBoolean() == value
    elif isinstance(value, int):
        assert code_val.ToInt32() == value
    elif isinstance(value, float):
        assert code_val.ToNumber() == value
    else:
        assert code_val.ToString() == value
    
def test_interp_parse():
    yield assertv, "1+1;", 2
    yield assertp, "print(1+2+3); print(1);", ["6", "1"]
    yield assertp, "print(1,2,3);\n", "1,2,3"

def test_var_assign():
    yield assertv, "x=3;x;", 3
    yield assertv, "x=3;y=4;x+y;", 7

def test_minus():
    assertv("2-1;", 1)

def test_string_var():
    assertv('\"sss\";', 'sss')

def test_string_concat():
    assert_prints('x="xxx"; y="yyy"; print(x+y);', ["xxxyyy"])

def test_string_num_concat():
    assert_prints('x=4; y="x"; print(x+y, y+x);', ["4x,x4"])

def test_to_string():
    assert_prints("x={}; print(x);", ["[object Object]"])

def test_object_access():
    assert_prints("x={d:3}; print(x.d);", ["3"])
    assert_prints("x={d:3}; print(x.d.d);", ["undefined"])
    assert_prints("x={d:3, z:4}; print(x.d+x.z);", ["7"])

def test_object_access_index():
    assert_prints('x={d:"x"}; print(x["d"]);', ["x"])

def test_function_prints():
    py.test.skip("not ready yet")
    assert_prints('x=function(){print(3);}; x();', ["3"])

def test_function_returns():
    py.test.skip("not ready yet")
    assert_prints('x=function(){return 1;}; print(x()+x());', ["2"])
    assert_prints('function x() { return; };', [])

def test_var_declaration():
    yield assertv, 'var x = 3; x;', 3
    yield assertv, 'var x = 3; x+x;', 6

def test_var_scoping():
    py.test.skip("not ready yet")
    assert_prints("""
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

def test_function_args():
    py.test.skip("not ready yet")
    assert_prints("""
    x = function (t,r) {
           return t+r;
    };
    print(x(2,3));
    """, ["5"])

def test_function_less_args():
    py.test.skip("not ready yet")
    assert_prints("""
    x = function (t, r) {
            return t + r;
    };
    print(x(2));
    """, ["NaN"])

def test_function_more_args():
    py.test.skip("not ready yet")
    assert_prints("""
    x = function (t, r) {
            return t + r;
    };
    print(x(2,3,4));
    """, ["5"])

def test_function_has_var():
    py.test.skip("not ready yet")
    assert_prints("""
    x = function () {
            var t = 'test';
            return t;
    };
    print(x());
    """, ["test"])

def test_function_arguments():
    py.test.skip("not ready yet")
    assert_prints("""
    x = function () {
            r = arguments[0];
            t = arguments[1];
            return t + r;
    };
    print(x(2,3));
    """, ["5"])


def test_index():
    yield assertv, """
    x = {1:"test"};
    x[1];
    """, 'test'

def test_array_initializer():
    assert_prints("""
    x = [];
    print(x);
    """, [""])

def test_throw():
    assert_prints("throw(3);", ["uncaught exception: 3"])
    
def test_group():
    assert_prints("print((2+1));", ["3"])

def test_comma():
    py.test.skip("not ready yet")
    assert_prints("print((500,3));", ["3"])

def test_try_catch():
    py.test.skip("not ready yet")
    assert_prints("""
    try {
        throw(3);
    }
    catch (x) {
        print(x);
    }
    """, ["3"])

def test_block():
    assertv("{5;}", W_Number(5))
    assertv("{3; 5;}", W_Number(5))

def test_try_catch_finally():
    py.test.skip("not ready yet")
    assert_prints("""
    try {
        throw(3);
    }
    catch (x) {
        print(x);
    }
    finally {
        print(5);
    }
    """, ["3", "5"])
    
def test_if_then():
    assertp("""
    if (1) {
        print(1);
    }
    """, "1")

def test_if_then_else():
    assertp("""
    if (0) {
        print(1);
    } else {
        print(2);
    }
    """, "2")

def test_compare():
    yield assertv, "1>0;", True
    yield assertv, "0>1;", False
    yield assertv, "0>0;", False
    yield assertv, "1<0;", False
    yield assertv, "0<1;", True
    yield assertv, "0<0;", False
    yield assertv, "1>=0;", True
    yield assertv, "1>=1;", True
    yield assertv, "1>=2;", False
    yield assertv, "0<=1;", True
    yield assertv, "1<=1;", True
    yield assertv, "1<=0;", False
    yield assertv, "0==0;", True
    yield assertv, "1==1;", True
    yield assertv, "0==1;", False
    yield assertv, "0!=1;", True
    yield assertv, "1!=1;", False

def test_binary_op():
    yield assertp, "print(0||0); print(1||0);", ["0", "1"]
    yield assertp, "print(0&&1); print(1&&1);", ["0", "1"]

def test_while():
    assertp("""
    i = 0;
    while (i<3) {
        print(i);
        i = i+1;
    }
    print(i);
    """, ["0","1","2","3"])

def test_object_creation():
    yield assertv, """
    o = new Object();
    o;
    """, "[object Object]"

def test_var_decl():
    py.test.skip("not ready yet")
    assert_prints("print(x); var x;", ["undefined"])
    assert_prints("""
    try {
        print(z);
    }
    catch (e) {
        print(e);
    }
    """, ["ReferenceError: z is not defined"])

def test_function_name():
    py.test.skip("not ready yet")
    assert_prints("""
    function x() {
        print("my name is x");
    }
    x();
    """, ["my name is x"])
        
def test_new_with_function():
    py.test.skip("not ready yet")
    c= """
    x = function() {this.info = 'hello';};
    o = new x();
    print(o.info);
    """
    print c
    assert_prints(c, ["hello"])

def test_vars():
    assert_prints("""
    var x;x=3; print(x);""", ["3"])

def test_in():
    py.test.skip("not ready yet")
    assert_prints("""
    x = {y:3};
    print("y" in x);
    print("z" in x);
    """, ["true", "false"])

def test_append_code():
    assert_prints(["""
    var x; x=3;
    """, """
    print(x);
    z = 2;
    ""","""
    print(z);
    """]
    ,["3", "2"])

def test_for():
    assertp("""
    i = 0;
    for (i; i<3; i++) {
        print(i);
    }
    print(i);
    """, ["0","1","2","3"])

def test_eval():
    assertp("""
    var x = 2;
    eval('x=x+1; print(x); z=2;');
    print(z);
    """, ["3","2"])

def test_arrayobject():
    assertv("""var x = new Array();
    x.length == 0;""", 'true')
     
def test_break():
    assertp("""
    while(1){
        break;
    }
    for(x=0;1==1;x++) {
        break;
    }
    print('out');""", "out")

def test_typeof():
    assertv("""
    var x = 3;
    typeof x == 'number';
    """, True)
    
def test_semicolon():
    assertp(';', [])

def test_newwithargs():
    assertp("""
    var x = new Object(1,2,3,4);
    print(x);
    """, "[object Object]")

def test_increment():
    assertv("""
    var x;
    x = 1;
    x++;
    x;""", 2)
    
def test_ternaryop():
    py.test.skip("not ready yet")
    assert_prints([
    "( 1 == 1 ) ? print('yep') : print('nope');",
    "( 1 == 0 ) ? print('yep') : print('nope');"],
    ["yep","nope"])

def test_booleanliterals():
    assertp("""
    var x = false;
    var y = true;
    print(y);
    print(x);""", ["true", "false"])
    
def test_unarynot():
    assertp("""
    var x = false;
    print(!x);
    print(!!x);""", ["true", "false"])

def test_equals():
    assertv("""
    var x = 5;
    y = z = x;
    y;""", 5)

def test_math_stuff():
    assertp("""
    var x = 5;
    var z = 2;
    print(x*z);
    print(4/z);
    print(isNaN(z));
    print(Math.abs(z-x));
    print(Number.NaN);
    print(Number.POSITIVE_INFINITY);
    print(Number.NEGATIVE_INFINITY);
    print(Math.floor(3.2));
    print(null);
    print(-z);
    """, ['10', '2', 'false', '3', 'NaN', 'Infinity', '-Infinity',
    '3', '', '-2'])
    
def test_globalproperties():
    assertp( """
    print(NaN);
    print(Infinity);
    print(undefined);
    """, ['NaN', 'Infinity', 'undefined'])

def test_strangefunc():
    py.test.skip("not ready yet")
    assert_prints("""function f1() { var z; var t;}""", [])
    assert_prints(""" "'t'"; """, [])
    
def test_null():
    assertv("null;", w_Null)

def test_void():
    assertp("print(void print('hello'));",
                        ["hello", "undefined"])

def test_activationprob():
    py.test.skip("not ready yet")
    assert_prints( """
    function intern (int1){
        print(int1);
        return int1;
    }
    function x (v1){
        this.p1 = v1;
        this.p2 = intern(this.p1);
    }
    var ins = new x(1);
    print(ins.p1);
    print(ins.p2);
    """, ['1','1', '1'])

def test_array_acess():
    py.test.skip("not ready yet")
    assert_prints("""
    var x = new Array();
    x[0] = 1;
    x[x[0]] = 2;
    x[2] = x[0]+x[1];
    for(i=0; i<3; i++){
        print(x[i]);
    }
    """, ['1', '2', '3'])

def test_array_length():
    assertp("""
    var testcases = new Array();
    var tc = testcases.length;
    print('tc'+tc);
    """, 'tc0')

def test_mod_op():
    assertp("print(2%2);", '0')

def test_unary_plus():
    assertp("print(+1);", '1')

def test_delete():
    assertp("""
    var x = {};
    x.y = 1;
    delete x.y;
    print(x.y);
    """, 'undefined')

def test_forin():
    py.test.skip("not ready yet")
    assert_prints("""
    var x = {a:5};
    for(y in x){
        print(y);
    }
    """, ['5',])

def test_stricteq():
    yield assertv, "2 === 2;", True
    yield assertv, "2 === 3;", False
    yield assertv, "2 !== 3;", True
    yield assertv, "2 !== 2;", False

def test_with():
    py.test.skip("not ready yet")
    assert_prints("""
    var mock = {x:2};
    var x=4;
    print(x);
    try {
        with(mock) {
            print(x);
            throw 3;
            print("not reacheable");
        }
    }
    catch(y){
        print(y);
    }
    print(x);
    """, ['4', '2', '3', '4'])

def test_bitops():
    yield assertv, "2 ^ 2;", 0
    yield assertv, "2 & 3;", 2
    yield assertv, "2 | 3;", 3

def test_for_strange():
    py.test.skip("not ready yet")
    assert_prints("""
    for (var arg = "", i = 0; i < 2; i++) { print(i);}
    """, ['0', '1'])

def test_recursive_call():
    py.test.skip("not ready yet")
    assert_prints("""
    function fact(x) { if (x == 0) { return 1; } else { return fact(x-1)*x; }}
    print(fact(3));
    """, ['6',])

def test_function_prototype():
    py.test.skip("not ready yet")
    assert_prints("""
    function foo() {}; foo.prototype.bar = function() {};
    """, [])


def test_function_this():
    py.test.skip("not ready yet")
    assert_prints("""
    function foo() {print("debug");this.bar = function() {};};
    var f = new foo();
    f.bar();
    """, ['debug',])
    
