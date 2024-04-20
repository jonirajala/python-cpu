.global _start

.section .text
_start:
    /* Test ADD and SUB */
    MOV R0, #15           /* Load initial value into R0 */
    MOV R1, #10           /* Load initial value into R1 */
    ADD R2, R0, R1        /* R2 = R0 + R1, expect R2 = 25 */
    SUB R3, R0, R1        /* R3 = R0 - R1, expect R3 = 5 */
    
    /* Test MUL */
    MOV R4, #3
    MUL R5, R4, R1        /* R5 = R4 * R1, expect R5 = 30 */

    /* Test results */
    CMP R2, #25
    CMP R3, #5
    CMP R5, #30
    BNE error             /* Branch to error if any comparison fails */

success:
    MOV R0, #1            /* Indicate success */
    B exit

error:
    MOV R0, #0            /* Indicate failure */
    B exit

exit:
    SWI 0                 /* Exit */