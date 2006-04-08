===================================================================
List of things that need to be improved for translation to be saner
===================================================================


 * understand nondeterminism after rtyping
 
 * experiment with different heuristics:
 
    * weigh backedges more (TESTING)
    * consider size of outer function
    * consider number of arguments (TESTING)

 * find a more deterministic inlining order (TESTING using number of callers)

 * experiment with using a base inlining threshold and then drive inlining by
   malloc removal possibilities (using escape analysis)

 * move the inlining of gc helpers just before emitting the code.
   throw the graph away (TESTING, need to do a new framework translation)

 * for gcc: use just one implement file (TRIED: turns out to be a bad idea,
   because gcc uses too much ram). Need to experiment more now that
   inlining should at least be more deterministic!

things to improve the framework gc
==================================

 * find out whether a function can collect

