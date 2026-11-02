K_B_EV = 8.617333e-5
M_CR = 51.996
M_FE = 55.845
M_NI = 58.693
M_O = 15.999
M_CR2O3 = 2*M_CR + 3*M_O
M_FE2O3 = 2*M_FE + 3*M_O
M_FE3O4 = 3*M_FE + 4*M_O
M_NIO = M_NI + M_O
RHO_OXIDE = {"Cr2O3": 5.22, "Fe2O3": 5.24, "Fe3O4": 5.17, "NiO": 6.67}
S_STOICH = {
 "Cr2O3": M_CR2O3/(3*M_O),
 "Fe2O3": M_FE2O3/(3*M_O),
 "Fe3O4": M_FE3O4/(4*M_O),
 "NiO": M_NIO/(1*M_O),
}
