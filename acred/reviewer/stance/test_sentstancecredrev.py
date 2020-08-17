#
# Copyright (c) 2020 Expert System Iberia
#
"""Tests `sentstancecredrev`
"""
import json
import copy
from acred.reviewer.stance import sentstancecredrev as sscr
from acred import content
from esiutils import dictu


def read_json(path):
    with open(path, encoding='utf-8') as f:
        return json.load(f)

relSent01 = read_json('test/SimilarSent/ss_01.json')
relSent05 = read_json('test/SimilarSent/ss_05.json')

mockSimResult = {
    '@type': 'SemanticClaimSimilarityResult',
    'q_claim': 'This is the query claim.',
    'stanceReviewer': {
        '@type': 'SentStanceReviewer',
        'sotwareVersion': '0.1.0'
    }
}

def test_similarSent_as_SentStanceReview_01():
    review = sscr.similarSent_as_SentStanceReview(relSent01, mockSimResult, {})
    assert review is None


def test_similarSent_as_SentStanceReview_05():
    review = sscr.similarSent_as_SentStanceReview(relSent05, mockSimResult, {})
    assert review is not None
    expectedFields = ['@context', '@type', 'additionalType', 'reviewAspect',
                      'itemReviewed', 'reviewRating', 'dateCreated', 'author']
    
    isval, msg = dictu.is_value(review)
    assert isval, msg
    
    # with open('test/SentStanceReview/ssr05.json', 'w') as f:
    #     json.dump(review, f, indent=2)

    assert set(expectedFields) == set(list(review.keys()))
    assert 'stance' == review['reviewAspect']
    assert content.is_sentence_pair(review['itemReviewed'])
    assert dictu.get_in(review, ['author', '@type']) == 'SentStanceReviewer'
    

    

