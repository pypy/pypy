import pyllvm
code = open("hello.s").read()
pyllvm.start_ee("modname", code)
