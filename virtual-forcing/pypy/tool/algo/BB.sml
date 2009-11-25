(*
    Copyright 1992-1996 Stephen Adams.

    This software may be used freely provided that:
      1. This copyright notice is attached to any copy, derived work,
         or work including all or part of this software.
      2. Any derived work must contain a prominent notice stating that
         it has been altered from the original.

*)

(* Address:  Electronics & Computer Science
             University of Southampton
	     Southampton  SO9 5NH
	     Great Britian
   E-mail:   sra@ecs.soton.ac.uk

   Comments:

     1.  The implementation is based on Binary search trees of Bounded
         Balance, similar to Nievergelt & Reingold, SIAM J. Computing
         2(1), March 1973.  The main advantage of these trees is that
         they keep the size of the tree in the node, giving a constant
         time size operation.

     2.  The bounded balance criterion is simpler than N&R's alpha.
         Simply, one subtree must not have more than `weight' times as
         many elements as the opposite subtree.  Rebalancing is
         guaranteed to reinstate the criterion for weight>2.23, but
         the occasional incorrect behaviour for weight=2 is not
         detrimental to performance.

     3.  There are two implementations of union.  The default,
         hedge_union, is much more complex and usually 20% faster.  I
         am not sure that the performance increase warrants the
         complexity (and time it took to write), but I am leaving it
         in for the competition.  It is derived from the original
         union by replacing the split_lt(gt) operations with a lazy
         version. The `obvious' version is called old_union.
*)

