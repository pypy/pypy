extdeclarations = """
;ll_math.py
declare double %acos(double)
declare double %asin(double)
declare double %atan(double)
declare double %ceil(double)
declare double %cos(double)
declare double %cosh(double)
declare double %exp(double)
declare double %fabs(double)
declare double %floor(double)
declare double %log(double)
declare double %log10(double)
declare double %sin(double)
declare double %sinh(double)
declare double %sqrt(double)
declare double %tan(double)
declare double %tanh(double)
"""

extfunctions = {}

simple_math_functions = [
    'acos', 'asin', 'atan', 'ceil', 'cos', 'cosh', 'exp', 'fabs',
    'floor', 'log', 'log10', 'sin', 'sinh', 'sqrt', 'tan', 'tanh'
    ]

func_template = """
double %%ll_math_%(func)s(double %%x) {
    %%t = call double %%%(func)s(double %%x)
    ret double %%t
}

"""

for func in simple_math_functions:
    extfunctions["%ll_math_" + func] = ((), func_template % locals())
