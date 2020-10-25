import matplotlib.pylab as plt
import numpy as np

from MC_Engines.MC_SABR import SABR_Engine
from Tools import RNG, Types
from Instruments.EuropeanInstruments import EuropeanOption, TypeSellBuy, TypeEuropeanOption
from py_vollib.black_scholes_merton.implied_volatility import implied_volatility
from scipy.optimize import curve_fit
from AnalyticEngines.MalliavinMethod import ExpansionTools


dt = np.arange(0.025, 30, 1) * 1.0 / 365.0
no_dt_s = len(dt)

# simulation info
alpha = 0.3
nu = 0.6
rho = -0.6
parameters = [alpha, nu, rho]
no_time_steps = 50

seed = 123456789
no_paths = 500000
delta_time = 1.0 / 365.0

# random number generator
rnd_generator = RNG.RndGenerator(seed)

# option information
f0 = 100.0
options = []
options_shift = []
shift_spot = 0.0001
for d_i in dt:
    options.append(EuropeanOption(f0, 1.0, TypeSellBuy.BUY, TypeEuropeanOption.CALL, f0, d_i))
    options_shift.append(EuropeanOption(f0 * (1.0 + shift_spot), 1.0, TypeSellBuy.BUY, TypeEuropeanOption.CALL, f0, d_i))

# outputs
vol_swap_approximation = []
vol_swap_mc = []
implied_vol_atm = []

skew_atm_mc = []

for i in range(0, no_dt_s):
    rnd_generator.set_seed(seed)
    map_output = SABR_Engine.get_path_multi_step(0.0, dt[i], parameters, f0, no_paths, no_time_steps,
                                                 Types.TYPE_STANDARD_NORMAL_SAMPLING.ANTITHETIC, rnd_generator)

    mc_option_price = options[i].get_price(map_output[Types.SABR_OUTPUT.PATHS][:, -1])
    mc_option_price_shift = options_shift[i].get_price(map_output[Types.SABR_OUTPUT.PATHS][:, -1])
    implied_vol_base = implied_volatility(mc_option_price[0], f0, f0, dt[i], 0.0, 0.0, 'c')
    implied_vol_shift = implied_volatility(mc_option_price_shift[0], f0, f0, dt[i], 0.0, 0.0, 'c')
    vol_swap_mc.append(np.mean(np.sqrt(np.sum(map_output[Types.SABR_OUTPUT.INTEGRAL_VARIANCE_PATHS], 1) / dt[i])))
    skew_atm_mc.append((implied_vol_shift - implied_vol_base) / (shift_spot * f0))

asymptotic_limit = rho * nu

plt.plot(dt, skew_atm_mc, label='skew_mc')
plt.plot(dt, np.ones(len(dt)) * asymptotic_limit, label='limit asymptotic')

# curve fit


# def f_law(x, a, b):
#     return a + b * x
#
#
# popt, pcov = curve_fit(f_law, dt, output)
# y_fit_values = f_law(dt, *popt)
#
# plt.plot(dt, output, label='(I(t,f0) - E(v_t))', linestyle='--', color='black')
# plt.plot(dt, y_fit_values, label="%s + %s * t" % (round(popt[0], 5), round(popt[1], 5)), marker='.',
#          linestyle='--', color='black')
#
plt.xlabel('T')
plt.legend()
plt.show()