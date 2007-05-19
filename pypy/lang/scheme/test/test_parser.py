from pypy.lang.scheme.ssparser import *
from pypy.rlib.parsing.parsing import Symbol, Nonterminal

def test_simple_sexpr():
	#parse simple sexpr
	t = parse(r'''(+ 1 2)''')
	assert isinstance(t[0], Nonterminal) 
	assert len(t[0].children) == 3

def test_string():
	#parse string
	t = parse(r'''"don't beleive \"them\""''')
	assert isinstance(t[0], Symbol)

def test_complex_sexpr():
	#parse more complex sexpr
	t = parse(r'''
		(define (fac n) ; comment
			(if (< n 2) n
				(* (fac (- n 1)) n)))
		''')
	assert isinstance(t[0], Nonterminal)
	assert len(t[0].children) == 3
	assert isinstance(t[0].children[0], Symbol)
	assert isinstance(t[0].children[1], Nonterminal)
	assert isinstance(t[0].children[2], Nonterminal)

def test_ident_gen():
	ch_list = "+-*/azAZ09<=>-_~!$%&:?^"
	for char in ch_list:
		yield check_ident_ch, char

def check_ident_ch(char):
	t = parse("(" + char + ")")
	assert isinstance(t[0], Nonterminal)
	assert isinstance(t[0].children[0], Symbol)
