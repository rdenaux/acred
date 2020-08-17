#
# Copyright (c) 2020 Expert System Iberia
#
"""Implements a sentence-level stance reviewer based on a trained model

TODO: rename, this is not a credibility reviewer, so it should be just
`sentstancerev``
"""
from acred import content
from acred.service import claimsim
from esiutils import isodate


ci_context = 'http://coinform.eu'

# FIXME: copied from stance/stancepred.py but we don't want to
#  import that from here since its meant to be hidden. Maybe we
#  could pass it as an additional field for the bot?
content.register_acred_type('SentStanceReviewer', {
    'super_types': ['SoftwareApplication', 'Bot'],
    'ident_keys': ['@type', 'name', 'dateCreated', 'softwareVersion',
                   'isBasedOn', 'launchConfiguration'],
    'route_template': '/bot/{@type}/{softwareVersion}/{identifier}',
    'itemref_keys': ['isBasedOn']
})

content.register_acred_type('SentStanceReview', {
    'super_types': ['StanceReview', 'Review'],
    'ident_keys': ['@type', 'dateCreated', 'author', 'itemReviewed', 'reviewRating'], 
    'route_template': '/review/{identifier}',
    'itemref_keys': ['author', 'itemReviewed', 'reviewRating']
})


def bot_info(config):
    return claimsim.stancePredictor(config)


def review(item, config):
    """Reviews the incoming item and returns 

    :param item: a single item or a list of items, in this case the 
      items must be `ItemPair` instances, where both items are `Sentence` 
      instances.
    :param config: a configuration map
    :returns: one or more Review objects for the input items
    :rtype: dict or list of dict
    """
    # not implemented because this is inefficient,
    # you should use claimsim.find_related_sentences
    # also see aggqsent_credrev
    raise NotImplemented()


def similarSent_as_SentStanceReview(simSent, simResult, cfg):
    if 'sent_stance' not in simSent:
        return None
    
    qSent = simResult['q_claim']
    dbSent = simSent['sentence']
    stanceReviewer = simResult['stanceReviewer']
    return {
        '@context': ci_context,
        '@type': 'SentStanceReview',
        'additionalType': content.super_types('SentStanceReview'),
        'reviewAspect': 'stance',
        'itemReviewed': content.as_dbq_sentpair(
            dbSent=dbSent, qSent=qSent, cfg=cfg),
        'reviewRating': {
            '@type': 'Rating',
            'reviewAspect': 'stance',
            'ratingValue': simSent['sent_stance'],
            'confidence': simSent['sent_stance_confidence'],
            'ratingExplanation': 'Sentence `dbSent` **%s** `qSent`.' % (
                simSent['sent_stance'])
        },
        'dateCreated': simResult.get('dateCreated', isodate.now_utc_timestamp()),
        'author': stanceReviewer
    }
