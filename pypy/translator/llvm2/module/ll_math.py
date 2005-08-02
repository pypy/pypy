extdeclarations = """
;ll_math.py
declare ccc double %acos(double)
declare ccc double %asin(double)
declare ccc double %atan(double)
declare ccc double %ceil(double)
declare ccc double %cos(double)
declare ccc double %cosh(double)
declare ccc double %exp(double)
declare ccc double %fabs(double)
declare ccc double %floor(double)
declare ccc double %log(double)
declare ccc double %log10(double)
declare ccc double %sin(double)
declare ccc double %sinh(double)
declare ccc double %sqrt(double)
declare ccc double %tan(double)
declare ccc double %tanh(double)
declare ccc double %atan2(double,double)
declare ccc double %fmod(double,double)
"""

extfunctions = {}

#functions with a one-to-one C equivalent
simple_functions = [
    ('double %x', ['acos','asin','atan','ceil','cos','cosh','exp','fabs',
                   'floor','log','log10','sin','sinh','sqrt','tan','tanh']),
    ('double %x, double %y', ['atan2','fmod']),
    ]

simple_function_template = """
fastcc double %%ll_math_%(function)s(%(params)s) {
    %%t = call ccc double %%%(function)s(%(params)s)
    ret double %%t
}

"""

for params, functions in simple_functions:
    for function in functions:
        extfunctions["%ll_math_" + function] = ((), simple_function_template % locals())
