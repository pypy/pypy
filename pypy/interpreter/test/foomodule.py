
__interplevel__exec("w_foo = space.w_Ellipsis")
foo1 = __interplevel__eval("w_foo")  # foo1 is Ellipsis
from __interplevel__ import foo      # Ellipsis too

def bar(a, b):  # visible from interp-level code
    return a * b

__interplevel__execfile("foointerp.py")  # defines w_foo2 and foobuilder()

from __interplevel__ import foo2   # from w_foo2, gives "hello"
from __interplevel__ import foobuilder
foo3 = foobuilder("guido")         # gives "hi, guido!"
