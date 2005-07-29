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
declare double %atan2(double,double)
declare double %fmod(double,double)
"""

extfunctions = {}

#functions with a one-to-one C equivalent
simple_functions = [
    ('double %x', ['acos','asin','atan','ceil','cos','cosh','exp','fabs',
                   'floor','log','log10','sin','sinh','sqrt','tan','tanh']),
    ('double %x, double %y', ['atan2','fmod']),
    ]

simple_function_template = """
double %%ll_math_%(function)s(%(params)s) {
    %%t = call double %%%(function)s(%(params)s)
    ret double %%t
}

"""

for params, functions in simple_functions:
    for function in functions:
        extfunctions["%ll_math_" + function] = ((), simple_function_template % locals())
