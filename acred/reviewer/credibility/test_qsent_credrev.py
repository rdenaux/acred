#
# Copyright (c) 2020 Expert System Iberia
#
"""Tests the qsent_credrev
"""
import pytest
import json
from acred.reviewer.credibility import qsent_credrev

def read_json(path):
    with open(path, encoding='utf-8') as f:
        return json.load(f)

polarSimReview05 = read_json('test/SentPolarSimilarityReview/spsr05.json')
dbSentCredReview05 = read_json('test/DBSentCredReview/dbscr05.json')

def test_qsentcr_aggregate_subReviews_05():
    review = qsent_credrev.aggregate_subReviews(polarSimReview05, dbSentCredReview05, {})
    # with open('test/QSentCredReview/qscr05.json', 'w') as f:
    #      json.dump(review, f, indent=2)
        
    expectedFields = ['@context', '@type', 'reviewRating', 'additionalType',
                      'isBasedOn', 'itemReviewed', 'text', 'dateCreated',
                      'reviewAspect', 'author']
    assert set(expectedFields) == set(list(review.keys()))


def test_ensure_credibility_1():
    result = qsent_credrev.ensure_credibility({
        'similarity': 1.0,
        'sentence': 'sentA',
        'domain_credibility': {
            'credibility': {
                'value': 1.0,
                'confidence': 0.8
            },
            'itemReviewed': 'http://example.com/'},
        'claimReview_credibility_rating': {
            'value': 0.75,
            'confidence': 0.81}})
    assert 'similarity_credibility' in result
    simcred = result['similarity_credibility']
    assert simcred['value'] == 0.75
    assert simcred['confidence'] == pytest.approx(0.729) # 0.81
    assert 'Claim *is very similar to*:' in simcred['explanation']
    assert 'that was fact-checked' in simcred['explanation']
    assert 'and found to be accurate' in simcred['explanation']


def test_ensure_credibility_2():
    result = qsent_credrev.ensure_credibility({
        'similarity': 1.0,
        'sentence': 'sentA',
        'domain_credibility': {
            'credibility': {
                'value': 1.0,
                'confidence': 0.8
            },
            'itemReviewed': 'http://example.com/'},
        'sent_stance': 'disagree',
        'sent_stance_confidence': 0.9,
        'claimReview_credibility_rating': {
            'value': 0.75,
            'confidence': 0.81}})
    assert 'similarity_credibility' in result
    simcred = result['similarity_credibility']
    assert simcred['value'] == -0.75
    assert simcred['confidence'] == 0.81
    assert 'Claim *disagrees with*:' in simcred['explanation']
    assert 'that was fact-checked' in simcred['explanation']
    assert 'and found to be accurate' in simcred['explanation']


