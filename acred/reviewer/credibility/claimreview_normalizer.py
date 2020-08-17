#
# Copyright (c) 2020 Expert System Iberia
#
"""Normalizes `ClaimReview` so other reviewers can use a standard
value range. Produces a `NormalisedClaimReview`.
"""
from esiutils import isodate, bot_describer, dictu, hashu
from acred import content
from acred.rating import agg
from acred.reviewer.credibility import label as credlabel
import logging

version = '0.1.2'
dateCreated = '2020-06-05T13:23:00Z'
ci_context = 'http://coinform.eu'
logger = logging.getLogger(__name__)

content.register_acred_type('ClaimReviewNormalizer', {
    'super_types': ['SoftwareApplication', 'Bot'],
    'ident_keys': ['@type', 'name', 'dateCreated', 'softwareVersion',
         'isBasedOn', 'launchConfiguration'],
    'route_template': '/bot/{@type}/{softwareVersion}/{identifier}',
    'itemref_keys': ['isBasedOn']
})

content.register_acred_type('NormalisedClaimReview', {
    'super_types': ['ClaimReview', 'Review'],
    'ident_keys': ['@type', 'dateCreated', 'author', 'claimReviewed', 'reviewRating', 'reviewAspect',
                   'basedOnClaimReview'],
    'route_template': '/review/{identifier}',
    'itemref_keys': ['author', 'reviewRating', 'basedOnClaimReview']
})

content.register_acred_type('schema:ClaimReview', {
    'super_types': [],
    'ident_keys': ['url'],
    'route_template': None, # already should have an external url
    'itemref_keys': []
})

def normalise(claimReview, cfg):
    if claimReview is None:
        return None
    assert content.is_claimReview(claimReview), "%s" % (claimReview)
    sub_ratings = normalised_claimReview_ratings(claimReview)
    most_confident = agg.select_most_confident_rating(sub_ratings)
    if most_confident is None:
        agg_rating = {
            '@type': 'AggregateRating',
            'reviewAspect': 'credibility',
            'reviewCount': 1, # the original claimReview
            'ratingCount': len(sub_ratings),
            'ratingValue': 0.0,
            'confidence': 0.0,
            'ratingExplanation': 'Failed to interpret original [review](claimReview,get("url", "missing_url"))'
        }
    else:
        agg_rating = {
            **most_confident,
            '@type': 'AggregateRating',
            'reviewCount': 1,
            'ratingCount': len(sub_ratings)
        }
        assert type(agg_rating['confidence']) == float
        assert 'ratingExplanation' in agg_rating, '%s' % (most_confident)
    return {
        '@context': ci_context,
        '@type': 'NormalisedClaimReview',
        'additionalType': content.super_types('NormalisedClaimReview'),
        'author': bot_info(cfg),
        'text': 'Claim `%s` is *%s* %s' % (
            claimReview.get('claimReviewed'),
            credlabel.rating_label(agg_rating, cfg),
            agg_rating.get('ratingExplanation', '(missing explanation)')),
        'claimReviewed': claimReview.get('claimReviewed'),
        'dateCreated': isodate.now_utc_timestamp(),
        'isBasedOn': [claimReview] + sub_ratings,
        'reviewAspect': 'credibility',
        'reviewRating': agg_rating
    }


def bot_info(cfg):
    result = {
        '@context': ci_context,
        '@type': 'ClaimReviewNormalizer',
        'name': 'ESI ClaimReview Credibility Normalizer',
        'description': 'Analyses the alternateName and numerical rating value for a ClaimReview and tries to convert that into a normalised credibility rating',
        'additionalType': content.super_types('ClaimReviewNormalizer'),
        'author': bot_describer.esiLab_organization(),
        'dateCreated': dateCreated,
        'softwareVersion': version,
        'url': 'http://coinform.eu/bot/ClaimReviewNormalizer/%s' % version,
        'applicationSuite': 'Co-inform',
        'isBasedOn': [], # no dependencies
        'launchConfiguration': {} # no configs?
    }
    ident = hashu.hash_dict(dictu.select_keys(
        result,
        content.ident_keys(result)))
    return {
        **result,
        'identifier': ident
    }


def normalised_claimReview_accuracy(claimReview):
    creds = normalised_claimReview_ratings(claimReview)
    return agg.select_most_confident_rating(creds)


