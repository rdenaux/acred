#
# Copyright (c) 2020 Expert System Iberia
#
"""
Unit Tests for the dbsent_credrev
"""
import pytest
import json
import copy
from acred.reviewer.credibility import dbsent_credrev

def read_json(path):
    with open(path, encoding='utf-8') as f:
        return json.load(f)

relSent01 = read_json('test/SimilarSent/ss_01.json')
relSent02 = read_json('test/SimilarSent/ss_02.json')
relSent05 = read_json('test/SimilarSent/ss_05.json')

expected_auth = {
    '@context': 'http://coinform.eu',
    '@type': 'DBSentCredReviewer',
    'additionalType': ['SoftwareApplication', 'Bot'],
    'name': '',
    'launchConfiguration': {
        'acred_factchecker_urls': [],
        'factchecker_website_to_qclaim_confidence_penalty_factor': 0.5
    },
    'applicationSuite': 'Co-inform',
    'description': '',
    'url': '',
    'isBasedOn': [],
    'dateCreated': '',
    'author': {'@type': 'Organization',
               'name': 'Expert System Lab Madrid',
               'url': 'http://expertsystem.com'},
    'softwareVersion': '0.1.0',
    'identifier': ''}


def test_SimilarSent_as_DBSentCredRev_01():
    dbscr = dbsent_credrev.similarSent_as_DBSentCredRev(relSent01, {})
    expected = {
        '@context': 'http://coinform.eu',
        '@type': 'DBSentCredReview',
        'additionalType': ['CredibilityReview', 'Review'],
        'author': expected_auth,
        'itemReviewed': {},
        'text': "Sentence `Prada removed a display from their store in the Soho neighborhood of New York City after a complaint regarding monkey-like figurines spread widely online.` , in [this page](https://www.snopes.com/fact-check/prada-store-blackface-imagery/), seems *credible* based on [fact-check](https://www.snopes.com/fact-check/prada-store-blackface-imagery/) by [snopes](http://www.snopes.com) with textual claim-review rating 'true'",
        'isBasedOn': [],
        'reviewAspect': 'credibility',
        'dateCreated': '2020-03-30T19:38:00Z',
        'reviewRating': {
            '@type': 'AggregateRating',
            'ratingValue': 1.0,
            'confidence': 1.0,
            'ratingCount': 6,
            'ratingExplanation': "based on [fact-check](https://www.snopes.com/fact-check/prada-store-blackface-imagery/) by [snopes](http://www.snopes.com) with textual claim-review rating 'true'",
            'reviewAspect': 'credibility',
            'reviewCount': 5
        }
    }
    assert set(list(expected.keys())) == set(list(dbscr.keys()))
    assert expected['@type'] == dbscr['@type']
    assert expected['reviewAspect'] == dbscr['reviewAspect']
    
    eauth = expected['author']
    aauth = dbscr['author']
    assert set(list(eauth.keys())) == set(list(aauth.keys()))
    auth_isBasedOn = aauth['isBasedOn']
    assert len(auth_isBasedOn) == 2
    auth_basedOn_types = [bo.get('@type', None) for bo in auth_isBasedOn]
    assert set(auth_basedOn_types) == set(['MisinfoMeSourceCredReviewer', 'ClaimReviewNormalizer'])
    # assert expected['author'] == dbscr['author']

    erat = expected['reviewRating']
    arat = dbscr['reviewRating']
    assert erat == arat
    assert dbscr['text'] == expected['text']


def test_SimilarSent_as_DBSentCredRev_02():
    dbscr = dbsent_credrev.similarSent_as_DBSentCredRev(relSent02, {})
    expected = {
        '@context': 'http://coinform.eu',
        '@type': 'DBSentCredReview',
        'additionalType': ['CredibilityReview', 'Review'],
        'author': expected_auth,
        'itemReviewed': {},
        'text': 'Sentence `That is why Brussels has now entered full crisis - where it is prepared for a British free withdrawal, according to sources of  The Guardian.` , in [this page](https://www.aftonbladet.se/nyheter/a/50pox1/eu-kraver-473-miljarder--for-att-fortsatta-forhandlingarna), seems *not verifiable* as it was published on site `www.aftonbladet.se`. Site `www.aftonbladet.se` seems *credible* based on 1 review(s) by external rater(s) ([Web Of Trust](https://mywot.com/))',
        'isBasedOn': [],
        'reviewAspect': 'credibility',
        'dateCreated': '2020-03-30T19:38:00Z',
        'reviewRating': {
            '@type': 'AggregateRating',
            'ratingValue': 0.62,
            'confidence': 0.39,
            'ratingCount': 2,
            'ratingExplanation': 'as it was published on site `www.aftonbladet.se`. Site `www.aftonbladet.se` seems *credible* based on 1 review(s) by external rater(s) ([Web Of Trust](https://mywot.com/))',
            'reviewAspect': 'credibility',
            'reviewCount': 2
        }
    }
    assert set(list(expected.keys())) == set(list(dbscr.keys()))
    assert expected['@type'] == dbscr['@type']
    assert expected['reviewAspect'] == dbscr['reviewAspect']
    
    eauth = expected['author']
    aauth = dbscr['author']
    assert set(list(eauth.keys())) == set(list(aauth.keys()))
    auth_isBasedOn = aauth['isBasedOn']
    assert len(auth_isBasedOn) == 2
    auth_basedOn_types = [bo.get('@type', None) for bo in auth_isBasedOn if bo is not None]
    assert set(auth_basedOn_types) == set(['ClaimReviewNormalizer', 'MisinfoMeSourceCredReviewer'])
    # assert expected['author'] == dbscr['author']

    erat = expected['reviewRating']
    arat = dbscr['reviewRating']
    assert erat == arat
    assert dbscr['text'] == expected['text']


