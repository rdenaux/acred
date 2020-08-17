#
# Copyright (c) 2020 Expert System Iberia
#
"""
Unit Tests for the aggqsent_credrev
"""
from acred.reviewer.credibility import aggqsent_credrev
from acred import itnorm
import json

def load_json(path):
    with open(path, encoding='utf-8') as f:
        return json.load(f)

def test_claimsim_results_as_aggQSentCredReview_01():
    # 01. setup
    claimsim_result = load_json('test/SemanticClaimSimilarityResult/scsr_02.json')
    worth_rev = load_json('test/SentCheckWorthinessReview/scwr_01.json')  # ideally for the same sentence
    cfg = {
        'dev_mock_semSentSimReviewer': {'@type': 'MockSemSentSimReviewer',
                                        'identifier': '42'},
        'dev_mock_stancePredictor': {'@type': 'MockStancePredictor',
                                     'identifier': '43'},
        'dev_mock_semSentenceEncoder': {'@type': 'MockSemSentenceEncoder',
                                        'identifier': '44'}
    }  

    # 02. execute
    woutWorth = aggqsent_credrev.claimsim_result_as_aggQSentCredReview(claimsim_result, {}, cfg)
    withWorth = aggqsent_credrev.claimsim_result_as_aggQSentCredReview(claimsim_result, worth_rev, cfg)

    # test results: in this case we expect some fields to have different values, so verify
    assert len(woutWorth['isBasedOn']) == 2
    assert len(withWorth['isBasedOn']) == 2 + 1
    assert woutWorth['reviewRating']['ratingCount'] == 14
    assert withWorth['reviewRating']['ratingCount'] == 14 + 1
    assert woutWorth['reviewRating']['reviewCount'] == 14
    assert withWorth['reviewRating']['reviewCount'] == 14 + 1
    # reviewing the same sentence with or without checkworthiness results in a different review, reflected by having a different identifier
    assert itnorm.ensure_ident(withWorth, cfg)['identifier'] != itnorm.ensure_ident(woutWorth, cfg)['identifier']
    expectedExpl = "*agrees with*:\n\n * `Diarrhea, gut, blood and bone marrow cells are being destroyed, which can cause death after about two days.`\nthat seems *uncertain* as it was published on site `www.krone.at`. Site `www.krone.at` seems *uncertain* based on 1 review(s) by external rater(s) ([NewsGuard](https://www.newsguardtech.com/))"
    assert withWorth['reviewRating']['ratingExplanation'] == expectedExpl
    assert woutWorth['reviewRating']['ratingExplanation'] == expectedExpl
    assert withWorth['text'] == 'Sentence `Coronavirus kills people` seems *uncertain* as it ' + expectedExpl
    assert woutWorth['text'] == 'Sentence `Coronavirus kills people` seems *uncertain* as it ' + expectedExpl


def test_claimsim_results_as_aggQSentCredReview_02():
    # 01. setup
    claimsim_result = load_json('test/SemanticClaimSimilarityResult/scsr_02.json')
    cfg = {
        'dev_mock_semSentSimReviewer': {'@type': 'MockSemSentSimReviewer',
                                        'identifier': '42'},
        'dev_mock_stancePredictor': {'@type': 'MockStancePredictor',
                                     'identifier': '43'},
        'dev_mock_semSentenceEncoder': {'@type': 'MockSemSentenceEncoder',
                                        'identifier': '44'}
    }  
    worth_rev = load_json('test/SentCheckWorthinessReview/scwr_01.json')  # ideally for the same sentence
    claimsim_result['results'] = []

    # 02. execute
    woutWorth = aggqsent_credrev.claimsim_result_as_aggQSentCredReview(claimsim_result, {}, cfg)
    withWorth = aggqsent_credrev.claimsim_result_as_aggQSentCredReview(claimsim_result, worth_rev, cfg)

    # test results: in this case we expect some fields to have different values, so verify
    assert len(woutWorth['isBasedOn']) == 0
    assert len(withWorth['isBasedOn']) == 0 + 1
    assert itnorm.ensure_ident(withWorth, cfg)['identifier'] != itnorm.ensure_ident(woutWorth, cfg)['identifier']
    expectedExpl = "has no (close) matches in the Co-inform database, so we cannot assess its credibility."
    assert withWorth['reviewRating']['ratingExplanation'] == expectedExpl
    assert woutWorth['reviewRating']['ratingExplanation'] == expectedExpl
    assert withWorth['text'] == 'Sentence `Coronavirus kills people` seems *not verifiable* as it ' + expectedExpl
    assert woutWorth['text'] == 'Sentence `Coronavirus kills people` seems *not verifiable* as it ' + expectedExpl

    
