:- module(structural_comparison, ['=@='/2]).

'=@='(A, B) :-
	copy_term(A, A1),
	copy_term(B, B1),
	numbervars(A1, 0, N),
	numbervars(B1, 0, N),
	A1 == B1.
