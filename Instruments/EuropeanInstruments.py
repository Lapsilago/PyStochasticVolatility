import numpy as np
# import quadpy as qp

from scipy.integrate import quad
from functools import partial
from typing import Callable, List
from enum import Enum
from MCPricers.EuropeanPricers import call_operator, put_operator, malliavin_delta_call_put, malliavin_gamma_call_put
from Tools.Types import ndarray, ANALYTIC_MODEL, TypeGreeks
from AnalyticEngines.FourierMethod.HestonCharesticFunction import f_attari_heston, f_delta_attari_heston, \
    f_dual_delta_attari_heston, f_heston, f_gamma_heston, f_gamma_attari_heston


class TypeEuropeanOption(Enum):
    CALL = 1
    PUT = -1


class TypeSellBuy(Enum):
    SELL = -1
    BUY = 1


class EuropeanPayoff(object):
    def __init__(self,
                 f_price: Callable[[List[float]], List[float]]):
        self._f_price = f_price

    def get_value(self, x: List[float]):
        return self._f_price(x)


class EuropeanOption(object):
    def __init__(self,
                 strike: float,
                 notional: float,
                 buy_sell: TypeSellBuy,
                 option_type: TypeEuropeanOption,
                 spot: float,
                 delta_time: float):

        self._strike = strike
        self._notional = notional
        self._option_type = option_type
        self._buy_sell = buy_sell
        self._spot = spot
        self._delta_time = delta_time

        if buy_sell == TypeSellBuy.BUY:
            mult_buy_sell = 1.0
        else:
            mult_buy_sell = -1.0

        if option_type == TypeEuropeanOption.CALL:
            self._payoff = EuropeanPayoff(lambda x: mult_buy_sell * notional * call_operator(x, strike))
        else:
            self._payoff = EuropeanPayoff(lambda x: mult_buy_sell * notional * put_operator(x, strike))

    def get_price(self, x: ndarray) -> ndarray:
        if len(x.shape) == 1:
            return self._payoff.get_value(x)
        else:
            return self._payoff.get_value(x[:, -1])

    def get_malliavin_delta(self, x: ndarray, delta_weight: ndarray):
        if self._option_type == TypeEuropeanOption.CALL:
            return malliavin_delta_call_put(x[:, -1], self._strike, self._spot,  delta_weight, 1.0)
        else:
            return malliavin_delta_call_put(x[:, -1], self._strike, self._spot,  delta_weight, -1.0)

    def get_malliavin_gamma(self, x: ndarray, gamma_weight: ndarray):
        return malliavin_gamma_call_put(x[:, -1], self._strike, self._spot, gamma_weight)

    def get_analytic_value(self, *args, model_type=None, compute_greek=False):

        if model_type == ANALYTIC_MODEL.BLACK_SCHOLES_MODEL:
            pass

        elif model_type == ANALYTIC_MODEL.SABR_MODEL:
            alpha = args[0]
            rho = args[1]
            nu = args[2]
            pass

        elif model_type == ANALYTIC_MODEL.HESTON_MODEL_ATTARI:
            r = args[0]
            theta = args[1]
            rho = args[2]
            k = args[3]
            epsilon = args[4]
            v0 = args[5]
            risk_lambda = args[6]

            b2 = k + risk_lambda
            u2 = -0.5

            integrator = partial(f_attari_heston,
                                 t=self._delta_time,
                                 v=v0,
                                 spot=self._spot,
                                 r_t=r,
                                 theta=theta,
                                 rho=rho,
                                 k=k,
                                 epsilon=epsilon,
                                 b=b2,
                                 u=u2,
                                 strike=self._strike)

            integral_value = quad(integrator, 0.0, np.inf)
            df = np.exp(- r * self._delta_time)
            discrete_value = self._spot - 0.5 * self._strike * df
            stochastic_adjustment = (self._strike * df / np.pi) * integral_value[0]
            price = discrete_value - stochastic_adjustment

            if compute_greek:
                delta_integrator = partial(f_delta_attari_heston,
                                           t=self._delta_time,
                                           v=v0,
                                           spot=self._spot,
                                           r_t=r,
                                           theta=theta,
                                           rho=rho,
                                           k=k,
                                           epsilon=epsilon,
                                           b=b2,
                                           u=u2,
                                           strike=self._strike)

                dual_delta_integrator = partial(f_dual_delta_attari_heston,
                                                t=self._delta_time,
                                                v=v0,
                                                spot=self._spot,
                                                r_t=r,
                                                theta=theta,
                                                rho=rho,
                                                k=k,
                                                epsilon=epsilon,
                                                b=b2,
                                                u=u2,
                                                strike=self._strike)

                gamma_integrator = partial(f_gamma_attari_heston,
                                           t=self._delta_time,
                                           v=v0,
                                           spot=self._spot,
                                           r_t=r,
                                           theta=theta,
                                           rho=rho,
                                           k=k,
                                           epsilon=epsilon,
                                           b=b2,
                                           u=u2,
                                           strike=self._strike)

                delta_integral = quad(delta_integrator, 0.0, np.inf)
                dual_delta = quad(dual_delta_integrator, 0.0, np.inf)
                gamma_integral = quad(gamma_integrator, 0.0, np.inf)

                aux_dual_delta = (discrete_value - price) / self._strike

                greeks_map = {TypeGreeks.DELTA: 1.0 - (self._strike * df / np.pi) * delta_integral[0],
                              TypeGreeks.GAMMA: - (self._strike * df / np.pi) * gamma_integral[0],
                              TypeGreeks.DUAL_DELTA: - 0.5 * df - aux_dual_delta - (df * self._strike / np.pi) * dual_delta[0]}

                return price, greeks_map

            else:
                return price

        elif model_type == ANALYTIC_MODEL.HESTON_MODEL_REGULAR:
            r = args[0]
            theta = args[1]
            rho = args[2]
            k = args[3]
            epsilon = args[4]
            v0 = args[5]
            risk_lambda = args[6]

            u1 = 0.5
            b1 = k + risk_lambda - epsilon * rho
            b2 = k + risk_lambda
            u2 = -0.5

            if self._option_type == TypeEuropeanOption.CALL:
                phi = 1.0
            else:
                phi = -1.0

            integrator1 = partial(f_heston,
                                  t=self._delta_time,
                                  x=np.log(self._spot),
                                  v=v0,
                                  r_t=r,
                                  theta=theta,
                                  rho=rho,
                                  k=k,
                                  epsilon=epsilon,
                                  b=b1,
                                  u=u1,
                                  strike=self._strike)

            integrator2 = partial(f_heston,
                                  t=self._delta_time,
                                  x=np.log(self._spot),
                                  v=v0,
                                  r_t=r,
                                  theta=theta,
                                  rho=rho,
                                  k=k,
                                  epsilon=epsilon,
                                  b=b2,
                                  u=u2,
                                  strike=self._strike)

            int_val_1 = quad(integrator1, 0.0, np.inf)
            value_1_aux = 0.5 + (1.0/np.pi) * int_val_1[0]
            p1 = 0.5 * (1 - phi) + phi * value_1_aux

            int_val_2 = quad(integrator2, 0.0, np.inf)
            value_2_aux = 0.5 + (1.0/np.pi) * int_val_2[0]
            p2 = 0.5 * (1 - phi) + phi * value_2_aux
            df = np.exp(- r * self._delta_time)

            price = self._spot * p1 - df * self._strike * p2

            if compute_greek:
                gamma_integrator = partial(f_gamma_heston,
                                           t=self._delta_time,
                                           x=np.log(self._spot),
                                           v=v0,
                                           r_t=r,
                                           theta=theta,
                                           rho=rho,
                                           k=k,
                                           epsilon=epsilon,
                                           b=b2,
                                           u=u2,
                                           strike=self._strike)

                gamma_output = quad(gamma_integrator, 0.0, np.inf)
                gamma = gamma_output[0] / (np.pi * self._spot)
                greeks_map = {TypeGreeks.DELTA: phi * p1, TypeGreeks.GAMMA: gamma,
                              TypeGreeks.DUAL_DELTA: - phi * df * p2}

                return price, greeks_map

            else:
                return price

        else:
            raise Exception("The method " + str(model_type) + " is unknown.")





