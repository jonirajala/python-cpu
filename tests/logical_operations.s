.global _start

.section .text
_start:
    /* Setup initial values */
    MOV R0, #0xF0        /* 11110000 */
    MOV R1, #0xCC        /* 11001100 */
    
    /* Logical operations */
    AND R2, R0, R1       /* R2 = 0xC0 */
    ORR R3, R0, R1       /* R3 = 0xFC */
    EOR R4, R0, R1       /* R4 = 0x3C */
    
    /* Test results */
    CMP R2, #0xC0
    CMP R3, #0xFC
    CMP R4, #0x3C
    BNE error             /* Branch to error if any comparison fails */

success:
    MOV R0, #1            /* Indicate success */
    B exit

error:
    MOV R0, #0            /* Indicate failure */
    B exit

exit:
    SWI 0                 /* Exit */
