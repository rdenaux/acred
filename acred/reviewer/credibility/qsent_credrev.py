#
# Copyright (c) 2020 Expert System Iberia
#
"""Credibility reviewer for a "query" sentence. I.e. a sentence that
may not be in the co-inform database yet. Produces a `QSentCredReview`

This assessment is done based on a reference credibility review for a
sentence in the co-inform DB, along with a similarity review between
the query sentence and the reference sentence.
"""
from acred.reviewer.credibility import dbsent_credrev
from acred.reviewer.similarity import label as simlabel
from acred.reviewer.similarity import aggsent_simreviewer
from acred.reviewer.credibility import label as credlabel
from acred.rating import agg
from acred import content
from esiutils import isodate, bot_describer, citimings, dictu, hashu

ci_context = 'http://coinform.eu'
version = '0.1.0'


content.register_acred_type('QSentCredReviewer', {
    'super_types': ['SoftwareApplication', 'Bot'],
    'ident_keys': ['@type', 'name', 'dateCreated', 'softwareVersion', 'isBasedOn', 'launchConfiguration'],
    'route_template': '/bot/{@type}/{softwareVersion}/{identifier}',
    'itemref_keys': ['isBasedOn']
})


content.register_acred_type('QSentCredReview', {
    'super_types': ['CredibilityReview', 'Review'],
    'ident_keys': ['@type', 'dateCreated', 'author', 'itemReviewed', 'reviewRating', 'isBasedOn'],
    'route_template': '/review/{identifier}',
    'itemref_keys': ['author', 'itemReviewed', 'reviewRating', 'isBasedOn']
})

def review(item, based_on, config):
    """Reviews the incoming item and returns a Review for it

    :param item: a single item or a list of items, in this case the 
      items must be `Sentence` instances.
    :param based_on: list of zero or more relevant reviews that may 
      be required by this reviewer to perform the review of the `item`.
      For qsent_credrev, this must contain both a SentenceSimilarityReview
      and a DBSentCredReview.
    :param config: a configuration map
    :returns: one or more Review objects for the input items
    :rtype: dict or list of dict
    """
    raise NotImplemented()

def default_sub_bots(cfg):
    return [dbsent_credrev.default_bot_info(cfg),
            aggsent_simreviewer.default_bot_info(cfg)]

