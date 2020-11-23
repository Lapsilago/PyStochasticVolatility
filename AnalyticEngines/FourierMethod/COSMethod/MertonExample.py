import numpy as np
import matplotlib.pylab as plt
from AnalyticEngines.FourierMethod.CharesticFunctions import JumpDiffusionCharesticFunction, HestonCharesticFunction
from functools import partial
from AnalyticEngines.FourierMethod.COSMethod import COSRepresentation
from Instruments.EuropeanInstruments import TypeEuropeanOption
from py_vollib.black_scholes_merton.implied_volatility import implied_volatility
from py_vollib.black_scholes_merton import black_scholes_merton

import time

# European option price
no_strikes = 20
k_s = np.linspace(50.0, 200.0, no_strikes)
f0 = 100.0
x0 = np.log(f0)

# Merton parameters
sigma = 0.25
lambda_t = 0.2
jumpmean = 0.4
jumpstd = 0.15

# Upper and lower bound for cos integral
a = -2.0
b = 2.0

# maturities
T = [1.0]
markers = ['.', '+', '*', '^']
no_maturities = len(T)


for i in range(0, no_maturities):
    cf_merton = partial(JumpDiffusionCharesticFunction.get_meton_cf, t=T[i], x=x0, sigma=sigma, jumpmean=jumpmean,
                        jumpstd=jumpstd, lambda_t=lambda_t)

    # check martingale
    aux = cf_merton(np.asfortranarray(-1j))

    cos_price_merton = COSRepresentation.get_european_option_price(TypeEuropeanOption.CALL, a, b, 64, k_s, cf_merton)
    # aux = black_scholes_merton('c', 100.0, 50.0, 1.0, 0.0, 0.25, 0.0)

    iv_smile_merton = []
    for k in range(0, no_strikes):
        iv_smile_merton.append(implied_volatility(cos_price_merton[k], f0, f0, T[i], 0.0, 0.0, 'c'))

    plt.plot(k_s, iv_smile_merton, label='T=%s' % T[i], linestyle='--', color='black', marker=markers[i])

# plt.ylim([0.0, 1.0])
plt.xlabel('K')
plt.legend()
plt.show()
