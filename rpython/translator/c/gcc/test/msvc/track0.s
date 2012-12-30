; Function compile flags: /Ogtpy
;	COMDAT _pypy_g_ll_join_strs__Signed_arrayPtr
_TEXT	SEGMENT
_l_result_2$ = -8					; size = 4
_l_v405$ = -4						; size = 4
_l_num_items_0$ = 8					; size = 4
_l_items_2$ = 12					; size = 4
_pypy_g_ll_join_strs__Signed_arrayPtr PROC		; COMDAT

; 1457 : struct pypy_rpy_string0 *pypy_g_ll_join_strs__Signed_arrayPtr(long l_num_items_0, struct pypy_array0 *l_items_2) {

	sub	esp, 8
	push	ebx
	push	ebp
	push	esi

; 1458 : 	long l_i_22; long l_i_23; long l_res_index_0;
; 1459 : 	struct pypy_rpy_string0 *l_result_2; bool_t l_v403; bool_t l_v404;
; 1460 : 	bool_t l_v409; bool_t l_v410; bool_t l_v411; long l_v402;
; 1461 : 	long l_v414; long l_v417; long l_v418; long l_v421; long l_v422;
; 1462 : 	long l_v423; struct pypy_object_vtable0 *l_v408;
; 1463 : 	struct pypy_rpy_string0 *l_v412; struct pypy_rpy_string0 *l_v413;
; 1464 : 	struct pypy_rpy_string0 *l_v415; struct pypy_rpy_string0 *l_v419;
; 1465 : 	struct pypy_rpy_string0 *l_v420; struct pypy_rpy_string0 *l_v424;
; 1466 : 	void* l_v405; void* l_v406;
; 1467 : 
; 1468 :     block0:
; 1469 : 	l_i_23 = 0L;

	xor	esi, esi
	push	edi

; 1470 : 	l_v402 = 0L;

	xor	edi, edi

; 1471 : 	goto block1;
; 1472 : 
; 1473 :     block1:
; 1474 : 	OP_INT_LT(l_i_23, l_num_items_0, l_v403);

	cmp	DWORD PTR _l_num_items_0$[esp+20], esi
$block0$40039:
$block1$40040:

; 1475 : 	l_v404 = l_v403;
; 1476 : 	while (l_v404) {

	jle	SHORT $block2$40046
	mov	ebp, DWORD PTR _l_items_2$[esp+20]
	add	ebp, 8
$LL5@pypy_g_ll_@139:
$block6$40044:

; 1525 : 	goto block3_back;
; 1526 : 
; 1527 :     block6:
; 1528 : 	l_v419 = RPyItem(l_items_2, l_i_23);

	test	esi, esi
	jl	SHORT $LN14@pypy_g_ll_@139
	mov	eax, DWORD PTR _l_items_2$[esp+20]
	cmp	esi, DWORD PTR [eax+4]
	jl	SHORT $LN15@pypy_g_ll_@139
$LN14@pypy_g_ll_@139:
	call	_RPyAbort
$LN15@pypy_g_ll_@139:

; 1529 : 	l_v420 = l_v419;

	mov	ebx, DWORD PTR [ebp]

; 1530 : 	l_v421 = RPyField(l_v420, rs_chars).length;

	test	ebx, ebx
	jne	SHORT $LN16@pypy_g_ll_@139
	call	_RPyAbort
$LN16@pypy_g_ll_@139:

; 1531 : 	OP_INT_ADD(l_v402, l_v421, l_v422);
; 1532 : 	OP_INT_ADD(l_i_23, 1L, l_v423);
; 1533 : 	l_i_23 = l_v423;

	inc	esi
	add	ebp, 4

; 1534 : 	l_v402 = l_v422;

	add	edi, DWORD PTR [ebx+8]
	cmp	esi, DWORD PTR _l_num_items_0$[esp+20]
$block1_back$40045:
	jl	SHORT $LL5@pypy_g_ll_@139
$block2$40046:

; 1477 : 		goto block6;
; 1478 : 		  block1_back: ;
; 1479 : 		OP_INT_LT(l_i_23, l_num_items_0, l_v403);
; 1480 : 		l_v404 = l_v403;
; 1481 : 	}
; 1482 : 	goto block2;
; 1483 : 
; 1484 :     block2:
; 1485 : 	l_result_2 = pypy_g_mallocstr__Signed(l_v402);

	push	edi
	call	_pypy_g_mallocstr__Signed
    ;; expected {28(%esp) | 16(%esp), 8(%esp), 4(%esp), 12(%esp) | 36(%esp)}

; 1486 : 	l_v405 = (void*)l_items_2;

	mov	ecx, DWORD PTR _l_items_2$[esp+24]
	add	esp, 4
	mov	DWORD PTR _l_result_2$[esp+24], eax
	mov	DWORD PTR _l_v405$[esp+24], ecx

; 1487 : 	l_v406 = pypy_asm_gcroot(l_v405);

	mov	eax, DWORD PTR ?_constant_always_one_@?1??pypy_asm_gcroot@@9@9
	imul	eax, DWORD PTR _l_v405$[esp+24]

; 1488 : 	l_items_2 = l_v406; /* for moving GCs */
; 1489 : 	l_v408 = RPyField((&pypy_g_ExcData), ed_exc_type);
; 1490 : 	l_v409 = (l_v408 == NULL);

	cmp	DWORD PTR _pypy_g_ExcData, 0

; 1491 : 	if (!l_v409) {

	je	SHORT $LN3@pypy_g_ll_@139
	pop	edi
	pop	esi
	pop	ebp

; 1492 : 		l_v424 = ((struct pypy_rpy_string0 *) NULL);

	xor	eax, eax
	pop	ebx

; 1535 : 	goto block1_back;
; 1536 : }

	add	esp, 8
	ret	0
$LN3@pypy_g_ll_@139:

; 1493 : 		goto block4;
; 1494 : 	}
; 1495 : 	l_i_22 = 0L;

	xor	esi, esi

