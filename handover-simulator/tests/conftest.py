import os
import sys
import types

SRC_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "src")
if SRC_DIR not in sys.path:
    sys.path.insert(0, SRC_DIR)

# keras/tensorflow are not test dependencies of this repo but are imported at
# module scope by dqn.py / simulator_gti_dqn.py. Stub them out so those modules
# can be imported without the real (heavy) libraries installed.
if "tensorflow" not in sys.modules:
    tf_stub = types.ModuleType("tensorflow")
    tf_keras_losses = types.ModuleType("tensorflow.keras")
    tf_keras_losses.losses = types.ModuleType("tensorflow.keras.losses")
    tf_keras_losses.losses.Huber = lambda *a, **k: None
    tf_stub.keras = tf_keras_losses
    sys.modules["tensorflow"] = tf_stub
    sys.modules["tensorflow.keras"] = tf_keras_losses
    sys.modules["tensorflow.keras.losses"] = tf_keras_losses.losses

if "keras" not in sys.modules:
    keras_stub = types.ModuleType("keras")
    keras_models = types.ModuleType("keras.models")
    keras_models.Sequential = lambda *a, **k: None
    keras_layers = types.ModuleType("keras.layers")
    keras_layers.Dense = lambda *a, **k: None
    keras_optimizers = types.ModuleType("keras.optimizers")
    keras_optimizers.Adam = lambda *a, **k: None
    keras_stub.models = keras_models
    keras_stub.layers = keras_layers
    keras_stub.optimizers = keras_optimizers
    sys.modules["keras"] = keras_stub
    sys.modules["keras.models"] = keras_models
    sys.modules["keras.layers"] = keras_layers
    sys.modules["keras.optimizers"] = keras_optimizers

import pytest


@pytest.fixture
def scenario():
    return {
        "scenario_dimensions": {"min_x": 0.0, "max_x": 1000.0, "min_y": 0.0, "max_y": 1000.0},
        "bands": [
            {"Band_ID": 0, "Central_Frequency_Hz": 2.0e9, "User_Bandwidth_Hz": 5.0e6, "GNB_Bandwidth_Hz": 20.0e6},
            {"Band_ID": 1, "Central_Frequency_Hz": 3.5e9, "User_Bandwidth_Hz": 5.0e6, "GNB_Bandwidth_Hz": 20.0e6},
        ],
        "gnbs": [
            {"GNB_ID": 0, "Position_X": 0.0, "Position_Y": 0.0, "Position_Z": 10.0, "Band_ID": 0,
             "Transmission_Power_dBm": 30.0, "Type": "macro"},
            {"GNB_ID": 1, "Position_X": 500.0, "Position_Y": 500.0, "Position_Z": 10.0, "Band_ID": 1,
             "Transmission_Power_dBm": 30.0, "Type": "macro"},
        ],
    }
