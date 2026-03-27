#!/usr/bin/env python3

"""
Archivo con las constantes relativas a la cinética de reactores
y a distintos reactores nucleares
"""

class Constantes_Nucleares:
    """ Constantes comunes """

    ENERGIA_FISION = 3.2e-11  # [J] Total [2]
    FACTOR_DIVEN = 0.7960 # Para U235 [1]
    EFECTIVIDAD_FOTONEUTRONES = 0
    FACTOR_BENNETT = 1

    """
    [1] Norman E. Holden & Martin S. Zucker (1988) Prompt Neutron Emission
        Multiplicity Distribution and Average Values (Nubar) at 2200 m/s for
        the Fissile Nuclides, Nuclear Science and Engineering, 98:2, 174-181,
        DOI: 10.13182/NSE88-A28498

    [2] ENDF/B-VII.0 - Se usa la total, la de neutrinos es compensada con la
        energía depositada por gammas de captura.

    """

# Constantes propias para cada reactor
# Son una subclase de Constantes_Nucleares


class RA0(Constantes_Nucleares):
    LAMBDA_REDUCIDO = 0.016700  # [s]
    FACTOR_FORMA_L = 1.18
    BETA_EFECTIVO = 0.00792


class RA1(Constantes_Nucleares):
    LAMBDA_REDUCIDO = 0.011900  # [s]
    FACTOR_FORMA_L = 1.18
    BETA_EFECTIVO = 0.00751 # [3]
    SIGMA_BETA_EFECTIVO = 0.00003

    """
    [3] IN-EN-GRYCN-DAN-008 Rev.0 - "Cálculo de parámetros neutrónicos del
    reactor RA-1", S. Bazzana, C. Barberis (2019)

    """


class RA3(Constantes_Nucleares):
    LAMBDA_REDUCIDO = 0.008340  # [s]
    FACTOR_FORMA_L = 1.19
    BETA_EFECTIVO = 0.00769 # [4]
    EFECTIVIDAD_FOTONEUTRONES = 1.12e-4

    """
    [4] IN14EF02 Rev.0 - "Cálculo e la fracción efectiva de neutrones
    retardados en combustible de bajo enriquecimiento. Caso del reactor RA-3 de
    la CNEA", G. Estryk (2002)

    """


class RA4(Constantes_Nucleares):
    LAMBDA_REDUCIDO = 0.006531 # [s]
    FACTOR_FORMA_L = 1.18
    BETA_EFECTIVO = 0.00768


class RA6(Constantes_Nucleares):
    LAMBDA_REDUCIDO = 0.010000  # [s]
    FACTOR_FORMA_L = 1.19
    BETA_EFECTIVO = 0.007642 # [5]
    class N011(Constantes_Nucleares):
        LAMBDA_REDUCIDO = 0.00553  # [s] Medido
        FACTOR_FORMA_L = 1.19
        BETA_EFECTIVO = 0.007642  # PUMA
    class N016(Constantes_Nucleares):
        LAMBDA_REDUCIDO = 0.00565  # [s]
        FACTOR_FORMA_L = 1.19
        BETA_EFECTIVO = 0.00782

    """
    [5] ITA-47-005-07 "Evaluación de parámetros cinéticos", H. Blaumann, E.
    Lopasso.

    """


class RA8(Constantes_Nucleares):
    LAMBDA_REDUCIDO = 0.006184  # [s]
    FACTOR_FORMA_L = 1.18
    BETA_EFECTIVO = 0.0076


class CNAII(Constantes_Nucleares):
    LAMBDA_REDUCIDO = 0.069439  # [s]
    FACTOR_FORMA_L = 1.00
    BETA_EFECTIVO = 0.00758
    EFECTIVIDAD_FOTONEUTRONES = 0.62


class RP10(Constantes_Nucleares):
    class N007(Constantes_Nucleares):
        LAMBDA_REDUCIDO = 0.005685  # [s]
        FACTOR_FORMA_L = 1.2
        BETA_EFECTIVO = 0.00774
        EFECTIVIDAD_FOTONEUTRONES = 0.3
    class N008(Constantes_Nucleares):
        LAMBDA_REDUCIDO = 0.0070385  # [s]
        FACTOR_FORMA_L = 1.2
        BETA_EFECTIVO = 0.00754
        EFECTIVIDAD_FOTONEUTRONES = 0.3


if __name__ == '__main__':

    a = RA3
    print(RA3.BETA_EFECTIVO)
    print(RA3.N301.BETA_EFECTIVO)

    print([i for i in dir(RA3) if i.startswith("N")])
