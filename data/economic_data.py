"""Compatibility layer for the original dashboard modules."""

from data.real_data import get_canada_policy_rate
from data.simulated_data import SIMULATED_INFLATION, SIMULATED_UNEMPLOYMENT


def get_canada_rate():
    return get_canada_policy_rate()


def get_inflation():
    return SIMULATED_INFLATION


def get_unemployment():
    return SIMULATED_UNEMPLOYMENT
