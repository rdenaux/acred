#
# Copyright (c) 2020 Expert System Iberia
#
"""Tests `aggsent_simreviewer`
"""
import pytest
import json
import copy
from acred.reviewer.similarity import aggsent_simreviewer as psr #polarSimilarityReviewer
from acred import content
from esiutils import dictu

def read_json(path):
    with open(path, encoding='utf-8') as f:
        return json.load(f)

stanceReview05 = read_json('test/SentStanceReview/ssr05.json')
simReview05 = read_json('test/SentSimilarityReview/ssr05.json')


def test_aggregate_subReviews_05():
    review = psr.aggregate_subReviews(simReview05, stanceReview05, {})

    # with open('test/SentPolarSimilarityReview/spsr05.json', 'w') as f:
    #     json.dump(review, f, indent=2)

    expectedFields = ['@context', '@type', 'additionalType', 'itemReviewed', 'headline',
                      'reviewAspect', 'reviewBody', 'reviewRating', 'isBasedOn',
                      'dateCreated', 'author']
    assert set(expectedFields) == set(list(review.keys()))
    rating = review['reviewRating']
    assert content.is_rating(rating)
    exp_rating = {
        '@type': 'AggregateRating',
        'reviewAspect': 'polarSimilarity',
        'ratingValue': 0.7169436162195257,
        'confidence': 0.9742276072502136,
        'reviewCount': 2,
        'ratingCount': 2,
        'ratingExplanation': 'Sentence `This is the query claim.` is similar(?) but unrelated to `Said of the findings in a case against his charitable foundation: "All they found was incredibly effective philanthropy and some small technical violations, such as not keeping board minutes."`'
    }
    expRatingFs = list(exp_rating.keys())
    assert set(expRatingFs) == set(list(rating))
    assert rating == exp_rating
    
    


### calc_agg_polarsim
#stances = ['agree', 'disagree', 'discuss', 'unrelated']
# sim in range [0.0, 1.0]
# stance_conf in range [0.0, 1.0]
### 

def test_calc_agg_polarsim_agree():
    # if stance is agree -> inc sim confidence, positive polarity
    with pytest.raises(AssertionError) as excinfo:
        psr.calc_agg_polarsim(1.1, 'agree', 1.0, {})
    with pytest.raises(AssertionError) as excinfo:
        psr.calc_agg_polarsim(-0.1, 'agree', 1.0, {})
    with pytest.raises(AssertionError) as excinfo:
        psr.calc_agg_polarsim(1.0, 'agree', 2.0, {})
    with pytest.raises(AssertionError) as excinfo:
        psr.calc_agg_polarsim(1.0, 'agree', -0.2, {})

    assert 1.0 == psr.calc_agg_polarsim(1.0, 'agree', 1.0, {})
    assert 1.0 == psr.calc_agg_polarsim(1.0, 'agree', 0.8, {})
    assert 1.0 == psr.calc_agg_polarsim(1.0, 'agree', 0.6, {})
    assert 1.0 == psr.calc_agg_polarsim(1.0, 'agree', 0.4, {})

    assert 0.9 == psr.calc_agg_polarsim(0.8, 'agree', 1.0, {})
    assert 0.8 == psr.calc_agg_polarsim(0.6, 'agree', 1.0, {})
    assert 0.7 == psr.calc_agg_polarsim(0.4, 'agree', 1.0, {})
    assert 0.6 == psr.calc_agg_polarsim(0.2, 'agree', 1.0, {})

    assert 0.6 == psr.calc_agg_polarsim(0.6, 'agree', 0.6, {})