def normalised_claimReview_ratings(claimReview):
    rating = claimReview.get('reviewRating', {})
    fromVal, from_altName = None, None
    try:
        fromVal = normalised_ratingValue(rating, claimReview)
        from_altName = review_altName_as_accuracy(rating, claimReview)
    except Exception as e:
        logger.error(e, exc_info=True)
    creds = [from_altName, fromVal]
    return [c for c in creds if c is not None]

def normalised_ratingValue(rating, claimReview):
    """Returns a normalised credibility value for a claimReview rating dict

    :param rating: dict of a claimReview reviewRating. Should be of type https://schema.org/Rating
    :param claimReview: dict of the ClaimReview (used for generating explanations)
    :returns: a credibility dict with a value in range [-1, 1] and confidence in range [0, 1]
    :rtype: dict
    """
    ratingVal = rating.get('ratingValue', -1)
    if type(ratingVal) == str:
        ratingVal = float(ratingVal)
    if ratingVal != -1:
        worst = rating.get('worstRating', 1)
        best = rating.get('bestRating', 5)
        if type(worst) == str:
            worst = float(worst)
        if type(best) == str:
            best = float(best)
        assert isinstance(worst, (int, float)), type(worst)
        assert isinstance(best, (int, float)), type(best)
        assert worst < best
        assert worst <= ratingVal
        assert ratingVal <= best
        rnge = best - worst
        value = ratingVal - worst
        norm = value / rnge  # norm in range [0, 1]
        cred = (norm * 2.0) - 1.0  # cred in range [-1, 1]
        return {
            "@type": "Rating",
            'reviewAspect': 'credibility',
            "ratingValue": cred,
            "confidence": 0.85,  # hard-coded 
            "ratingExplanation":
            "Based on a [fact-check](%s) by [%s](%s) with normalised numeric ratingValue %s in range [%s-%s]" % (
                url(claimReview), author_name(claimReview), author_url(claimReview),
                ratingVal, worst, best),
            'description': 'Normalised accuracy from original rating value (and range)'

        }
    else:
        return {
            '@type': 'Rating',
            'reviewAspect': 'credibility',
            'ratingValue': 0.0,
            'confidence': 0.0,
            'ratingExplanation': 'Failed to normalise numeric rating in original [ClaimReview](%s) by [%s](%s)' % (
                url(claimReview), author_name(claimReview), author_url(claimReview))
        }

def url(claimReview, defValue='missingUrl'):
    return claimReview.get('url', defValue)

def author_name(claimReview, defValue="unknown author"):
    name = dictu.get_in(claimReview, ['author', 'name'])
    if name is None:
        url = dictu.get_in(claimReview, ['author', 'url'])
        name = content.domain_from_url(url)
        if name.startswith('www.'):
            name = name.replace('www.', '')
        if name.endswith('.com'):
            name = name.replace('.com', '')
    return name or defValue

def author_url(claimReview, defValue="unknownUrl"):
    return dictu.get_in(claimReview, ['author', 'url'], defValue)

