"""Run code from Guido's Tutorial, to make sure it works under PyPy.

Note that as a script, we have to explicitly print stuff to see it.
"""

##! Section 2.1.2

the_world_is_flat = 1

if the_world_is_flat:
    print "Be careful not to fall off!"

print
##! Section 3.1.1a

print repr(2+2)
print repr((50-5*6)/4)
print repr(7/3)
print repr(7/-3)

width = 20
height = 5*9
print repr(width * height)

x = y = z = 0  # Zero x, y and z
print repr(x)
print repr(y)
print repr(z)


print repr(3 * 3.75 / 1.5)
print repr(7.0 / 2)

print
##! Section 3.1.1b

print repr(1j * 1J)

print repr(1j * complex(0,1))
print repr(3+1j*3)
print repr((3+1j)*3)
print repr((1+2j)/(1+1j))

a=1.5+0.5j
print repr(a.real)
print repr(a.imag)

a=3.0+4.0j
try:
    print repr(float(a))
except TypeError:
    print "Got TypeError for repr(float(a))"
print repr(a.real)
print repr(a.imag)
print repr(abs(a))

print
##! Section 3.1.1c

#Mock up '_' variable use
tax = 12.5 / 100
price = 100.50
print repr(price * tax)
_ = price * tax
print repr(price + _)
_ = price + _
print repr(round(_, 2))

print
##! Section 3.1.2

print repr('spam eggs')
print repr('doesn\'t')
print repr("doesn't")
print repr('"Yes," he said.')
print repr("\"Yes,\" he said.")
print repr('"Isn\'t," she said.')

hello = "This is a rather long string containing\n\
several lines of text just as you would do in C.\n\
    Note that whitespace at the beginning of the line is\
 significant."
print hello
hello = r"This is a rather long string containing\n\
several lines of text much as you would do in C."
print hello
print """
Usage: thingy [OPTIONS] 
     -h                        Display this usage message
     -H hostname               Hostname to connect to
"""

word = 'Help' + 'A'
print repr(word)
print repr('<' + word*5 + '>')
print repr('str' 'ing')
print repr('str'.strip() + 'ing')
print repr(word[4])
print repr(word[0:2])
print repr(word[2:4])
print repr(word[:2])
print repr(word[2:])

try:
    word[0] = 'x'
except TypeError:
    print "Got a TypeError with word[0] = 'x'"
try:
    word[:1] = 'Splat'
except TypeError:
    print "Got a TypeError with word[:1] = 'Splat'"
print repr('x' + word[1:])
print repr('Splat' + word[4])
print repr(word[:2] + word[2:])
print repr(word[:3] + word[3:])

print repr(word[1:100])
print repr(word[10:])
print repr(word[2:1])
print repr(word[-1])
print repr(word[-2])
print repr(word[-2:])
print repr(word[:-2])
print repr(word[-0])

print repr(word[-100:])
try:
    print repr(word[-10])
except IndexError:
    print "Got IndexError with word[-10]"

s = 'supercalifragilisticexpialidocious'
print repr(len(s))

print
##! Section 3.1.3

