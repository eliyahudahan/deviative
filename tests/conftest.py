"""Shared pytest fixtures for Deviative tests."""
import pandas as pd
import pytest


@pytest.fixture
def moving_anomaly():
    return pd.DataFrame({
        'movement_state': ['moving'],
        'DCPA': [0.1], 'TCPA': [0.01], 'distance_km': [0.5],
    })


@pytest.fixture
def moving_not_anomaly():
    return pd.DataFrame({
        'movement_state': ['moving'],
        'DCPA': [0.5], 'TCPA': [0.01], 'distance_km': [0.5],
    })


@pytest.fixture
def anchored_pair():
    return pd.DataFrame({
        'movement_state': ['anchored'],
        'DCPA': [0.1], 'TCPA': [0.01], 'distance_km': [0.5],
    })
