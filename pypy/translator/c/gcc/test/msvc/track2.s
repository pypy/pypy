; Function compile flags: /Odtpy
;	COMDAT _pypy_g__inplace_divrem1
_TEXT	SEGMENT
tv158 = -292						; size = 4
tv152 = -288						; size = 4
tv72 = -284						; size = 4
tv65 = -280						; size = 4
_l_v30733$ = -273					; size = 1
_l_v30737$ = -272					; size = 8
_l_v30740$ = -257					; size = 1
_l_v30744$ = -256					; size = 4
_l_v30753$ = -252					; size = 4
_l_v30748$ = -248					; size = 8
_l_v30709$ = -233					; size = 1
_l_v30710$ = -232					; size = 1
_l_v30714$ = -231					; size = 1
_l_v30718$ = -230					; size = 1
_l_v30729$ = -229					; size = 1
_l_v30725$ = -228					; size = 4
_l_v30705$ = -224					; size = 8
_l_evalue_70$ = -216					; size = 4
_l_index_219$ = -212					; size = 4
_l_v30738$ = -205					; size = 1
_l_v30730$ = -204					; size = 4
_l_v30734$ = -200					; size = 4
_l_length_82$ = -196					; size = 4
_l_v30745$ = -189					; size = 1
_l_v30752$ = -188					; size = 4
_l_v30749$ = -184					; size = 8
_l_l_100$ = -172					; size = 4
_l_l_101$ = -168					; size = 4
_l_length_83$ = -164					; size = 4
_l_v30704$ = -160					; size = 4
_l_v30722$ = -156					; size = 4
_l_v30715$ = -152					; size = 8
_l_v30726$ = -144					; size = 8
_l_v30711$ = -132					; size = 4
_l_x_97$ = -128						; size = 4
_l_v30739$ = -121					; size = 1
_l_v30731$ = -120					; size = 8
_l_v30735$ = -112					; size = 8
_l_v30742$ = -97					; size = 1
_l_v30751$ = -96					; size = 4
_l_v30707$ = -90					; size = 1
_l_v30723$ = -89					; size = 1
_l_v30712$ = -88					; size = 4
_l_v30716$ = -84					; size = 4
_l_v30703$ = -80					; size = 8
_l_v30727$ = -72					; size = 8
_l_v30732$ = -64					; size = 8
_l_v30736$ = -56					; size = 8
_l_index_218$ = -44					; size = 4
_l_v30750$ = -40					; size = 4
_l_v30754$ = -36					; size = 4
_l_v30717$ = -30					; size = 1
_l_v30720$ = -29					; size = 1
_l_v30713$ = -28					; size = 4
_l_v30702$ = -24					; size = 8
_l_v30706$ = -16					; size = 8
_l_v30728$ = -8						; size = 8
_l_self_3688$ = 8					; size = 4
_l_pin_1$ = 12						; size = 4
_l_n_38$ = 16						; size = 8
_l_size_53$ = 24					; size = 4
_pypy_g__inplace_divrem1 PROC				; COMDAT

