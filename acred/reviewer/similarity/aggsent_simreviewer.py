#
# Copyright (c) 2020 Expert System Iberia
#
"""Implements a sentence-level aggregated similarity reviewer by aggregating a 
normal semantic similarity review and a stance detection between the two sentences
being reviewed.

"""
from esiutils import isodate, bot_describer, dictu, hashu
from acred.reviewer.similarity import label as simlabel
from acred.reviewer.similarity import semsent_simrev
from acred.reviewer.stance import sentstancecredrev as stancecredrev
from acred.rating import agg
from acred import content


version = '0.1.0'
ci_context = 'http://coinform.eu'


content.register_acred_type('SentPolarityReviewer', {
    'super_types': ['SoftwareApplication', 'Bot'],
    'ident_keys': ['@type', 'name', 'dateCreated', 'softwareVersion', 'isBasedOn', 'launchConfiguration'],
    'route_template': '/bot/{@type}/{softwareVersion}/{identifier}',
    'itemref_keys': ['isBasedOn']
})

content.register_acred_type('SentPolarSimilarityReview', {
    'super_types': ['SimilarityReview', 'Review'],
    'ident_keys': ['@type', 'headline', 'reviewBody', 'dateCreated',
                   'author', 'itemReviewed', 'reviewRating', 'isBasedOn'], 
    'route_template': '/review/{identifier}',
    'itemref_keys': ['author', 'itemReviewed', 'reviewRating', 'isBasedOn']
})

def review(item, config):
    """Reviews the incoming item and returns a Review object

    :param item: a single item or a list of items, in this case the 
      items must be `ItemPair` instances, where both items are `Sentence` 
      instances.
    :param config: a configuration map
    :returns: one or more Review objects for the input items
    :rtype: dict or list of dict
    """
    raise NotImplemented()

def default_sub_bots(cfg):
    return [semsent_simrev.bot_info(cfg), stancecredrev.bot_info(cfg)]

def bot_info(sub_bots, cfg):
    result = {
        '@context': ci_context,
        '@type': 'SentPolarityReviewer',
        'name': 'ESI Sentence Polarity Reviewer',
        'description': 'Estimates the polar similarity between two sentences',
        'additionalType': content.super_types('SentPolarityReviewer'),
        'softwareVersion': version,
        'dateCreated': '2020-03-27T22:54:00Z',
        'url': 'http://coinform.eu/bot/SentencePolarSimilarityReviewer/%s' % version,
        'applicationSuite': 'Co-inform',
        'author': bot_describer.esiLab_organization(),
        'isBasedOn': sub_bots,
        'launchConfiguration': {}
    }
    ident = hashu.hash_dict(dictu.select_keys(
        result, content.ident_keys(result)))
    return {
        **result,
        'identifier': ident
    }


def default_bot_info(cfg):
    return bot_info(default_sub_bots(cfg), cfg)


def similarSent_as_SentPolarSimilarityReview(simSent, simResult, cfg):
    """Converts a `SimilarSent` into a `SentPolarSimilarityReview` that combines
    a basic `SentSimilarityReview` with a `SentStanceReview` by delegating to
    `semsent_simrev`iewer and `sentstancecredrev`

    A `similarity` rating has values between 0 (dissimilar) and 1
    (similar), by contrast a `polarSimilarity` ranges between -1
    (semantically similar, but contradicting) and 1 (semantically
    similar and in agreement)

    :param simSent: 
    :param simResult: 
    :param cfg: 
    :returns: 
    :rtype:

    """
    simple_sentSimReview = semsent_simrev.similarSent_as_SentSimilarityReview(
        simSent, simResult, cfg)
    stanceReview = stancecredrev.similarSent_as_SentStanceReview(
        simSent, simResult, cfg)
    return aggregate_subReviews(simple_sentSimReview, stanceReview, cfg)