def bot_info(sub_bots, cfg):
    result = {
        '@context': ci_context,
        '@type': 'QSentCredReviewer',
        'name': 'ESI Query Sentence Credibility Reviewer',
        'description': 'Estimates the credibility of a sentence based on its polar similarity with a sentence in the Co-inform database for which a credibility can be estimated',
        'additionalType': content.super_types('QSentCredReviewer'),
        'author': bot_describer.esiLab_organization(),
        'softwareVersion': version,
        'dateCreated': '2020-03-27T22:54:00Z',
        'url': 'http://coinform.eu/bot/QSentenceCredReviewer/%s' % version,
        'applicationSuite': 'Co-inform',
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

    
def similarSent_as_QSentCredReview(simSent, claimSimResult, cfg):
    """Converts a `SimilarSent` into a `QSentCredReview`

    This review is done based on a reference credibility review
    for a sentence in the co-inform DB, along with a similarity review
    between the query sentence and the reference sentence.

    :param simSent: a `SimilarSent` dict
    :param claimSimResult: the `SemanticClaimSimilarityResult` containing `simSent`
    :param cfg: configuration options
    :returns: a `QSentCredReview`
    :rtype: dict

    """
    aggqsent_simreview = aggsent_simreviewer.similarSent_as_SentPolarSimilarityReview(
        simSent, claimSimResult, cfg)
    dbSent_credreview = dbsent_credrev.similarSent_as_DBSentCredRev(simSent, cfg)
    return aggregate_subReviews(aggqsent_simreview, dbSent_credreview, cfg)


def aggregate_subReviews(aggqsent_simreview, dbSent_credreview, cfg):
    """Combines a polar similarity review and a dbSent credReview into a `QSentCredReview`

    :param aggqsent_simreview: a `SentPolarSimilarityReview` dict
      describing the polar similarity between the query and the db
      sentences
    :param dbSent_credreview: a `DBSentCredReview` for the db sentence
    :param cfg: configuration options
    :returns: a `QSentCredReview` that provides an aggregate
     credibility review and rating for the query sentence
    :rtype: dict
    """
    agg_start = citimings.start()
    
    dbSent_credval = dictu.get_in(dbSent_credreview, ['reviewRating', 'ratingValue'])
    assert dbSent_credval >= -1.0 and dbSent_credval <= 1.0
    dbSent = dictu.get_in(dbSent_credreview, ['itemReviewed', 'text'])
    
    agg_sim = dictu.get_in(aggqsent_simreview, ['reviewRating', 'ratingValue'])
    qSent = dictu.get_in(aggqsent_simreview, ['itemReviewed', 'sentA', 'text'])
    dbSent2 = dictu.get_in(aggqsent_simreview, ['itemReviewed', 'sentB', 'text'])
    assert dbSent == dbSent2, '%s != %s' % (dbSent, dbSent2)
    
    agg_cred_conf = dictu.get_in(dbSent_credreview, ['reviewRating', 'confidence']) * abs(agg_sim)
    assert agg_cred_conf >= 0.0 and agg_cred_conf <= 1.0, agg_cred_conf
    sim_polarity = -1 if agg_sim < 0 else 1
    
    isBasedOn = [aggqsent_simreview, dbSent_credreview] # subReviews
    subRatings = [rev.get('reviewRating')
                  for rev in isBasedOn
                  if rev.get('reviewRating') is not None]
    sub_bots = [] # TODO: extract author of subRatings?, directly request bot_info of deps?
    # the sentence ...
    explanation = '*%s*:\n\n * `%s`\nthat seems *%s* %s' % (
        aggqsent_simreview.get('headline', ' '), # the polar relation between qsent and dbsent
        dbSent,
        credlabel.rating_label(dbSent_credreview['reviewRating'], cfg),
        #credlabel.describe_credval(dbSent_credval, cred_dict=dbSent_credreview), # TODO: remove
        dictu.get_in(dbSent_credreview, ['reviewRating', 'ratingExplanation']))
    revRating = {
        '@context': ci_context,
        '@type': 'AggregateRating',
        'additionalType': ['Rating'],
        'reviewAspect': 'credibility',
        'reviewCount': agg.total_reviewCount(subRatings) + len(isBasedOn),
        'ratingCount': agg.total_ratingCount(subRatings),
        'ratingValue': sim_polarity * dbSent_credval,
        'confidence': agg_cred_conf,
        'ratingExplanation': explanation
    }
    return {
        '@context': ci_context,
        '@type': 'QSentCredReview',
        'additionalType': content.super_types('QSentCredReview'),
        'itemReviewed': content.as_sentence(qSent, cfg=cfg),
        'text': 'Sentence `%s` seems *%s* as it %s' % (
            qSent, credlabel.rating_label(revRating, cfg),
            explanation),
        'dateCreated': isodate.now_utc_timestamp(),
        'author': bot_info(sub_bots, cfg),
        'reviewAspect': 'credibility',
        'reviewRating': revRating,
        'isBasedOn': isBasedOn
    }
    

def ensure_credibility(relsents, cfg={}):
    """Add a `similarity_credibility` field to input relsents
    It does this by combining the domain credibility, claimReview and
    possibly stance detection results.

    **Depreated**: use similarSent_as_QSentCredReview and/or
      aggregate_subReviews

    :param relsents: list of or a single SimilarSent dict. You should
      have already performed claimReview credibility rating
      normalisation. See `enhance_relsent`.
    :returns: input SimilarSent with additional credibility field
    :rtype: dict

    """
    if type(relsents) == list:
        return [ensure_credibility(rs, cfg=cfg) for rs in relsents]
    assert type(relsents) == dict
    relsent = relsents  # single relsent
    assert 'similarity' in relsent
    sim = relsent.get('similarity', 0.5)
    assert sim >= 0.0 and sim <= 1.0

    top_cred = dbsent_credrev.select_top_relsent_cred(relsent)
    top_credval = top_cred.get('value', 0.0)
    top_conf = top_cred.get('confidence', 0.0)
    assert top_conf >= 0.0 and top_conf <= 1.0
    
    # doc_stance = relsent.get('doc_stance', None)
    # doc_stance_conf = relsent.get('doc_stance_confidence', 0.0)
    sent_stance = relsent.get('sent_stance', None)
    sent_stance_conf = relsent.get('sent_stance_confidence', 0.0)

    polarity = -1 if sent_stance == 'disagree' else 1

    agg_sim = aggsent_simreviewer.calc_agg_polarsim(sim, sent_stance, sent_stance_conf, cfg)
    agg_conf = top_conf * abs(agg_sim)
    explanation = 'Claim *%s*:\n\n * %s\nthat %s. %s' % (
        simlabel.claim_rel_str(sim, sent_stance),
        relsent.get(
            'sentence',
            "missing sentence (keys %s)" % (
                list(relsent.keys()))),
        credlabel.describe_credval(top_credval, cred_dict=top_cred),
        top_cred.get('explanation', ''))

    relsent['similarity_credibility'] = {  # MUTATE input!!
        'value': top_credval * polarity,
        'confidence': agg_conf,
        'explanation': explanation
    }
    assert agg_conf >= 0.0 and agg_conf <= 1.0, agg_conf
    assert top_credval >= -1.0 and top_credval <= 1.0
    return relsent



    
