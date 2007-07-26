
import py
from pypy.lang.js import interpreter
from pypy.lang.js.operations import AEC, Number, Position, Plus
from pypy.lang.js.jsobj import W_Number, W_Object, \
    ExecutionContext, W_Root, ThrowException, w_Null

def test_simple():
    n1 = Number(Position(), 2.0)
    n2 = Number(Position(), 4.0)
    p = Plus(Position(), n1, n2)
    assert p.eval(ExecutionContext([W_Object(),])).GetValue().ToNumber() == 6.0
    l = []
    interpreter.writer = l.append

def assertp(code, prints):
    l = []
    interpreter.writer = l.append
    jsint = interpreter.Interpreter()
    ctx = jsint.w_Global
    try:
        jsint.run(interpreter.load_source(code, ''))
    except ThrowException, excpt:
        l.append("uncaught exception: "+str(excpt.exception.ToString(ctx)))
    print l, prints
    if isinstance(prints, list):
        assert l == prints
    else:
        assert l[0] == prints

def assertv(code, value):
    jsint = interpreter.Interpreter()
    ctx = jsint.w_Global
    try:
        code_val = jsint.run(interpreter.load_source(code, '')).GetValue()
    except ThrowException, excpt:
        code_val = excpt.exception
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
        assert code_val.ToString(ctx) == value

def asserte(code, value):
    jsint = interpreter.Interpreter()
    py.test.raises(value, 'jsint.run(interpreter.load_source(code, ""))')
    
    
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
    assertp('x="xxx"; y="yyy"; print(x+y);', "xxxyyy")

def test_string_num_concat():
    assertp('x=4; y="x"; print(x+y, y+x);', ["4x,x4"])

def test_to_string():
    assertp("x={}; print(x);", ["[object Object]"])

def test_object_access():
    yield assertp, "x={d:3}; print(x.d);", "3"
    yield assertp, "x={d:3}; print(x.d.d);", "undefined"
    yield assertp, "x={d:3, z:4}; print(x.d+x.z);", "7"

def test_object_access_index():
    assertp('x={d:"x"}; print(x["d"]);', 'x')

def test_function_prints():
    assertp('x=function(){print(3);}; x();', '3')

def test_function_returns():
    yield assertv, 'x=function(){return 1;}; x()+x();', 2
    yield assertp, 'function x() { return; };', []
    yield assertv, 'function x() { d=2; return d;}; x()', 2

def test_var_declaration():
    yield assertv, 'var x = 3; x;', 3
    yield assertv, 'var x = 3; x+x;', 6

def test_var_scoping():
    assertp("""
    var y;
    var p;
    p = 0;
    function x () {
        var p;
        p = 1;
        y = 3; return y + z;
    };
    var z = 2;
    print(x(), y, p);
    """, ["5,3,0"])

def test_function_args():
    assertv("""
    x = function (t,r) {
           return t+r;
    };
    x(2,3);
    """, 5)

def test_function_less_args():
    assertp("""
    x = function (t, r) {
            return t + r;
    };
    print(x(2));
    """, "NaN")

def test_function_more_args():
    assertv("""
    x = function (t, r) {
            return t + r;
    };
    x(2,3,4);
    """, 5)

def test_function_has_var():
    assertv("""
    x = function () {
            var t = 'test';
            return t;
    };
    x();
    """, 'test')

def test_function_arguments():
    assertv("""
    x = function () {
            r = arguments[0];
            t = arguments[1];
            return t + r;
    };
    x(2,3);
    """, 5)


def test_index():
    assertv("""
    x = {1:"test"};
    x[1];
    """, 'test')

def test_array_initializer():
    assertp("""
    x = [];
    print(x);
    print(x.length)
    """, ['', '0'])

def test_throw():
    assertp("throw(3);", "uncaught exception: 3")
    
def test_group():
    assertv("(2+1);", 3)

def test_comma():
    assertv("(500,3);", 3)

def test_block():
    yield assertv, "{5;}", 5
    yield assertv, "{3; 5;}", 5

def test_try_catch_finally():
    yield assertp, """
    try {
        throw(3);
    }
    catch (x) {
        print(x);
    }
    """, "3"
    yield assertp, """
    try {
        throw(3);
    }
    catch (x) {
        print(x);
    }
    finally {
        print(5);
    }
    """, ["3", "5"]
    
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
    yield assertv, "1===1;", True
    yield assertv, "1!==1;", False

def test_string_compare():
    yield assertv, "'aaa' > 'a';", True
    yield assertv, "'aaa' < 'a';", False
    yield assertv, "'a' > 'a';", False

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
    yield assertp, "print(x); var x;", "undefined"
    yield assertp, """
    try {
        print(z);
    }
    catch (e) {
        print(e);
    }
    """, "ReferenceError: z is not defined"

