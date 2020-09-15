#
# Copyright (c) 2020 Expert System Iberia
#
"""
Unit Tests for the website_credrev
"""
from transformers import RobertaTokenizer
from stance import stancepred

def test_pad_encode_long_headline():
    headline = """Senate Committee Any Committee Agriculture, Nutrition, and Forestry (70th-116th) Armed Services (79th-116th) Banking, Housing, and
 Urban Affairs (70th-116th) Budget (93rd-116th) Commerce, Science, and Transportation (79th-116th) Energy and Natural Resources (70th-116th) Environment and Public Works (79th-116th) F
inance (70th-116th) Foreign Relations (70th-116th) Health, Education, Labor, and Pensions (70th-116th) Homeland Security and Governmental Affairs (70th-116th) Indian Affairs (95th-116t
h) Intelligence (Select) (94th-116th) Judiciary (70th-116th) Rules and Administration (79th-116th) Small Business and Entrepreneurship (81st-116th) Veterans' Affairs (91st-116th)"""
    body = "The American Health Care Act was scored twice by the CBO and it went through four committees before the House voted on it."
    tokenizer = RobertaTokenizer.from_pretrained('roberta-base')
    tokids, att_mask, tok_types = stancepred.pad_encode(headline, body, tokenizer, max_length=128)
    assert len(tokids) == 128

def test_pad_encode_02():
    headline = """In another highly successful operation several days ago, the Iraqi counterterrorist force conducted early-morning raids in Najaf that resulted in the capture of several senior lieutenants and 40 other members of that militia, and the seizure of enough weapons to fill nearly four 71/2-ton dump trucks."""
    body = """The sworn enemies Chuck Rhoades (Paul Giamatti) and Bobby Axelrod (Damian Lewis), whose power struggle has been the core of the series for three seasons, have buried the fighter bar and formed a sort of devil alliance to exploit each other's forces, targeting their aggression and their revenge. towards new objectives."""
    tokenizer = RobertaTokenizer.from_pretrained('roberta-base')
    tokids, att_mask, tok_types = stancepred.pad_encode(headline, body, tokenizer, max_length=128)
    assert len(tokids) == 128