def review_altName_as_accuracy(rating, claimReview):
    if type(rating) == str:
        altName = rating
    elif content.is_rating(rating):
        altName = rating.get('alternateName', None)
    elif type(rating) is dict and 'alternateName' in rating:
        altName = rating.get('alternateName', None)
    else:
        raise ValueError("Expecting str or Rating not %s %s" % (type(rating), rating))
    if altName is None:
        return {
            '@type': 'Rating',
            'reviewAspect': 'credibility',
            "ratingValue": 0.0,
            "confidence": 0.0,
            "ratingExplanation": "Based on [fact-check](%s) by [%s](%s) with no textual rating" % (
                url(claimReview), author_name(claimReview), author_url(claimReview))}
    
    assert type(altName) == str, '%s' % (type(altName))
    altName = altName.strip().lower()
    if altName.endswith('.'):
        altName = altName[:-1]
    value, confidence = None, None
    if altName in ['false', 'inaccurate',
                   'falso', 'faux', 'keliru',
                   'Фейк'.strip().lower(),  # fake in Russian
                   'not true', 'fake', 'fake news',
                   'incorrect', 'wrong',
                   'misleading/false',
                   'pants on fire', 'pants on fire!', 'four pinocchios',
                   'false and misleading', 'false , misleading',
                   'false, misleading', 'misleading , false',
                   'lie', 'yalan',  # turkish for lie
                   'forgery', 'still wrong', 'claim wrong',
                   'not legit (false)',
                   'not true (album)',
                   'science says not possible']:
        value = -1.0
        confidence = 1.0
    elif altName.startswith('wrong.'):
        value = -1.0
        confidence = 1.0
    elif altName.startswith('wrong,'):
        value = -1.0
        confidence = 1.0
    elif altName.startswith('wrong -'):
        value = -1.0
        confidence = 1.0
    elif altName.startswith('false -'):
        value = -1.0
        confidence = 1.0
    elif altName.startswith('no, '):
        value = -1.0
        confidence = 1.0
    elif altName.startswith('no! '):
        value = -1.0
        confidence = 1.0
    elif altName.startswith('certainly not! '):
        value = -1.0
        confidence = 1.0
    elif altName.endswith("rating: false"):
        value = -1.0
        confidence = 1.0
    elif altName in ['misleading', 'exaggerated', 'partial error', 'error',
                     'mostly false', 'three pinocchios', 'mainly false',
                     'this is misleading',
                     'sesat',  # indonesian?
                     'this is exaggerated', 'contradicts past remarks',
                     'most of it is not true', 'partially false',
                     'partly false',
                     'distorts the facts', 'distortion', 'short on truth',
                     'not the official statistic', 'conspiracy theory',
                     'misinformation / conspiracy theory',
                     'spins the facts', 'false headline',
                     'unlikely',
                     "science doesn't support claim"]:
        value = -0.5
        confidence = 1.0
    elif altName.startswith("misleading -"):
        value = -0.5
        confidence = 1.0
    elif altName.endswith("rating: false heading"):
        value = -0.5
        confidence = 1.0
    elif altName.endswith("debunked "):
        value = -0.5
        confidence = 1.0
    elif altName in ['half true', 'half-truths', 'two pinocchios',
                     'half truth',
                     'maybe', 'not exactly', 'unproven',
                     'unverified', 'the accuracy is mixed',
                     'mixed', 'mixture', 'other',
                     'this lacks evidence', 'not proven', 'needs more context',
                     'needs context', 'partial', 'partially correct',
                     'no evidence', 'not the whole story', 'partly true',
                     'we may never know', 'partially true , misleading',
                     'partially true', 'true but',
                     'misses the mark', 'insufficient evidence',
                     'this is unproven', 'unsupported', 'anecdote', 
                     'in dispute', 'analysis', 'lacks solid numbers']:
        value = 0.0
        confidence = 1.0
    elif altName.startswith('unsubstantiated.'):
        value = 0.0
        confidence = 1.0
    elif altName.endswith("rating: mixture"):
        value = 0.0
        confidence = 1.0
    elif altName in ['one pinocchio', 'mostly true', 'it could',
                     'mostly right',
                     'most legal experts agree', 'largely accurate',
                     "it's complicated", 'semi-correct', 'no sign of bias']:
        value = 0.5
        confidence = 1.0
    elif altName.startswith('true but '):
        value = 0.5
        confidence = 1.0
    elif altName.startswith('somewhat true '):
        value = 0.5
        confidence = 1.0
    elif altName in ['true', 'accurate', 'genuine', 'correct',
                     'benar']:  # indonesian for correct
        value = 1.0
        confidence = 1.0
    elif altName.startswith('accurate.'):
        value = 1.0
        confidence = 1.0
    elif altName in ['explanatory']:
        value = 0.0
        confidence = 0.75
    if value is not None:
        return {
            '@type': 'Rating',
            'reviewAspect': 'credibility',
            "ratingValue": value,
            "confidence": confidence,
            "ratingExplanation":
            "based on [fact-check](%s) by [%s](%s) with textual claim-review rating '%s'" % (
                url(claimReview), author_name(claimReview), author_url(claimReview),
                altName)
        }
    return {
        '@type': 'Rating',
        'reviewAspect': 'credibility',
        "ratingValue": 0.0,
        "confidence": 0.0,
        "ratingExplanation":
        "based on [fact-check](%s) by [%s](%s) with unknown accuracy for textual claim-review rating '%s'" % (
            url(claimReview), author_name(claimReview), author_url(claimReview),
            altName)
    }
