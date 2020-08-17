#
# Copyright (c) 2019 Expert System Iberia
#
"""
Unit Tests for predictor.py
"""
import pytest
from acred import predictor


##########
# testing ensure credibility is complex as it depends on:
#   0. similarity score
#   1. domain_credibility cred+conf
#   2. claimReview cred+conf
#   3. stance_pred label+conf
###########

test_cfg = {}