def test_calc_agg_polarsim_disagree():
    # if stance is disagree -> inc sim confidence, negative polarity
    assert -1.0 == psr.calc_agg_polarsim(1.0, 'disagree', 1.0, {})
    assert -1.0 == psr.calc_agg_polarsim(1.0, 'disagree', 0.8, {})
    assert -1.0 == psr.calc_agg_polarsim(1.0, 'disagree', 0.6, {})
    assert -1.0 == psr.calc_agg_polarsim(1.0, 'disagree', 0.4, {})

    assert -0.9 == psr.calc_agg_polarsim(0.8, 'disagree', 1.0, {})
    assert -0.8 == psr.calc_agg_polarsim(0.6, 'disagree', 1.0, {})
    assert -0.7 == psr.calc_agg_polarsim(0.4, 'disagree', 1.0, {})
    assert -0.6 == psr.calc_agg_polarsim(0.2, 'disagree', 1.0, {})

    assert -0.6 == psr.calc_agg_polarsim(0.6, 'disagree', 0.6, {})


def test_calc_agg_polarsim_discuss():
    # if stance is discuss -> keep sim?, positive polarity
    cfg = {'sentence_similarity_discuss_factor': 1.0}
    assert 1.0 == psr.calc_agg_polarsim(1.0, 'discuss', 1.0, cfg)
    assert 1.0 == psr.calc_agg_polarsim(1.0, 'discuss', 0.8, cfg)
    assert 1.0 == psr.calc_agg_polarsim(1.0, 'discuss', 0.6, cfg)
    assert 1.0 == psr.calc_agg_polarsim(1.0, 'discuss', 0.4, cfg)

    assert 0.8 == psr.calc_agg_polarsim(0.8, 'discuss', 1.0, cfg)
    assert 0.6 == psr.calc_agg_polarsim(0.6, 'discuss', 1.0, cfg)
    assert 0.4 == psr.calc_agg_polarsim(0.4, 'discuss', 1.0, cfg)
    assert 0.2 == psr.calc_agg_polarsim(0.2, 'discuss', 1.0, cfg)

    assert 0.6 == psr.calc_agg_polarsim(0.6, 'discuss', 0.6, cfg)

    cfg2 = {'sentence_similarity_discuss_factor': 0.9}
    assert 0.9 == psr.calc_agg_polarsim(1.0, 'discuss', 1.0, cfg2)
    assert 0.9 == psr.calc_agg_polarsim(1.0, 'discuss', 0.8, cfg2)
    assert 0.9 == psr.calc_agg_polarsim(1.0, 'discuss', 0.6, cfg2)
    assert 0.9 == psr.calc_agg_polarsim(1.0, 'discuss', 0.4, cfg2)

    assert pytest.approx(0.72) == psr.calc_agg_polarsim(0.8, 'discuss', 1.0, cfg2)
    assert pytest.approx(0.54) == psr.calc_agg_polarsim(0.6, 'discuss', 1.0, cfg2)
    assert pytest.approx(0.36) == psr.calc_agg_polarsim(0.4, 'discuss', 1.0, cfg2)
    assert pytest.approx(0.18) == psr.calc_agg_polarsim(0.2, 'discuss', 1.0, cfg2)

    assert pytest.approx(0.54) == psr.calc_agg_polarsim(0.6, 'discuss', 0.6, cfg2)


def test_calc_agg_polarsim_unrelated():
    # if stance is unrelated -> dec sim confidence,  positive polarity
    assert 0.9 == psr.calc_agg_polarsim(1.0, 'unrelated', 1.0, {})
    assert 0.9 == psr.calc_agg_polarsim(1.0, 'unrelated', 0.8, {})
    assert 0.9 == psr.calc_agg_polarsim(1.0, 'unrelated', 0.6, {})
    assert 0.9 == psr.calc_agg_polarsim(1.0, 'unrelated', 0.4, {})

    assert pytest.approx(0.72) == psr.calc_agg_polarsim(0.8, 'unrelated', 1.0, {})
    assert pytest.approx(0.54) == psr.calc_agg_polarsim(0.6, 'unrelated', 1.0, {})
    assert pytest.approx(0.36) == psr.calc_agg_polarsim(0.4, 'unrelated', 1.0, {})
    assert pytest.approx(0.18) == psr.calc_agg_polarsim(0.2, 'unrelated', 1.0, {})

    assert pytest.approx(0.54) == psr.calc_agg_polarsim(0.6, 'unrelated', 0.6, {})
    