; 16550: long pypy_g__inplace_divrem1(struct pypy_pypy_rlib_rbigint_rbigint0 *l_self_3688, struct pypy_pypy_rlib_rbigint_rbigint0 *l_pin_1, long long l_n_38, long l_size_53) {

	push	ebp
	mov	ebp, esp
	sub	esp, 292				; 00000124H
$block0$210880:

; 16551: 	struct pypy_object0 *l_evalue_70; long l_index_218; long l_index_219;
; 16552: 	struct pypy_array5 *l_l_100; struct pypy_array5 *l_l_101;
; 16553: 	long l_length_82; long l_length_83; bool_t l_v30707; bool_t l_v30709;
; 16554: 	bool_t l_v30710; bool_t l_v30714; bool_t l_v30717; bool_t l_v30718;
; 16555: 	bool_t l_v30720; bool_t l_v30723; bool_t l_v30729; bool_t l_v30733;
; 16556: 	bool_t l_v30738; bool_t l_v30739; bool_t l_v30740; bool_t l_v30742;
; 16557: 	bool_t l_v30745; long l_v30704; long l_v30712; long l_v30713;
; 16558: 	long l_v30716; long l_v30722; long l_v30725; long l_v30730;
; 16559: 	long l_v30734; long l_v30744; long l_v30750; long l_v30751;
; 16560: 	long l_v30752; long l_v30753; long l_v30754; long long l_v30702;
; 16561: 	long long l_v30703; long long l_v30705; long long l_v30706;
; 16562: 	long long l_v30715; long long l_v30726; long long l_v30727;
; 16563: 	long long l_v30728; long long l_v30731; long long l_v30732;
; 16564: 	long long l_v30735; long long l_v30736; long long l_v30737;
; 16565: 	long long l_v30748; long long l_v30749; struct pypy_array5 *l_v30711;
; 16566: 	long l_x_97;
; 16567: 
; 16568:     block0:
; 16569: 	OP_LLONG_GT(l_n_38, 0LL, l_v30707);

	cmp	DWORD PTR _l_n_38$[ebp+4], 0
	jl	SHORT $LN11@pypy_g__in
	jg	SHORT $LN19@pypy_g__in
	cmp	DWORD PTR _l_n_38$[ebp], 0
	jbe	SHORT $LN11@pypy_g__in
$LN19@pypy_g__in:
	mov	DWORD PTR tv65[ebp], 1
	jmp	SHORT $LN12@pypy_g__in
$LN11@pypy_g__in:
	mov	DWORD PTR tv65[ebp], 0
$LN12@pypy_g__in:
	mov	al, BYTE PTR tv65[ebp]
	mov	BYTE PTR _l_v30707$[ebp], al

; 16570: 	if (l_v30707) {

	movzx	ecx, BYTE PTR _l_v30707$[ebp]
	test	ecx, ecx
	je	SHORT $LN8@pypy_g__in

; 16571: 		goto block3;

	jmp	SHORT $block3$210882
$LN8@pypy_g__in:

; 16572: 	}
; 16573: 	l_evalue_70 = (&pypy_g_exceptions_AssertionError.ae_super.se_super.e_super);

	mov	DWORD PTR _l_evalue_70$[ebp], OFFSET _pypy_g_exceptions_AssertionError
$block1$210883:

; 16574: 	goto block1;
; 16575: 
; 16576:     block1:
; 16577: 	pypy_g_RPyRaiseException((&pypy_g_exceptions_AssertionError_vtable.ae_super.se_super.e_super), l_evalue_70);

	mov	edx, DWORD PTR _l_evalue_70$[ebp]
	push	edx
	push	OFFSET _pypy_g_exceptions_AssertionError_vtable
	call	_pypy_g_RPyRaiseException
    ;; expected {4(%ebp) | %ebx, %esi, %edi, (%ebp) | }
	add	esp, 8

; 16578: 	l_v30753 = -1L;

	mov	DWORD PTR _l_v30753$[ebp], -1
$block2$210884:

; 16579: 	goto block2;
; 16580: 
; 16581:     block2:
; 16582: 	RPY_DEBUG_RETURN();
; 16583: 	return l_v30753;

	mov	eax, DWORD PTR _l_v30753$[ebp]
	jmp	$LN9@pypy_g__in
$block3$210882:

; 16584: 
; 16585:     block3:
; 16586: 	OP_LLONG_LE(l_n_38, 2147483647LL, l_v30709);

	cmp	DWORD PTR _l_n_38$[ebp+4], 0
	jg	SHORT $LN13@pypy_g__in
	jl	SHORT $LN20@pypy_g__in
	cmp	DWORD PTR _l_n_38$[ebp], 2147483647	; 7fffffffH
	ja	SHORT $LN13@pypy_g__in
$LN20@pypy_g__in:
	mov	DWORD PTR tv72[ebp], 1
	jmp	SHORT $LN14@pypy_g__in
$LN13@pypy_g__in:
	mov	DWORD PTR tv72[ebp], 0
$LN14@pypy_g__in:
	mov	al, BYTE PTR tv72[ebp]
	mov	BYTE PTR _l_v30709$[ebp], al

; 16587: 	if (l_v30709) {

	movzx	ecx, BYTE PTR _l_v30709$[ebp]
	test	ecx, ecx
	je	SHORT $LN7@pypy_g__in

; 16588: 		goto block4;

	jmp	SHORT $block4$210886
$LN7@pypy_g__in:

; 16589: 	}
; 16590: 	l_evalue_70 = (&pypy_g_exceptions_AssertionError.ae_super.se_super.e_super);

	mov	DWORD PTR _l_evalue_70$[ebp], OFFSET _pypy_g_exceptions_AssertionError

; 16591: 	goto block1;

	jmp	SHORT $block1$210883
$block4$210886:

; 16592: 
; 16593:     block4:
; 16594: 	OP_INT_IS_TRUE(l_size_53, l_v30710);

	xor	edx, edx
	cmp	DWORD PTR _l_size_53$[ebp], 0
	setne	dl
	mov	BYTE PTR _l_v30710$[ebp], dl

; 16595: 	if (l_v30710) {

	movzx	eax, BYTE PTR _l_v30710$[ebp]
	test	eax, eax
	je	SHORT $block5$210889

; 16596: 		l_v30754 = l_size_53;

	mov	ecx, DWORD PTR _l_size_53$[ebp]
	mov	DWORD PTR _l_v30754$[ebp], ecx

; 16597: 		goto block6;

	jmp	SHORT $block6$210888
$block5$210889:

; 16598: 	}
; 16599: 	goto block5;
; 16600: 
; 16601:     block5:
; 16602: 	l_v30711 = RPyField(l_pin_1, prrr_inst_digits);

	mov	edx, DWORD PTR _l_pin_1$[ebp]
	mov	eax, DWORD PTR [edx+8]
	mov	DWORD PTR _l_v30711$[ebp], eax

; 16603: 	l_v30712 = l_v30711->length;

	mov	ecx, DWORD PTR _l_v30711$[ebp]
	mov	edx, DWORD PTR [ecx+4]
	mov	DWORD PTR _l_v30712$[ebp], edx

; 16604: 	l_v30754 = l_v30712;

	mov	eax, DWORD PTR _l_v30712$[ebp]
	mov	DWORD PTR _l_v30754$[ebp], eax
$block6$210888:

; 16605: 	goto block6;
; 16606: 
; 16607:     block6:
; 16608: 	OP_INT_SUB(l_v30754, 1L, l_v30713);

	mov	ecx, DWORD PTR _l_v30754$[ebp]
	sub	ecx, 1
	mov	DWORD PTR _l_v30713$[ebp], ecx

; 16609: 	l_v30702 = 0LL;

	mov	DWORD PTR _l_v30702$[ebp], 0
	mov	DWORD PTR _l_v30702$[ebp+4], 0

; 16610: 	l_x_97 = l_v30713;

	mov	edx, DWORD PTR _l_v30713$[ebp]
	mov	DWORD PTR _l_x_97$[ebp], edx
$block7$210890:

; 16611: 	goto block7;
; 16612: 
; 16613:     block7:
; 16614: 	OP_INT_GE(l_x_97, 0L, l_v30714);

	xor	eax, eax
	cmp	DWORD PTR _l_x_97$[ebp], 0
	setge	al
	mov	BYTE PTR _l_v30714$[ebp], al
$LN5@pypy_g__in:

; 16615: 	while (l_v30714) {

	movzx	ecx, BYTE PTR _l_v30714$[ebp]
	test	ecx, ecx
	je	SHORT $block8$210896

; 16616: 		goto block9;

	jmp	SHORT $block9$210894
$block7_back$210895:

; 16617: 		  block7_back: ;
; 16618: 		OP_INT_GE(l_x_97, 0L, l_v30714);

	xor	edx, edx
	cmp	DWORD PTR _l_x_97$[ebp], 0
	setge	dl
	mov	BYTE PTR _l_v30714$[ebp], dl

; 16619: 	}

	jmp	SHORT $LN5@pypy_g__in
$block8$210896:

; 16620: 	goto block8;
; 16621: 
; 16622:     block8:
; 16623: 	OP_LLONG_AND(l_v30702, 2147483647LL, l_v30715);

	mov	eax, DWORD PTR _l_v30702$[ebp]
	and	eax, 2147483647				; 7fffffffH
	mov	ecx, DWORD PTR _l_v30702$[ebp+4]
	and	ecx, 0
	mov	DWORD PTR _l_v30715$[ebp], eax
	mov	DWORD PTR _l_v30715$[ebp+4], ecx

; 16624: 	OP_TRUNCATE_LONGLONG_TO_INT(l_v30715, l_v30716);

	mov	edx, DWORD PTR _l_v30715$[ebp]
	mov	DWORD PTR _l_v30716$[ebp], edx

; 16625: 	l_v30753 = l_v30716;

	mov	eax, DWORD PTR _l_v30716$[ebp]
	mov	DWORD PTR _l_v30753$[ebp], eax

; 16626: 	goto block2;

	jmp	$block2$210884
$block9$210894:

; 16627: 
; 16628:     block9:
; 16629: 	OP_LLONG_LSHIFT(l_v30702, 31LL, l_v30703);

	mov	eax, DWORD PTR _l_v30702$[ebp]
	mov	edx, DWORD PTR _l_v30702$[ebp+4]
	mov	cl, 31					; 0000001fH
	call	__allshl
    ;; expected {4(%ebp) | %ebx, %esi, %edi, (%ebp) | }
	mov	DWORD PTR _l_v30703$[ebp], eax
	mov	DWORD PTR _l_v30703$[ebp+4], edx

; 16630: 	l_l_100 = RPyField(l_pin_1, prrr_inst_digits);

	mov	ecx, DWORD PTR _l_pin_1$[ebp]
	mov	edx, DWORD PTR [ecx+8]
	mov	DWORD PTR _l_l_100$[ebp], edx

; 16631: 	l_length_83 = l_l_100->length;

	mov	eax, DWORD PTR _l_l_100$[ebp]
	mov	ecx, DWORD PTR [eax+4]
	mov	DWORD PTR _l_length_83$[ebp], ecx

; 16632: 	OP_INT_LT(l_x_97, 0L, l_v30717);

	xor	edx, edx
	cmp	DWORD PTR _l_x_97$[ebp], 0
	setl	dl
	mov	BYTE PTR _l_v30717$[ebp], dl

; 16633: 	if (l_v30717) {

	movzx	eax, BYTE PTR _l_v30717$[ebp]
	test	eax, eax
	je	SHORT $LN3@pypy_g__in

; 16634: 		goto block14;

	jmp	$block14$210899
$LN3@pypy_g__in:

; 16635: 	}
; 16636: 	l_index_218 = l_x_97;

	mov	ecx, DWORD PTR _l_x_97$[ebp]
	mov	DWORD PTR _l_index_218$[ebp], ecx
$block10$210900:

; 16637: 	goto block10;
; 16638: 
; 16639:     block10:
; 16640: 	OP_INT_GE(l_index_218, 0L, l_v30718);

	xor	edx, edx
	cmp	DWORD PTR _l_index_218$[ebp], 0
	setge	dl
	mov	BYTE PTR _l_v30718$[ebp], dl

; 16641: 	RPyAssert(l_v30718, "negative list getitem index out of bound");
; 16642: 	OP_INT_LT(l_index_218, l_length_83, l_v30720);

	mov	eax, DWORD PTR _l_index_218$[ebp]
	xor	ecx, ecx
	cmp	eax, DWORD PTR _l_length_83$[ebp]
	setl	cl
	mov	BYTE PTR _l_v30720$[ebp], cl

; 16643: 	RPyAssert(l_v30720, "list getitem index out of bound");
; 16644: 	l_v30722 = l_l_100->length;

	mov	edx, DWORD PTR _l_l_100$[ebp]
	mov	eax, DWORD PTR [edx+4]
	mov	DWORD PTR _l_v30722$[ebp], eax

; 16645: 	OP_INT_LT(l_index_218, l_v30722, l_v30723);

	mov	ecx, DWORD PTR _l_index_218$[ebp]
	xor	edx, edx
	cmp	ecx, DWORD PTR _l_v30722$[ebp]
	setl	dl
	mov	BYTE PTR _l_v30723$[ebp], dl

; 16646: 	RPyAssert(l_v30723, "fixed getitem out of bounds");
; 16647: 	l_v30725 = RPyItem(l_l_100, l_index_218);

	mov	eax, DWORD PTR _l_index_218$[ebp]
	mov	ecx, DWORD PTR _l_l_100$[ebp]
	mov	edx, DWORD PTR [ecx+eax*4+8]
	mov	DWORD PTR _l_v30725$[ebp], edx

; 16648: 	OP_CAST_INT_TO_LONGLONG(l_v30725, l_v30726);

	mov	eax, DWORD PTR _l_v30725$[ebp]
	cdq
	mov	DWORD PTR _l_v30726$[ebp], eax
	mov	DWORD PTR _l_v30726$[ebp+4], edx

; 16649: 	OP_LLONG_ADD(l_v30703, l_v30726, l_v30706);

	mov	eax, DWORD PTR _l_v30703$[ebp]
	add	eax, DWORD PTR _l_v30726$[ebp]
	mov	ecx, DWORD PTR _l_v30703$[ebp+4]
	adc	ecx, DWORD PTR _l_v30726$[ebp+4]
	mov	DWORD PTR _l_v30706$[ebp], eax
	mov	DWORD PTR _l_v30706$[ebp+4], ecx

; 16650: 	OP_LLONG_FLOORDIV(l_v30706, l_n_38, l_v30727);

	mov	edx, DWORD PTR _l_n_38$[ebp+4]
	push	edx
	mov	eax, DWORD PTR _l_n_38$[ebp]
	push	eax
	mov	ecx, DWORD PTR _l_v30706$[ebp+4]
	push	ecx
	mov	edx, DWORD PTR _l_v30706$[ebp]
	push	edx
	call	__alldiv
    ;; expected {4(%ebp) | %ebx, %esi, %edi, (%ebp) | }
	mov	DWORD PTR _l_v30727$[ebp], eax
	mov	DWORD PTR _l_v30727$[ebp+4], edx

; 16651: 	OP_LLONG_XOR(l_v30706, l_n_38, l_v30728);

	mov	eax, DWORD PTR _l_v30706$[ebp]
	xor	eax, DWORD PTR _l_n_38$[ebp]
	mov	ecx, DWORD PTR _l_v30706$[ebp+4]
	xor	ecx, DWORD PTR _l_n_38$[ebp+4]
	mov	DWORD PTR _l_v30728$[ebp], eax
	mov	DWORD PTR _l_v30728$[ebp+4], ecx

; 16652: 	OP_LLONG_LE(l_v30728, 0LL, l_v30729);

	jg	SHORT $LN15@pypy_g__in
	jl	SHORT $LN21@pypy_g__in
	cmp	DWORD PTR _l_v30728$[ebp], 0
	ja	SHORT $LN15@pypy_g__in
$LN21@pypy_g__in:
	mov	DWORD PTR tv152[ebp], 1
	jmp	SHORT $LN16@pypy_g__in
$LN15@pypy_g__in:
	mov	DWORD PTR tv152[ebp], 0
$LN16@pypy_g__in:
	mov	dl, BYTE PTR tv152[ebp]
	mov	BYTE PTR _l_v30729$[ebp], dl

; 16653: 	OP_CAST_BOOL_TO_INT(l_v30729, l_v30730);

	movzx	eax, BYTE PTR _l_v30729$[ebp]
	mov	DWORD PTR _l_v30730$[ebp], eax

; 16654: 	OP_CAST_INT_TO_LONGLONG(l_v30730, l_v30731);

	mov	eax, DWORD PTR _l_v30730$[ebp]
	cdq
	mov	DWORD PTR _l_v30731$[ebp], eax
	mov	DWORD PTR _l_v30731$[ebp+4], edx

; 16655: 	OP_LLONG_MOD(l_v30706, l_n_38, l_v30732);

	mov	ecx, DWORD PTR _l_n_38$[ebp+4]
	push	ecx
	mov	edx, DWORD PTR _l_n_38$[ebp]
	push	edx
	mov	eax, DWORD PTR _l_v30706$[ebp+4]
	push	eax
	mov	ecx, DWORD PTR _l_v30706$[ebp]
	push	ecx
	call	__allrem
    ;; expected {4(%ebp) | %ebx, %esi, %edi, (%ebp) | }
	mov	DWORD PTR _l_v30732$[ebp], eax
	mov	DWORD PTR _l_v30732$[ebp+4], edx

; 16656: 	OP_LLONG_NE(l_v30732, 0LL, l_v30733);

	mov	edx, DWORD PTR _l_v30732$[ebp]
	or	edx, DWORD PTR _l_v30732$[ebp+4]
	je	SHORT $LN17@pypy_g__in
	mov	DWORD PTR tv158[ebp], 1
	jmp	SHORT $LN18@pypy_g__in
$LN17@pypy_g__in:
	mov	DWORD PTR tv158[ebp], 0
$LN18@pypy_g__in:
	mov	al, BYTE PTR tv158[ebp]
	mov	BYTE PTR _l_v30733$[ebp], al

; 16657: 	OP_CAST_BOOL_TO_INT(l_v30733, l_v30734);

	movzx	ecx, BYTE PTR _l_v30733$[ebp]
	mov	DWORD PTR _l_v30734$[ebp], ecx

; 16658: 	OP_CAST_INT_TO_LONGLONG(l_v30734, l_v30735);

	mov	eax, DWORD PTR _l_v30734$[ebp]
	cdq
	mov	DWORD PTR _l_v30735$[ebp], eax
	mov	DWORD PTR _l_v30735$[ebp+4], edx

; 16659: 	OP_LLONG_AND(l_v30731, l_v30735, l_v30736);

	mov	edx, DWORD PTR _l_v30731$[ebp]
	and	edx, DWORD PTR _l_v30735$[ebp]
	mov	eax, DWORD PTR _l_v30731$[ebp+4]
	and	eax, DWORD PTR _l_v30735$[ebp+4]
	mov	DWORD PTR _l_v30736$[ebp], edx
	mov	DWORD PTR _l_v30736$[ebp+4], eax

; 16660: 	OP_LLONG_SUB(l_v30727, l_v30736, l_v30705);

	mov	ecx, DWORD PTR _l_v30727$[ebp]
	sub	ecx, DWORD PTR _l_v30736$[ebp]
	mov	edx, DWORD PTR _l_v30727$[ebp+4]
	sbb	edx, DWORD PTR _l_v30736$[ebp+4]
	mov	DWORD PTR _l_v30705$[ebp], ecx
	mov	DWORD PTR _l_v30705$[ebp+4], edx

; 16661: 	OP_LLONG_AND(l_v30705, 2147483647LL, l_v30737);

	mov	eax, DWORD PTR _l_v30705$[ebp]
	and	eax, 2147483647				; 7fffffffH
	mov	ecx, DWORD PTR _l_v30705$[ebp+4]
	and	ecx, 0
	mov	DWORD PTR _l_v30737$[ebp], eax
	mov	DWORD PTR _l_v30737$[ebp+4], ecx

; 16662: 	OP_TRUNCATE_LONGLONG_TO_INT(l_v30737, l_v30704);

	mov	edx, DWORD PTR _l_v30737$[ebp]
	mov	DWORD PTR _l_v30704$[ebp], edx

; 16663: 	OP_INT_GE(l_v30704, 0L, l_v30738);

	xor	eax, eax
	cmp	DWORD PTR _l_v30704$[ebp], 0
	setge	al
	mov	BYTE PTR _l_v30738$[ebp], al

; 16664: 	if (l_v30738) {

	movzx	ecx, BYTE PTR _l_v30738$[ebp]
	test	ecx, ecx
	je	SHORT $LN2@pypy_g__in

; 16665: 		goto block11;

	jmp	SHORT $block11$210908
$LN2@pypy_g__in:

; 16666: 	}
; 16667: 	l_evalue_70 = (&pypy_g_exceptions_AssertionError.ae_super.se_super.e_super);

	mov	DWORD PTR _l_evalue_70$[ebp], OFFSET _pypy_g_exceptions_AssertionError

; 16668: 	goto block1;

	jmp	$block1$210883
$block11$210908:

; 16669: 
; 16670:     block11:
; 16671: 	l_l_101 = RPyField(l_self_3688, prrr_inst_digits);

	mov	edx, DWORD PTR _l_self_3688$[ebp]
	mov	eax, DWORD PTR [edx+8]
	mov	DWORD PTR _l_l_101$[ebp], eax

; 16672: 	l_length_82 = l_l_101->length;

	mov	ecx, DWORD PTR _l_l_101$[ebp]
	mov	edx, DWORD PTR [ecx+4]
	mov	DWORD PTR _l_length_82$[ebp], edx

; 16673: 	OP_INT_LT(l_x_97, 0L, l_v30739);

	xor	eax, eax
	cmp	DWORD PTR _l_x_97$[ebp], 0
	setl	al
	mov	BYTE PTR _l_v30739$[ebp], al

; 16674: 	if (l_v30739) {

	movzx	ecx, BYTE PTR _l_v30739$[ebp]
	test	ecx, ecx
	je	SHORT $LN1@pypy_g__in

; 16675: 		goto block13;

	jmp	$block13$210910
$LN1@pypy_g__in:

; 16676: 	}
; 16677: 	l_index_219 = l_x_97;

	mov	edx, DWORD PTR _l_x_97$[ebp]
	mov	DWORD PTR _l_index_219$[ebp], edx
$block12$210911:

; 16678: 	goto block12;
; 16679: 
; 16680:     block12:
; 16681: 	OP_INT_GE(l_index_219, 0L, l_v30740);

	xor	eax, eax
	cmp	DWORD PTR _l_index_219$[ebp], 0
	setge	al
	mov	BYTE PTR _l_v30740$[ebp], al

; 16682: 	RPyAssert(l_v30740, "negative list setitem index out of bound");
; 16683: 	OP_INT_LT(l_index_219, l_length_82, l_v30742);

	mov	ecx, DWORD PTR _l_index_219$[ebp]
	xor	edx, edx
	cmp	ecx, DWORD PTR _l_length_82$[ebp]
	setl	dl
	mov	BYTE PTR _l_v30742$[ebp], dl

; 16684: 	RPyAssert(l_v30742, "list setitem index out of bound");
; 16685: 	l_v30744 = l_l_101->length;

	mov	eax, DWORD PTR _l_l_101$[ebp]
	mov	ecx, DWORD PTR [eax+4]
	mov	DWORD PTR _l_v30744$[ebp], ecx

; 16686: 	OP_INT_LT(l_index_219, l_v30744, l_v30745);

	mov	edx, DWORD PTR _l_index_219$[ebp]
	xor	eax, eax
	cmp	edx, DWORD PTR _l_v30744$[ebp]
	setl	al
	mov	BYTE PTR _l_v30745$[ebp], al

; 16687: 	RPyAssert(l_v30745, "fixed setitem out of bounds");
; 16688: 	RPyItem(l_l_101, l_index_219) = l_v30704;

	mov	ecx, DWORD PTR _l_index_219$[ebp]
	mov	edx, DWORD PTR _l_l_101$[ebp]
	mov	eax, DWORD PTR _l_v30704$[ebp]
	mov	DWORD PTR [edx+ecx*4+8], eax

; 16689: 	OP_LLONG_MUL(l_v30705, l_n_38, l_v30748);

	mov	ecx, DWORD PTR _l_n_38$[ebp+4]
	push	ecx
	mov	edx, DWORD PTR _l_n_38$[ebp]
	push	edx
	mov	eax, DWORD PTR _l_v30705$[ebp+4]
	push	eax
	mov	ecx, DWORD PTR _l_v30705$[ebp]
	push	ecx
	call	__allmul
    ;; expected {4(%ebp) | %ebx, %esi, %edi, (%ebp) | }
	mov	DWORD PTR _l_v30748$[ebp], eax
	mov	DWORD PTR _l_v30748$[ebp+4], edx

; 16690: 	OP_LLONG_SUB(l_v30706, l_v30748, l_v30749);

	mov	edx, DWORD PTR _l_v30706$[ebp]
	sub	edx, DWORD PTR _l_v30748$[ebp]
	mov	eax, DWORD PTR _l_v30706$[ebp+4]
	sbb	eax, DWORD PTR _l_v30748$[ebp+4]
	mov	DWORD PTR _l_v30749$[ebp], edx
	mov	DWORD PTR _l_v30749$[ebp+4], eax

; 16691: 	OP_INT_SUB(l_x_97, 1L, l_v30750);

	mov	ecx, DWORD PTR _l_x_97$[ebp]
	sub	ecx, 1
	mov	DWORD PTR _l_v30750$[ebp], ecx

; 16692: 	l_v30702 = l_v30749;

	mov	edx, DWORD PTR _l_v30749$[ebp]
	mov	DWORD PTR _l_v30702$[ebp], edx
	mov	eax, DWORD PTR _l_v30749$[ebp+4]
	mov	DWORD PTR _l_v30702$[ebp+4], eax

; 16693: 	l_x_97 = l_v30750;

	mov	ecx, DWORD PTR _l_v30750$[ebp]
	mov	DWORD PTR _l_x_97$[ebp], ecx

; 16694: 	goto block7_back;

	jmp	$block7_back$210895
$block13$210910:

; 16695: 
; 16696:     block13:
; 16697: 	OP_INT_ADD(l_x_97, l_length_82, l_v30751);

	mov	edx, DWORD PTR _l_x_97$[ebp]
	add	edx, DWORD PTR _l_length_82$[ebp]
	mov	DWORD PTR _l_v30751$[ebp], edx

; 16698: 	l_index_219 = l_v30751;

	mov	eax, DWORD PTR _l_v30751$[ebp]
	mov	DWORD PTR _l_index_219$[ebp], eax

; 16699: 	goto block12;

	jmp	$block12$210911
$block14$210899:

; 16700: 
; 16701:     block14:
; 16702: 	OP_INT_ADD(l_x_97, l_length_83, l_v30752);

	mov	ecx, DWORD PTR _l_x_97$[ebp]
	add	ecx, DWORD PTR _l_length_83$[ebp]
	mov	DWORD PTR _l_v30752$[ebp], ecx

; 16703: 	l_index_218 = l_v30752;

	mov	edx, DWORD PTR _l_v30752$[ebp]
	mov	DWORD PTR _l_index_218$[ebp], edx

; 16704: 	goto block10;

	jmp	$block10$210900
$LN9@pypy_g__in:

; 16705: }

	mov	esp, ebp
	pop	ebp
	ret	0
_pypy_g__inplace_divrem1 ENDP
