import compiler
c = compiler.compile('a=1', '', 'exec')
import dis
dis.dis(c)
exec c
print a
