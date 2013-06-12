:- module(system, [term_expand/2]).

:- use_module(list).
:- use_module(dcg).
:- use_module(numbervars).
:- use_module(structural_comparison).
:- use_module(unifiable).
:- use_module(attvars).
:- use_module(freeze).
:- use_module(when).
:- use_module(coroutines).

term_expand(A, A) :-
	A \= (_X --> _Y).

term_expand(A, B) :-
	A = (_X --> _Y),
	trans(A, B).
