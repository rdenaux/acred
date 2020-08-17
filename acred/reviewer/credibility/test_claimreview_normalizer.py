#
# Copyright (c) 2019 Expert System Iberia
#
"""
Unit Tests for the predictor file
"""
import pytest
import json
from acred.reviewer.credibility import claimreview_normalizer as crn


def read_json(path):
    with open(path, encoding='utf-8') as f:
        return json.load(f)

cr_01 = read_json('test/ClaimReview/cr_01.json')
cr_02 = read_json('test/ClaimReview/cr_02.json')
cr_03 = read_json('test/ClaimReview/cr_03.json')


def test_review_altName_as_accuracy():
    altName = 'Фейк'
    result = crn.review_altName_as_accuracy(altName, cr_01)
    nAltName = altName.strip().lower()
    expected = {
        '@type': 'Rating',
        'reviewAspect': 'credibility',
        'ratingValue': -1.0,
        'confidence': 1.0,
        'ratingExplanation': "based on [fact-check](https://checkyourfact.com/2019/09/11/fact-check-viral-tim-allen-statement-attacking-democrats/) by [checkyourfact](http://checkyourfact.com) with textual claim-review rating '%s'" % nAltName
    }
    assert expected == result


def test_review_altName_as_accuracy_2():
    altName = 'Fact Crescendo Rating: False'
    result = crn.review_altName_as_accuracy(altName, cr_01)
    nAltName = altName.strip().lower()
    expected = {
        '@type': 'Rating',
        'reviewAspect': 'credibility',
        'ratingValue': -1.0,
        'confidence': 1.0,
        'ratingExplanation': "based on [fact-check](https://checkyourfact.com/2019/09/11/fact-check-viral-tim-allen-statement-attacking-democrats/) by [checkyourfact](http://checkyourfact.com) with textual claim-review rating '%s'" % nAltName
    }
    assert expected == result


def test_review_altName_as_accuracy_poynter():
    altNames = {
        "false":       {'ratingValue': -1.0, 'confidence': 1.0},
        "misleading":  {'ratingValue': -0.5, 'confidence': 1.0},
        "mostly false": {'ratingValue': -0.5, 'confidence': 1.0},
        "partially false": {'ratingValue': -0.5, 'confidence': 1.0},
        "pants on fire!": {'ratingValue': -1.0, 'confidence': 1.0},
        "no evidence":    {'ratingValue': 0.0, 'confidence': 1.0},
        "explanatory":    {'ratingValue': 0.0, 'confidence': 0.75},
        "partly false":   {'ratingValue': -0.5, 'confidence': 1.0},
        "mostly true":    {'ratingValue': 0.5, 'confidence': 1.0},
        "half true":      {'ratingValue': 0.0, 'confidence': 1.0},
        "(org. doesn't apply rating)": {'ratingValue': 0.0, 'confidence': 0.0},
        "mainly false":  {'ratingValue': -0.5, 'confidence': 1.0},
        "four pinocchios": {'ratingValue': -1.0, 'confidence': 1.0},
        "conspiracy theory": {'ratingValue': -0.5, 'confidence': 1.0},
        "fake": {'ratingValue': -1.0, 'confidence': 1.0},
        "partly true": {'ratingValue': 0.0, 'confidence': 1.0},
        "correct":     {'ratingValue': 1.0, 'confidence': 1.0},
        "incorrect":   {'ratingValue': -1.0, 'confidence': 1.0},
        "misleading/false": {'ratingValue': -1.0, 'confidence': 1.0},
        "three pinocchios": {'ratingValue': -0.5, 'confidence': 1.0},
        "two pinocchios":   {'ratingValue': 0.0, 'confidence': 1.0},
        "fake news":   {'ratingValue': -1.0, 'confidence': 1.0},
        "false and misleading": {'ratingValue': -1.0, 'confidence': 1.0},
        "half truth":  {'ratingValue': 0.0, 'confidence': 1.0},
        "in dispute":  {'ratingValue': 0.0, 'confidence': 1.0},
        "inaccurate":  {'ratingValue': -1.0, 'confidence': 1.0},
        "misinformation / conspiracy theory": {'ratingValue': -0.5, 'confidence': 1.0},
        "mixed":  {'ratingValue': 0.0, 'confidence': 1.0},
        "not legit (false)": {'ratingValue': -1.0, 'confidence': 1.0},
        "not true (album)": {'ratingValue': -1.0, 'confidence': 1.0},
        "pants on fire": {'ratingValue': -1.0, 'confidence': 1.0},
        "partially correct": {'ratingValue': 0.0, 'confidence': 1.0},
        "partially true": {'ratingValue': 0.0, 'confidence': 1.0},
        "true but": {'ratingValue': 0.0, 'confidence': 1.0},
        "unlikely": {'ratingValue': -0.5, 'confidence': 1.0},
        "unproven": {'ratingValue': 0.0, 'confidence': 1.0},
        "unverified": {'ratingValue': 0.0, 'confidence': 1.0}}
    for altName, expected in altNames.items():
        result = crn.review_altName_as_accuracy(altName, cr_02)
        nAltName = altName.strip().lower()
        base_msg = 'based on [fact-check](https://www.newtral.es/la-torre-eiffel-no-se-ilumino-con-la-bandera-de-colombia-por-el-triunfo-de-egan-bernal/20190801/) by [Newtral](https://www.newtral.es/)'
        msg = base_msg + " with textual claim-review rating '%s'" % nAltName
        if expected['confidence'] == 0:
            msg = base_msg + " with unknown accuracy for textual claim-review rating '%s'" % nAltName
        expected = {
            '@type': 'Rating',
            'reviewAspect': 'credibility',
            'ratingValue': expected['ratingValue'],
            'confidence': expected['confidence'],
            'ratingExplanation': msg
        }
        assert expected == result


