#!/usr/bin/env python3
# encoding: UTF-8
import logging
import pandas as pd
import os
from utils import *


def check_A3_event(best_rsrp, connected_rsrp, A3Offset, Hys, best_gnb_id, connected_gnb_id):
    rsrp_a3 = connected_rsrp +(A3Offset + Hys)
    if best_rsrp >= rsrp_a3:
        return True
    return False


def check_A3_2_event(target_rsrp, connected_rsrp, A3Offset, Hys, best_gnb_id, connected_gnb_id):
    # RSRP_NEIGHBOR < RSRP_CONNECTED + A3Offset - Hys
    rsrp_a3 = connected_rsrp +(A3Offset - Hys)
    if target_rsrp < rsrp_a3:
        return True
    return False