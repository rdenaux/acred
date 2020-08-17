#
# Copyright (c) 2020 Expert System Iberia
#
"""Implements a sentence-level similarity reviewer based on a trained model
for semantic similarity.
"""
from acred import content
from acred.reviewer.similarity import label as simlabel
from acred.service import claimsim
from esiutils import isodate

content.register_acred_type('SentSimilarityReview', {
    'super_types': ['SimilarityReview', 'Review'],
    'ident_keys': ['@type', 'dateCreated', 'author', 'itemReviewed', 'reviewRating'], 
    'route_template': '/review/{identifier}',
    'itemref_keys': ['author', 'itemReviewed', 'reviewRating']
})


def bot_info(cfg):
    return claimsim.semSentSimReviewer(cfg)


def review(item, config):
    """Reviews the incoming item and returns a Review object

    :param item: a single item or a list of items, in this case the 
      items must be `ItemPair` instances, where both items are `Sentence` 
      instances.
    :param config: a configuration map
    :returns: one or more Review objects for the input items
    :rtype: dict or list of dict
    """
    # not implemented because this is inefficient,
    # you should probably use claimsim.find_related_sentences instead
    # also see aggqsent_credrev
    raise NotImplementedError()


def similarSent_as_SentSimilarityReview(simSent, simResult, cfg):
    qSent = simResult['q_claim']
    simReviewer = simResult['simReviewer']
    simVal = simSent['similarity']
    return {
        '@context': 'http://coinform.eu',
        '@type': 'SentSimilarityReview',
        'itemReviewed': content.as_dbq_sentpair(
            dbSent=simSent['sentence'], qSent=qSent, cfg=cfg),
        'headline': simlabel.claim_rel_str(simVal, None),
        'reviewRating': {
            '@type': 'Rating',
            'reviewAspect': 'similarity',
            'ratingValue': simVal
        },
        'dateCreated': simResult.get('dateCreated', isodate.now_utc_timestamp()),
        'author': simReviewer
    }