def test_cr_normalise_01():
    result = crn.normalise(cr_01, {})
    assert cr_01 in result['isBasedOn']
    assert result['@type'] == 'NormalisedClaimReview'
    assert result['reviewAspect'] == 'credibility'
    assert result['reviewRating'] == {
        '@type': 'AggregateRating',
        'ratingValue': 0.0,
        'confidence': 1.0,
        #'ratingExplanation': "Failed to normalise numeric rating in original ClaimReview",
        'ratingExplanation': "based on [fact-check](https://checkyourfact.com/2019/09/11/fact-check-viral-tim-allen-statement-attacking-democrats/) by [checkyourfact](http://checkyourfact.com) with textual claim-review rating 'other'",
        'ratingCount': 2,
        'reviewAspect': 'credibility',
        'reviewCount': 1
    }


def test_cr_normalise_02():
    result = crn.normalise(cr_02, {})
    assert cr_02 in result['isBasedOn']
    assert result['@type'] == 'NormalisedClaimReview'
    assert result['reviewAspect'] == 'credibility'
    rating = result['reviewRating']
    assert rating == {
        '@type': 'AggregateRating',
        'ratingValue': -1.0,
        'confidence': 1.0,
        'ratingExplanation': "based on [fact-check](https://www.newtral.es/la-torre-eiffel-no-se-ilumino-con-la-bandera-de-colombia-por-el-triunfo-de-egan-bernal/20190801/) by [Newtral](https://www.newtral.es/) with textual claim-review rating 'falso'",
        'ratingCount': 2,
        'reviewAspect': 'credibility',
        'reviewCount': 1
    }
    author = result['author']
    assert author['@type'] == 'ClaimReviewNormalizer'
    assert author['@context'] == 'http://coinform.eu'
    assert author['applicationSuite'] == 'Co-inform'


def test_cr_normalise_03():
    result = crn.normalise(cr_03, {})
    assert cr_03 in result['isBasedOn']
    assert result['@type'] == 'NormalisedClaimReview'
    assert result['reviewAspect'] == 'credibility'
    rating = result['reviewRating']
    assert rating == {
        '@type': 'AggregateRating',
        'ratingValue': 0.0,
        'confidence': 1.0,
        'ratingExplanation': "based on [fact-check](http://www.politifact.com/truth-o-meter/statements/2018/jan/08/donald-trump/how-accurate-donald-trumps-about-black-hispa/) by [politifact](http://www.politifact.com) with textual claim-review rating 'mixture'",
        'ratingCount': 2,
        'reviewAspect': 'credibility',
        'reviewCount': 1
    }
    author = result['author']
    assert author['@type'] == 'ClaimReviewNormalizer'
    assert author['@context'] == 'http://coinform.eu'
    assert author['applicationSuite'] == 'Co-inform'
    

