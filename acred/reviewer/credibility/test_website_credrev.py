#
# Copyright (c) 2020 Expert System Iberia
#
"""
Unit Tests for the website_credrev
"""
import pytest
import json
import copy
from acred.reviewer.credibility import website_credrev


def read_json(path):
    with open(path, encoding='utf-8') as f:
        return json.load(f)

simSent01 = read_json('test/SimilarSent/ss_01.json')
domcred01 = simSent01['domain_credibility']


def test_from_old_DomainCredibility():
    wscr = website_credrev.from_old_DomainCredibility(domcred01, {})
    expected_fields = ['@context', '@type', 'itemReviewed', 'text', 'additionalType', 'author', 'reviewRating',
                       'dateCreated', 'reviewAspect', 'isBasedOn', 'isBasedOn_assessments',
                       'timings']
    assert sorted(expected_fields) == sorted(list(wscr.keys()))
    assert wscr['@type'] == 'WebSiteCredReview'
    assert wscr['reviewAspect'] == 'credibility'
    assert len(wscr['isBasedOn_assessments']) == 2
    
    rating = wscr['reviewRating']
    expRating = {
        '@type': 'AggregateRating',
        'reviewAspect': 'credibility',
        'ratingValue': 0.9676923076923077,
        'confidence': 0.8666666666666667,
        'ratingExplanation': 'based on 2 review(s) by external rater(s) %s' % (
            '([NewsGuard](https://www.newsguardtech.com/) or [Web Of Trust](https://mywot.com/))'),
        'reviewCount': 2,
        'ratingCount': 2,
    }
    expText = 'Site `www.snopes.com` seems *credible* based on 2 review(s) by external rater(s) %s' % (
        '([NewsGuard](https://www.newsguardtech.com/) or [Web Of Trust](https://mywot.com/))')
    assert rating == expRating
    assert wscr['text'] == expText