def test_SimilarSent_as_DBSentCredRev_05():
    dbscr = dbsent_credrev.similarSent_as_DBSentCredRev(relSent05, {})
    # with open('test/DBSentCredReview/dbscr05.json', 'w') as f:
    #     json.dump(dbscr, f, indent=2)
        
    expected = {
        '@context': 'http://coinform.eu',
        '@type': 'DBSentCredReview',
        'additionalType': ['CredibilityReview', 'Review'],
        'author': expected_auth,
        'itemReviewed': {},
        'isBasedOn': [],
        'text': 'Sentence `??` seems *credible* as it was published in site `http://www.factcheck.org` which seems *credible* based on 1 review(s) by external rater(s) ([NewsGuard](https://www.newsguardtech.com/))',
        'reviewAspect': 'credibility',
        'dateCreated': '2020-03-30T19:38:00Z',
        'reviewRating': {
            '@type': 'AggregateRating',
            'ratingValue': 1.0,
            'confidence': 1.0,
            'ratingCount': 2,
            'ratingExplanation': 'as it was published on site `www.factcheck.org`. Site `www.factcheck.org` seems *credible* based on 1 review(s) by external rater(s) ([NewsGuard](https://www.newsguardtech.com/))',
            'reviewAspect': 'credibility',
            'reviewCount': 2
        }
    }
    assert set(list(expected.keys())) == set(list(dbscr.keys()))
    assert expected['@type'] == dbscr['@type']
    assert expected['reviewAspect'] == dbscr['reviewAspect']
    
    eauth = expected['author']
    aauth = dbscr['author']
    assert set(list(eauth.keys())) == set(list(aauth.keys()))
    auth_isBasedOn = aauth['isBasedOn']
    assert len(auth_isBasedOn) == 2
    auth_basedOn_types = [bo.get('@type', None) for bo in auth_isBasedOn if bo is not None]
    assert set(auth_basedOn_types) == set(['ClaimReviewNormalizer', 'MisinfoMeSourceCredReviewer'])
    # assert expected['author'] == dbscr['author']

    erat = expected['reviewRating']
    arat = dbscr['reviewRating']
    assert erat == arat
    

def test_enhance_relsent_01():
    expected = {
        **copy.deepcopy(relSent01),
        'altName': 'TRUE',
        'claimReviewed': 'Prada removed a display from their store in the Soho neighborhood of New York City after a complaint regarding monkey-like figurines spread widely online.',
        'claimReview_credibility_rating': {
            '@type': 'Rating',
            'confidence': 1.0,
            'ratingValue': 1.0,
            'reviewAspect': 'credibility',
            'ratingExplanation': "based on [fact-check](https://www.snopes.com/fact-check/prada-store-blackface-imagery/) by [snopes](http://www.snopes.com) with textual claim-review rating 'true'"},
        'fact-checker': 'http://www.snopes.com',
        'similarity': 0.6789597091735332,
        'url': 'https://www.snopes.com/fact-check/prada-store-blackface-imagery/'}
    
    enhanced = dbsent_credrev.enhance_relsent(copy.deepcopy(relSent01), {})
    assert sorted(list(expected.keys())) == sorted(list(enhanced.keys()))
    assert expected == enhanced


def test_is_factchecker_01():
    cfg = {'acred_factchecker_urls': ['https://snopes.com/']}
    assert dbsent_credrev.is_factchecker('https://snopes.com/a/b', None, cfg)
    assert dbsent_credrev.is_factchecker('http://snopes.com/a/b', None, cfg)

def test_is_factchecker_01():
    cfg = {'acred_factchecker_urls': ['https://snopes.com/']}
    assert dbsent_credrev.is_factchecker(None, 'snopes.com', cfg)
