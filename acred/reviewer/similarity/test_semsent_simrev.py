#
# Copyright (c) 2020 Expert System Iberia
#
"""
Unit Tests for semsent_simrev.py
"""
import pytest
import json
import copy
from acred.reviewer.similarity import semsent_simrev


def read_json(path):
    with open(path, encoding='utf-8') as f:
        return json.load(f)

relSent01 = read_json('test/SimilarSent/ss_01.json')
relSent05 = read_json('test/SimilarSent/ss_05.json')


def test_similarSent_as_SentSimilarityReview_01():
    actual = semsent_simrev.similarSent_as_SentSimilarityReview(relSent01, {
        'q_claim': 'test q sent',
        'simReviewer': {},
        'dateCreated': '2020-03-21T18:03:00Z'
    }, {})
    assert set(list(actual.keys())) == set(['@context', '@type', 'itemReviewed', 'reviewRating', 'dateCreated', 'author', 'headline'])


def test_similarSent_as_SentSimilarityReview_05():
    actual = semsent_simrev.similarSent_as_SentSimilarityReview(relSent05, {
        'q_claim': 'This is the query claim.',
        'simReviewer': {},
        'dateCreated': '2020-03-21T18:03:00Z'
    }, {})
    # with open('test/SentSimilarityReview/ssr05.json', 'w') as f:
    #     json.dump(actual, f, indent=2)
    assert set(list(actual.keys())) == set(['@context', '@type', 'itemReviewed', 'reviewRating', 'dateCreated', 'author', 'headline'])
    