; 1496 : 	l_res_index_0 = 0L;

	xor	ebp, ebp

; 1497 : 	goto block3;
; 1498 : 
; 1499 :     block3:
; 1500 : 	OP_INT_LT(l_i_22, l_num_items_0, l_v410);

	cmp	DWORD PTR _l_num_items_0$[esp+20], ebp
$block3$40053:

; 1501 : 	l_v411 = l_v410;
; 1502 : 	while (l_v411) {

	jle	SHORT $LN1@pypy_g_ll_@139
	mov	ebx, ecx
	add	ebx, 8
$LL2@pypy_g_ll_@139:
$block5$40057:

; 1514 : 
; 1515 :     block5:
; 1516 : 	l_v412 = RPyItem(l_items_2, l_i_22);

	test	esi, esi
	jl	SHORT $LN9@pypy_g_ll_@139
	mov	edx, DWORD PTR _l_items_2$[esp+20]
	cmp	esi, DWORD PTR [edx+4]
	jl	SHORT $LN10@pypy_g_ll_@139
$LN9@pypy_g_ll_@139:
	call	_RPyAbort
$LN10@pypy_g_ll_@139:

; 1517 : 	l_v413 = l_v412;

	mov	edi, DWORD PTR [ebx]

; 1518 : 	l_v414 = RPyField(l_v413, rs_chars).length;

	test	edi, edi
	jne	SHORT $LN11@pypy_g_ll_@139
	call	_RPyAbort
$LN11@pypy_g_ll_@139:
	mov	edi, DWORD PTR [edi+8]

; 1519 : 	l_v415 = RPyItem(l_items_2, l_i_22);

	test	esi, esi
	jl	SHORT $LN12@pypy_g_ll_@139
	mov	eax, DWORD PTR _l_items_2$[esp+20]
	cmp	esi, DWORD PTR [eax+4]
	jl	SHORT $LN13@pypy_g_ll_@139
$LN12@pypy_g_ll_@139:
	call	_RPyAbort
$LN13@pypy_g_ll_@139:

; 1520 : 	pypy_g_copy_string_contents__rpy_stringPtr_rpy_stringPt(l_v415, l_result_2, 0L, l_res_index_0, l_v414);

	mov	ecx, DWORD PTR [ebx]
	mov	edx, DWORD PTR _l_result_2$[esp+24]
	push	edi
	add	ecx, 12					; 0000000cH
	push	ecx
	lea	eax, DWORD PTR [edx+ebp+12]
	push	eax
$block0$80664:
$block0$80634:
$block0$80639:
$block1$80640:
$block0$80644:
$block1$80645:
$block1$80635:
$block0$80659:
$block0$80667:
$block1$80668:
$block0$80673:
$block1$80674:
$block1$80661:
$block0$80678:
$block1$80679:
	call	_memcpy
    ;; expected {36(%esp) | 24(%esp), 16(%esp), 12(%esp), 20(%esp) | }
	add	esp, 12					; 0000000cH

; 1521 : 	OP_INT_ADD(l_res_index_0, l_v414, l_v417);
; 1522 : 	OP_INT_ADD(l_i_22, 1L, l_v418);
; 1523 : 	l_i_22 = l_v418;

	inc	esi
	add	ebx, 4

; 1524 : 	l_res_index_0 = l_v417;

	add	ebp, edi
	cmp	esi, DWORD PTR _l_num_items_0$[esp+20]
$block1$80671:
$block3_back$40058:
	jl	SHORT $LL2@pypy_g_ll_@139
$LN1@pypy_g_ll_@139:

; 1503 : 		goto block5;
; 1504 : 		  block3_back: ;
; 1505 : 		OP_INT_LT(l_i_22, l_num_items_0, l_v410);
; 1506 : 		l_v411 = l_v410;
; 1507 : 	}
; 1508 : 	l_v424 = l_result_2;
; 1509 : 	goto block4;
; 1510 : 
; 1511 :     block4:
; 1512 : 	RPY_DEBUG_RETURN();
; 1513 : 	return l_v424;

	mov	eax, DWORD PTR _l_result_2$[esp+24]
	pop	edi
	pop	esi
	pop	ebp
$block4$40052:
	pop	ebx

; 1535 : 	goto block1_back;
; 1536 : }

	add	esp, 8
	ret	0
_pypy_g_ll_join_strs__Signed_arrayPtr ENDP
