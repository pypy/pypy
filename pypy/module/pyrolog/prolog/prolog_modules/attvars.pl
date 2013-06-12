:- module(attvars, [put_attrs/2]).

put_attrs(X, []) :- 
	(nonvar(X)
	->
		throw(error(representation_error(put_attrs/2, 'argument must be unbound (1-st argument)')))
	;
		true
	).
put_attrs(X, att(Attr, Value, Rest)) :-
	(nonvar(X)
	->
		throw(error(representation_error(put_attrs/2, 'argument must be unbound (1-st argument)')))
	;
		put_attr(X, Attr, Value),
		put_attrs(X, Rest)
	).