structure B (*: INTSET*) =
    struct

	local

	    type T = int
	    val lt : T*T->bool = op <

	    (* weight is a parameter to the rebalancing process. *)
	    val weight:int = 3

	    datatype  Set = E | T of T * int * Set * Set

	    fun size E = 0
	      | size (T(_,n,_,_)) = n
	    
	    (*fun N(v,l,r) = T(v,1+size(l)+size(r),l,r)*)
	    fun N(v,E,              E)               = T(v,1,E,E)
	      | N(v,E,              r as T(_,n,_,_)) = T(v,n+1,E,r)
	      | N(v,l as T(_,n,_,_),E)               = T(v,n+1,l,E)
	      | N(v,l as T(_,n,_,_),r as T(_,m,_,_)) = T(v,n+m+1,l,r)

	    fun single_L (a,x,T(b,_,y,z)) = N(b,N(a,x,y),z)
	      | single_L _ = raise Match
	    fun single_R (b,T(a,_,x,y),z) = N(a,x,N(b,y,z))
	      | single_R _ = raise Match
	    fun double_L (a,w,T(c,_,T(b,_,x,y),z)) = N(b,N(a,w,x),N(c,y,z))
	      | double_L _ = raise Match
	    fun double_R (c,T(a,_,w,T(b,_,x,y)),z) = N(b,N(a,w,x),N(c,y,z))
	      | double_R _ = raise Match

	    fun T' (v,E,E) = T(v,1,E,E)
	      | T' (v,E,r as T(_,_,E,E))     = T(v,2,E,r)
	      | T' (v,l as T(_,_,E,E),E)     = T(v,2,l,E)

	      | T' (p as (_,E,T(_,_,T(_,_,_,_),E))) = double_L p
	      | T' (p as (_,T(_,_,E,T(_,_,_,_)),E)) = double_R p

	      (* these cases almost never happen with small weight*)
	      | T' (p as (_,E,T(_,_,T(_,ln,_,_),T(_,rn,_,_)))) =
		if ln<rn then single_L p else double_L p
	      | T' (p as (_,T(_,_,T(_,ln,_,_),T(_,rn,_,_)),E)) =
		if ln>rn then single_R p else double_R p

	      | T' (p as (_,E,T(_,_,E,_)))  = single_L p
	      | T' (p as (_,T(_,_,_,E),E))  = single_R p

	      | T' (p as (v,l as T(lv,ln,ll,lr),r as T(rv,rn,rl,rr))) =
		if rn>=weight*ln then (*right is too big*)
		    let val rln = size rl
			val rrn = size rr
		    in
			if rln < rrn then  single_L p  else  double_L p
		    end
		    
		else if ln>=weight*rn then  (*left is too big*)
		    let val lln = size ll
			val lrn = size lr
		    in
			if lrn < lln then  single_R p  else  double_R p
		    end

		else
	             T(v,ln+rn+1,l,r)

	    fun add (E,x) = T(x,1,E,E)
	      | add (set as T(v,_,l,r),x) =
	        if lt(x,v) then T'(v,add(l,x),r)
		else if lt(v,x) then T'(v,l,add(r,x))
		     else set

	    fun concat3 (E,v,r) = add(r,v)
	      | concat3 (l,v,E) = add(l,v)
	      | concat3 (l as T(v1,n1,l1,r1), v, r as T(v2,n2,l2,r2)) =
		if weight*n1 < n2 then T'(v2,concat3(l,v,l2),r2)
		else if weight*n2 < n1 then T'(v1,l1,concat3(r1,v,r))
		     else N(v,l,r)

	    fun split_lt (E,x) = E
	      | split_lt (t as T(v,_,l,r),x) =
		if lt(x,v) then split_lt(l,x)
		else if lt(v,x) then concat3(l,v,split_lt(r,x))
		     else l

	    fun split_gt (E,x) = E
	      | split_gt (t as T(v,_,l,r),x) =
		if lt(v,x) then split_gt(r,x)
		else if lt(x,v) then concat3(split_gt(l,x),v,r)
		     else r

	    fun min (T(v,_,E,_)) = v
	      | min (T(v,_,l,_)) = min l
	      | min _            = raise Match
		
	    and delete' (E,r) = r
	      | delete' (l,E) = l
	      | delete' (l,r) = let val min_elt = min r in
                          		T'(min_elt,l,delmin r)
				end
	    and delmin (T(_,_,E,r)) = r
	      | delmin (T(v,_,l,r)) = T'(v,delmin l,r)
	      | delmin _ = raise Match

	    fun concat (E,  s2) = s2
	      | concat (s1, E)  = s1
	      | concat (t1 as T(v1,n1,l1,r1), t2 as T(v2,n2,l2,r2)) =
		if weight*n1 < n2 then T'(v2,concat(t1,l2),r2)
		else if weight*n2 < n1 then T'(v1,l1,concat(r1,t2))
		     else T'(min t2,t1, delmin t2)

	    fun fold(f,base,set) =
		let fun fold'(base,E) = base
		      | fold'(base,T(v,_,l,r)) = fold'(f(v,fold'(base,r)),l)
		in 
		    fold'(base,set)
		end

	in

	    val empty = E
		
	    fun singleton x = T(x,1,E,E)


	    local
		fun trim (lo,hi,E) = E
		  | trim (lo,hi,s as T(v,_,l,r)) =
		    if  lt(lo,v)  then
			if  lt(v,hi)  then  s
			else  trim(lo,hi,l)
		    else trim(lo,hi,r)

			    
		fun uni_bd (s,E,lo,hi) = s
		  | uni_bd (E,T(v,_,l,r),lo,hi) = 
		     concat3(split_gt(l,lo),v,split_lt(r,hi))
		  | uni_bd (T(v,_,l1,r1), s2 as T(v2,_,l2,r2),lo,hi) =
			concat3(uni_bd(l1,trim(lo,v,s2),lo,v),
				v, 
				uni_bd(r1,trim(v,hi,s2),v,hi))
	          (* inv:  lo < v < hi *)

               (*all the other versions of uni and trim are
               specializations of the above two functions with
               lo=-infinity and/or hi=+infinity *)

		fun trim_lo (_ ,E) = E
		  | trim_lo (lo,s as T(v,_,_,r)) =
		        if lt(lo,v) then s else trim_lo(lo,r)
		fun trim_hi (_ ,E) = E
		  | trim_hi (hi,s as T(v,_,l,_)) =
		        if lt(v,hi) then s else trim_hi(hi,l)
			    
		fun uni_hi (s,E,hi) = s
		  | uni_hi (E,T(v,_,l,r),hi) = 
		     concat3(l,v,split_lt(r,hi))
		  | uni_hi (T(v,_,l1,r1), s2 as T(v2,_,l2,r2),hi) =
			concat3(uni_hi(l1,trim_hi(v,s2),v),
				v, 
				uni_bd(r1,trim(v,hi,s2),v,hi))

		fun uni_lo (s,E,lo) = s
		  | uni_lo (E,T(v,_,l,r),lo) = 
		     concat3(split_gt(l,lo),v,r)
		  | uni_lo (T(v,_,l1,r1), s2 as T(v2,_,l2,r2),lo) =
			concat3(uni_bd(l1,trim(lo,v,s2),lo,v),
				v, 
				uni_lo(r1,trim_lo(v,s2),v))

		fun uni (s,E) = s
		  | uni (E,s as T(v,_,l,r)) = s
		  | uni (T(v,_,l1,r1), s2 as T(v2,_,l2,r2)) =
			concat3(uni_hi(l1,trim_hi(v,s2),v),
				v, 
				uni_lo(r1,trim_lo(v,s2),v))

	    in
		val hedge_union = uni
	    end


	    fun old_union (E,s2)  = s2
	      | old_union (s1,E)  = s1
	      | old_union (s1 as T(v,_,l,r),s2) = 
		let val l2 = split_lt(s2,v)
		    val r2 = split_gt(s2,v)
		in
		    concat3(old_union(l,l2),v,old_union(r,r2))
		end

            (* The old_union version is about 20% slower than
               hedge_union in most cases *)

	    val union = hedge_union
	    (*val union = old_union*)

	    val add = add

	    fun difference (E,s)  = E
	      | difference (s,E)  = s
	      | difference (s, T(v,_,l,r)) =
		let val l2 = split_lt(s,v)
		    val r2 = split_gt(s,v)
		in
		    concat(difference(l2,l),difference(r2,r))
		end

	    fun member (x,set) =
		let fun mem E = false
		      | mem (T(v,_,l,r)) =
			if lt(x,v) then mem l else if lt(v,x) then mem r else true
		in mem set end

	    (*fun intersection (a,b) = difference(a,difference(a,b))*)

	    fun intersection (E,_) = E
	      | intersection (_,E) = E
	      | intersection (s, T(v,_,l,r)) =
		let val l2 = split_lt(s,v)
		    val r2 = split_gt(s,v)
		in
		    if member(v,s) then
			concat3(intersection(l2,l),v,intersection(r2,r))
		    else
			concat(intersection(l2,l),intersection(r2,r))
		end

	    fun members set = fold(op::,[],set)

	    fun cardinality E = 0
	      | cardinality (T(_,n,_,_)) = n
	    
	    fun delete (E,x) = E
	      | delete (set as T(v,_,l,r),x) =
		if lt(x,v) then T'(v,delete(l,x),r)
		else if lt(v,x) then T'(v,l,delete(r,x))
		     else delete'(l,r)

	    fun fromList l = List.fold (fn(x,y)=>add(y,x)) l E

	    type  intset = Set

	end
    end

structure IntSet : INTSET =B;
