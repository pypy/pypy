:- module(freeze, []).

attr_unify_hook(Goal, X) :-
    (attvar(X) 
    ->
	    coroutines:put_freeze_attribute(X, Goal)
    ;
	    call(Goal)
    ).

