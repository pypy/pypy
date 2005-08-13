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
internal fastcc double %%ll_math_%(function)s(%(params)s) {
    %%t = call ccc double %%%(function)s(%(params)s)
    ret double %%t
}

"""

for params, functions in simple_functions:
    for function in functions:
        extfunctions["%ll_math_" + function] = ((), simple_function_template % locals())

extfunctions["%ll_math_frexp"] = ((), """
internal fastcc %structtype.tuple2.6* %ll_math_frexp(double %x) {
    ; XXX: TODO: ll_math_frexp
    ret %structtype.tuple2.6* null
}
""")

extfunctions["%ll_math_hypot"] = ((), """
internal fastcc double %ll_math_hypot(double %x, double %y) {
    ; XXX: TODO: ll_math_hypot
    ret double 0.0
}
""")

extfunctions["%ll_math_ldexp"] = ((), """
internal fastcc double %ll_math_ldexp(double %x, int %y) {
    ; XXX: TODO: ll_math_ldexp
    ret double 0.0
}
""")

extfunctions["%ll_math_modf"] = ((), """
internal fastcc %structtype.tuple2.7* %ll_math_modf(double %x) {
    ; XXX: TODO: ll_math_modf
    ret %structtype.tuple2.7* null
}
""")

extfunctions["%ll_math_pow"] = ((), """
internal fastcc double %ll_math_pow(double %x, double %y) {
    ; XXX: TODO: ll_math_pow
    ret double 0.0
}
""")
