import numpy as np
import matplotlib.pylab as plt

from MC_Engines.MC_RBergomi import RBergomi_Engine
from Tools import Types
from Tools import RNG
from Instruments.EuropeanInstruments import EuropeanOption, TypeSellBuy, TypeEuropeanOption
from MC_Engines.MC_RBergomi import LocalVolRBegomi
from py_vollib.black_scholes import implied_volatility

# simulation info
hurst = 0.499
nu = 0.4
rho = -0.4
v0 = 0.05
sigma_0 = np.sqrt(v0)

parameters = [nu, rho, hurst]

f0 = 100
T = np.arange(7, 180, 5) * 1.0 / 360

seed = 123456789

no_time_steps = 50
no_paths = 250000

atm_lv = []
atm_lv_skew = []
atm_iv_skew = []
atm_lv_skew_derive_estimator = []
var_swap = []
ratio = []
target_skew = []

rnd_generator = RNG.RndGenerator(seed)

for t_i in T:
    rnd_generator.set_seed(seed)
    # Julien Guyon paper https://papers.ssrn.com/sol3/papers.cfm?abstract_id=1885032&download=yes
    h = 1.5 * np.sqrt(t_i) * np.power(no_paths, - 0.2)
    delta = h / 10.0

    bump = 0.01
    f_left = (1.0 - bump) * f0
    f_right = (1.0 + bump) * f0

    # Options to compute the skew
    option_left = EuropeanOption(f_left, 1.0, TypeSellBuy.BUY, TypeEuropeanOption.CALL, f0, t_i)
    option = EuropeanOption(f0, 1.0, TypeSellBuy.BUY, TypeEuropeanOption.CALL, f0, t_i)
    option_right = EuropeanOption(f_right, 1.0, TypeSellBuy.BUY, TypeEuropeanOption.CALL, f0, t_i)

    # Rbergomi paths simulation
    map_bergomi_output = RBergomi_Engine.get_path_multi_step(0.0, t_i, parameters, f0, sigma_0, no_paths,
                                                             no_time_steps, Types.TYPE_STANDARD_NORMAL_SAMPLING.ANTITHETIC,
                                                             rnd_generator)

    # check simulation
    forward = np.mean(map_bergomi_output[Types.RBERGOMI_OUTPUT.PATHS][:, -1])
    vol_mean = np.mean(map_bergomi_output[Types.RBERGOMI_OUTPUT.SPOT_VOLATILITY_PATHS][:, -1])

    # option prices
    left_price = option_left.get_price_control_variate(map_bergomi_output[Types.RBERGOMI_OUTPUT.PATHS][:, -1],
                                                       map_bergomi_output[Types.RBERGOMI_OUTPUT.INTEGRAL_VARIANCE_PATHS])

    right_price = option_right.get_price_control_variate(map_bergomi_output[Types.RBERGOMI_OUTPUT.PATHS][:, -1],
                                                         map_bergomi_output[Types.RBERGOMI_OUTPUT.INTEGRAL_VARIANCE_PATHS])

    price = option.get_price_control_variate(map_bergomi_output[Types.RBERGOMI_OUTPUT.PATHS][:, -1],
                                             map_bergomi_output[Types.RBERGOMI_OUTPUT.INTEGRAL_VARIANCE_PATHS])

    iv_left = implied_volatility.implied_volatility(left_price[0], f0, f_left, t_i, 0.0, 'c')
    iv = implied_volatility.implied_volatility(price[0], f0, f0, t_i, 0.0, 'c')
    iv_right = implied_volatility.implied_volatility(right_price[0], f0, f_right, t_i, 0.0, 'c')

    skew_iv_i = f0 * (iv_right - iv) / (f_right - f0)

    atm_iv_skew.append(skew_iv_i)

    # new lv markovian projection

    lv_left = LocalVolRBegomi.get_local_vol_rough(t_i, f0, f_left,
                                                  map_bergomi_output[Types.RBERGOMI_OUTPUT.VARIANCE_SPOT_PATHS][:, -1],
                                                  np.sum(map_bergomi_output[Types.RBERGOMI_OUTPUT.INTEGRAL_VARIANCE_PATHS], 1))

    lv_i = LocalVolRBegomi.get_local_vol_rough(t_i, f0, f0,
                                               map_bergomi_output[Types.RBERGOMI_OUTPUT.VARIANCE_SPOT_PATHS][:, -1],
                                               np.sum(map_bergomi_output[Types.RBERGOMI_OUTPUT.INTEGRAL_VARIANCE_PATHS], 1))

    lv_right = LocalVolRBegomi.get_local_vol_rough(t_i, f0, f_right,
                                                   map_bergomi_output[Types.RBERGOMI_OUTPUT.VARIANCE_SPOT_PATHS][:, -1],
                                                   np.sum(map_bergomi_output[Types.RBERGOMI_OUTPUT.INTEGRAL_VARIANCE_PATHS],1))

    skew = f0 * (lv_right - lv_left) / (f_right - f_left)

    skew_sv_mc = f0 * LocalVolRBegomi.get_skew_local_rough(t_i, f0, f0,
                                                           map_bergomi_output[Types.RBERGOMI_OUTPUT.VARIANCE_SPOT_PATHS][:, -1],
                                                           np.sum(map_bergomi_output[Types.RBERGOMI_OUTPUT.INTEGRAL_VARIANCE_PATHS], 1))
    atm_lv_skew.append(skew)
    ratio.append(skew_iv_i / skew_sv_mc)
    target_skew.append(1.0/(hurst + 1.5))


def f_law(x, b, c):
    return b * np.power(x, c)


# popt_atm_lv_skew, pcov_diff_vols_swap = curve_fit(f_law, T, atm_lv_skew)
# popt_atm_lv_skew, pcov_diff_vols_swap = curve_fit(f_law, T, ratio)
# y_fit_atm_lv_skew = f_law(T, *popt_atm_lv_skew)
# skew_lv_rbergomi_fit = f_law(T, *popt_atm_lv_skew)

# plt.plot(T, ratio, label="skew_iv / skew_lv", color="blue", linestyle="dotted")
# # plt.plot(T, target_skew, label="1/(H + 3/2)", color="red", linestyle="dotted")

plt.plot(T, atm_lv_skew, label="skew_lv", color="blue", linestyle="dotted")
plt.plot(T, atm_iv_skew, label="skew_iv", color="green", linestyle="dashdot")

# plt.plot(T, skew_lv_rbergomi_fit, label=" %s * T^(%s)" % (round(popt_atm_lv_skew[0], 5),
#          round(popt_atm_lv_skew[1], 5)), color="green", linestyle="dotted")

# plt.plot(T, ratio, label="skew ratio ", color="green", linestyle="dotted")
# plt.plot(T, y_fit_atm_lv_skew, label=" %s * T^(%s)" % (round(popt_atm_lv_skew[0], 5),
#          round(popt_atm_lv_skew[1], 5)), color="green", linestyle="dotted")
# plt.plot(T, skew_ratio, label=" %s * T^(%s)" % (round(popt_atm_lv_skew[0], 5),
#          round(popt_atm_lv_skew[1], 5)), color="green", linestyle="dotted")


# plt.ylim((0.4, 0.6))
plt.xlabel("T")
plt.ylabel("Skew")


plt.legend()
plt.show()