def test_function_name():
    assertp("""
    function x() {
        print("my name is x");
    }
    x();
    """, "my name is x")
        
def test_new_with_function():
    c= """
    x = function() {this.info = 'hello';};
    o = new x();
    o.info;
    """
    assertv(c, "hello")

def test_vars():
    assertp("""
    var x;x=3; print(x);""", ["3"])

def test_in():
    assertp("""
    x = {y:3};
    print("y" in x);
    print("z" in x);
    """, ["true", "false"])

def test_for():
    assertp("""
    i = 0;
    for (i; i<3; i++) {
        print(i);
    }
    print(i);
    """, ["0","1","2","3"])

def test_eval():
    yield assertp, """
    var x = 2;
    eval('x=x+1; print(x); z=2;');
    print(z);
    """, ["3","2"]
    yield asserte, "eval('var do =true;');", ThrowException

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
    """, '1')

def test_increment():
    assertv("""
    var x;
    x = 1;
    x++;
    x;""", 2)
    
def test_ternaryop():
    yield assertv, "( 1 == 1 ) ? true : false;", True
    yield assertv, "( 1 == 0 ) ? true : false;", False

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
    assertp("""function f1() { var z; var t;}""", [])
    assertp(""" "'t'"; """, [])
    
def test_null():
    assertv("null;", w_Null)

def test_void():
    assertp("print(void print('hello'));",
                        ["hello", "undefined"])

def test_activationprob():
    assertp( """
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
    assertp("""
    var x = new Array();
    x[0] = 1;
    print(x[0]);
    x[x[0]] = 2;
    print(x[1]);
    x[2] = x[0]+x[1];
    for(i=0; i<3; i++){
        print(x[i]);
    }
    """, ['1','2', '1', '2', '3'])

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
    assertp("""
    var x = {a:5};
    for(y in x){
        print(y);
    }
    """, ['5',])

def test_forinvar():
    assertp("""
    var x = {a:5};
    for(var y in x){
        print(y);
    }
    """, ['5',])

def test_stricteq():
    yield assertv, "2 === 2;", True
    yield assertv, "2 === 3;", False
    yield assertv, "2 !== 3;", True
    yield assertv, "2 !== 2;", False

def test_with():
    assertp("""
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
    yield assertv, "2 << 2;", 8
    yield assertv, "4 >> 2;", 1
    yield assertv, "-2 >> 31", -1
    yield assertv, "-2 >>> 31;", 1

def test_for_vararg():
    assertp("""
    for (var arg = "", i = 0; i < 2; i++) { print(i);}
    """, ['0', '1'])

def test_recursive_call():
    assertv("""
    function fact(x) { if (x == 0) { return 1; } else { return fact(x-1)*x; }}
    fact(3);
    """, 6)

def test_function_prototype():
    assertp("""
    function foo() {}; foo.prototype.bar = function() {};
    """, [])


def test_function_this():
    assertp("""
    function foo() {print("debug");this.bar = function() {};};
    var f = new foo();
    f.bar();
    """, 'debug')
    
def test_inplace_assign():
    yield assertv, "x=1; x+=1; x;", 2
    yield assertv, "x=1; x-=1; x;", 0
    yield assertv, "x=2; x*=2; x;", 4
    yield assertv, "x=2; x/=2; x;", 1
    yield assertv, "x=4; x%=2; x;", 0
    yield assertv, "x=2; x&=2; x;", 2
    yield assertv, "x=0; x|=1; x;", 1
    yield assertv, "x=2; x^=2; x;", 0

def test_twoarray():
    assertp("""
    a1 = new Array();
    a2 = new Array();
    a1[0] = 1;
    print(a1[0]);
    a2[0] = 2;
    print(a1[0]);
    """, ['1', '1'])
    
def test_semicolon():
    assertv("1", 1)

def test_functionjs():
    assertv("x = Function('return 1'); x()", 1)

def test_octal_and_hex():
    yield assertv, "010;", 8
    yield assertv, "0xF", 15

def test_switch():
    py.test.skip("not ready yet")
    yield assertv, """
    x = 1;
    switch(x){
        case 1: 15; break;
        default: 30;
    };""", 15
    yield assertv, """
    x = 1;
    switch(x){
        case 1: 15; break;
        default: 30;
    };""", 15

def test_autoboxing():
    yield assertv, "'abc'.charAt(0)", 'a'
    yield assertv, "true.toString()", 'true'
    yield assertv, "x=5; x.toString();", '5'

def test_proper_prototype_inheritance():
    yield assertv, """
    Object.prototype.my = function() {return 1};
    x = {};
    x.my();
    """, 1
    yield assertv, """
    Function.prototype.my = function() {return 1};
    function x () {};
    x.my();
    """, 1
    
def test_new_without_args_really():
    assertv("var x = new Boolean; x.toString();", 'false')