def aggregate_subReviews(simple_sentSimReview, stanceReview, cfg):
    """Aggregates a similarity and stance review into a polar similarity review

    :param simple_sentSimReview: a (non-polar) `SentSimilarityReview`
      for a `sentPair`
    :param stanceReview: a `SentStanceReview` for the same `sentPair`
      as `simple_sentSimReview`
    :param cfg: configuration options
    :returns: a `SentPolarSimilarityReview`
    :rtype: dict
    """
    assert simple_sentSimReview is not None
    if stanceReview is None:
        return simple_sentSimReview
    sim = dictu.get_in(simple_sentSimReview, ['reviewRating', 'ratingValue'])
    sent_stance = dictu.get_in(stanceReview,
                               ['reviewRating', 'ratingValue'], 'unrelated')
    stance_conf = dictu.get_in(stanceReview,
                               ['reviewRating', 'confidence'], '0.5')

    sent_pair = simple_sentSimReview['itemReviewed']
    assert stanceReview['itemReviewed'] == sent_pair, '%s != %s' % (
        stanceReview['itemReviewed'], sent_pair)
    
    agg_sim = calc_agg_polarsim(sim=sim, sent_stance=sent_stance,
        sent_stance_conf=stance_conf, cfg=cfg)
    sub_reviews = [sr for sr in [simple_sentSimReview, stanceReview]
                   if sr is not None]
    sub_ratings = [srev.get('reviewRating')
                   for srev in sub_reviews
                   if srev.get('reviewRating') is not None]
    headline = simlabel.claim_rel_str(sim, sent_stance)
    # TODO: more than an explanation this is the review body
    #  the explanation would be that one model said the sentences were x similar
    #  while another said they were (stance)
    explanation = 'Sentence `%s` %s `%s`' % (
            dictu.get_in(sent_pair, ['sentA', 'text']),
            headline,
            dictu.get_in(sent_pair, ['sentB', 'text']))
    sub_bots = [simple_sentSimReview.get('author', {}), stanceReview.get('author', {})]
    return {
        '@context': 'http://coinform.eu',
        '@type': 'SentPolarSimilarityReview',
        'additionalType': content.super_types('SentPolarSimilarityReview'),
        'itemReviewed': sent_pair,
        'headline': headline,
        'reviewAspect': 'polarSimilarity',
        'reviewBody': explanation,
        'reviewRating': {
            '@type': 'AggregateRating',
            'reviewAspect': 'polarSimilarity',
            'ratingValue': agg_sim,
            'confidence': stance_conf,
            'reviewCount': len(sub_reviews),
            'ratingCount': agg.total_ratingCount(sub_ratings),
            'ratingExplanation': explanation
        },
        'isBasedOn': sub_reviews,
        'dateCreated': isodate.now_utc_timestamp(),
        'author': bot_info(sub_bots, cfg)
    }


def calc_agg_polarsim(sim, sent_stance, sent_stance_conf, cfg):
    """Calculate the polar similarity value based on a (unipolar)
    similarity rating and a sentence stance rating.

    :param sim: float, a (unipolar) sentence similarity rating

    :param sent_stance: a stance rating label. Must be either `agree`,
      `disagree`, `unrelated` or `discuss`

    :param sent_stance_conf: confidence value for the `sent_stance` label

    :param cfg: configuration options
    :returns: an updated similarity rating value, taking into account 
    :rtype:

    """
    assert sim >= 0.0 and sim <= 1.0
    if sent_stance is None:
        sent_stance = 'unrelated'
    assert sent_stance in ['agree', 'disagree', 'unrelated', 'discuss'], sent_stance
    assert sent_stance_conf >= 0.0 and sent_stance_conf <= 1.0
    
    # if stance is agree -> inc sim confidence, positive polarity
    # if stance is disagree -> inc sim confidence, negative polarity
    # if stance is discuss -> keep sim?, positive polarity
    # if stance is unrelated -> dec sim confidence,  positive polarity
    if sent_stance in ['agree']:
        return sim if (sim > sent_stance_conf) else (sent_stance_conf + sim)/2.0
    elif sent_stance in ['disagree']:
        return -sim if (sim > sent_stance_conf) else -(sent_stance_conf + sim)/2.0
    elif sent_stance == 'unrelated':
        factor = float(cfg.get('sentence_similarity_unrelated_factor', 0.9))
        assert factor >= 0.0 and factor <= 1.0, factor
        return sim * factor  # not so similar after all
    else: # discuss
        factor = float(cfg.get('sentence_similarity_discuss_factor', 0.9))
        assert factor >= 0.0 and factor <= 1.0, factor
        return sim * factor
