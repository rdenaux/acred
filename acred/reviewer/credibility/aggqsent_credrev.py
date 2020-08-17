#
# Copyright (c) 2020 Expert System Iberia
#
"""Aggregation credibility reviewer for a "query" sentence. I.e. a
sentence that may not be in the co-inform database yet. It aggregates
the reviews for various `qsent_credrev`s, which each review the
credibility of the query sentence based on its similarity with a
sentence in the co-inform DB.
"""
import logging
from esiutils import isodate
from esiutils import citimings, dictu, bot_describer, hashu
from acred import content, itnorm
from acred.rating import agg
from acred.reviewer.credibility import dbsent_credrev
from acred.reviewer.credibility import label as credlabel
from acred.reviewer.credibility import qsent_credrev
# TODO: remove following imports as they're not really direct dependencies
#from acred.reviewer.similarity import semsent_simrev
from acred.reviewer.credibility import website_credrev
from acred.service import claimsim
from acred.reviewer.factcheckability import sent_worthrev


logger = logging.getLogger(__name__)

version = '0.1.1'
ci_context = 'http://coinform.eu'

content.register_acred_type('AggQSentCredReviewer', {
    'super_types': ['Bot', 'SoftwareApplication'],
    'ident_keys': ['@type', 'name', 'dateCreated', 'softwareVersion', 'isBasedOn', 'launchConfiguration'],
    'route_template': '/bot/{@type}/{softwareVersion}/{identifier}',
    'itemref_keys': ['isBasedOn']
})

content.register_acred_type('AggQSentCredReview', {
    'super_types': ['CredibilityReview', 'Review'],
    'ident_keys': ['@type', 'dateCreated', 'author', 'itemReviewed', 'reviewRating', 'isBasedOn'],
    'route_template': '/review/{identifier}',
    'itemref_keys': ['author', 'itemReviewed', 'reviewRating', 'isBasedOn']
})

def review(items, config):
    """Reviews the incoming item and returns a Review for it

    :param items: a list of items that must be `Sentence` instances.
    :param config: a configuration map
    :returns: one or more Review objects for the input items
    :rtype: list of dict
    """
    # We require a list: much faster than individual sents
    assert type(items) == list, "A list of input sentences is required"
    for item in items:
        assert content.is_sentence(item), '%s' % (item)
    rev_worth = config.get('worthiness_review', False)
    if rev_worth:
        factual_items, nfs_items = partition_factual_sentences(items, config)
    else:
        factual_items, nfs_items = items, []  # assume all items are factual

    assert len(factual_items + nfs_items) == len(items), '%s+%s != %s %s' % (
        len(factual_items), len(nfs_items), len(items), items) 
    factual_reviews = review_factual_items(factual_items, config)
    nfs_reviews = [as_non_verifiable_reviews(item, config) for item in nfs_items]

    return restore_order(items, factual_reviews + nfs_reviews)


def restore_order(items, revs):
    assert len(items) == len(revs)
    text2i = {item['text']: i for i, item in enumerate(items)}
    result = sorted(revs, key=lambda rev: text2i[rev['itemReviewed']['text']])
    assert len(result) == len(revs)
    return result



def review_factual_items(factual_items, config):
    claimsim_results = claimsim.find_related_sentences([s['text'] for s in factual_items], config)
    factual_result = [
        claimsim_result_as_aggQSentCredReview(csr, factual_item.get('worthinessReview'), config)
        for csr, factual_item in zip(claimsim_results, factual_items)]
    assert len(factual_items) == len(factual_result), '%s != %s' % (
        len(factual_items), len(factual_result))
    return factual_result


def as_non_verifiable_reviews(nfs_item, cfg):
    worth_rev = nfs_item.get('worthinessReview')
    rating = no_verifiable_rating()
    mod_nfs_item = nfs_item.copy()
    mod_nfs_item.pop('worthinessReview')
    aggqsent = {
        **base_AggQSentCredReview(cfg),
        'itemReviewed': mod_nfs_item,
        'text': 'Sentence `%s` seems *not verifiable* as it %s' % (
            mod_nfs_item['text'], rating['ratingExplanation']),
        'reviewRating': {
            **rating,
            'identifier': itnorm.calc_identifier(rating, cfg)
        },
        'isBasedOn': [worth_rev]
    }
    return {**aggqsent,
            #'identifier': itnorm.calc_identifier(aggqsent, cfg)
    }


def partition_factual_sentences(items, cfg):
    """Process the incoming `items` and split it between worthy and unworthy

    :param items: list of items
    :type items: list of dicts
    :return: a list of factual statements and a list of non-factual
    :rtype: lists
    """
    worth_item_revs = rev_item_worthiness(items, cfg)
    logger.info("Reviewed sentence worthiness")
    factual_items = [it for it in worth_item_revs
                     if dictu.get_in(it, ['worthinessReview', 'reviewRating',
                                          'ratingValue'], 'worthy') == 'worthy']
    nfs_items = [it for it in worth_item_revs
                     if dictu.get_in(it, ['worthinessReview', 'reviewRating',
                                          'ratingValue']) == 'unworthy']
    assert len(items) == len(factual_items) + len(nfs_items), '%s' % (
        'The total number of factual and non factual items '
        'must be the same as the initial number of items sent to the process')
    return factual_items, nfs_items



def rev_item_worthiness(items, cfg):
    """Process the incoming list of `items` and reviews the worthiness

    :param items: list of items
    :type items: list of dicts
    :return: list of items with a worthiness review
    :rtype: list of dicts
    """
    worth_reviews = sent_worthrev.review(items, cfg)
    return [{
        **it,
        'worthinessReview': sent_worth} for it, sent_worth in zip(items, worth_reviews)]


def default_sub_bots(cfg):
    return [dbsent_credrev.default_bot_info(cfg),
            qsent_credrev.default_bot_info(cfg)]


def bot_info(sub_bots, cfg):
    """Returns a description for this AggQSentCredReviewer

    :param cfg: 
    :returns: 
    :rtype: 
    """
    result = {
        '@context': ci_context,
        '@type': 'AggQSentCredReviewer',
        'additionalType': content.super_types('AggQSentCredReviewer'),
        'name': 'ESI Aggregate Query Sentence Credibility Reviewer',
        'description': 'Reviews the credibility of a query setence by comparing it to semantically similar sentences in the Co-inform DB and the credibility of those.',
        'author': bot_describer.esiLab_organization(),
        'dateCreated': '2020-03-19T15:09:00Z',
        'applicationCategory': [ 'Disinformation Detection' ],
        'softwareRequirements': ['python'],
        'softwareVersion': version,
        'executionEnvironment': bot_describer.inspect_execution_env(),
        'isBasedOn': sub_bots,
        'launchConfiguration': {
            'acred_pred_claim_search_url': cfg.get(
                'acred_pred_claim_search_url',
                'http://localhost:8070/test/api/v1/claim/internal-search')
        }
    }
    return {
        **result,
        'identifier': hashu.hash_dict(dictu.select_keys(
            result,
            content.ident_keys(result)
        ))
    }

def default_bot_info(cfg):
    return bot_info(default_sub_bots(cfg), cfg)

def calc_claim_cred(sents, cfg):
    """Produces ClaimCredibilityAssessments for a list of sents

    :param sents: list of input sentences (assumed to be claims)
    :param cfg: config parameters
    :returns: a list of coinform `ClaimCredibility` assessments
    :rtype: list
    """
    start = citimings.start()
    claimsim_results = claimsim.find_related_sentences(sents, cfg)
    relsents_t = citimings.timing('find_relsents', start)
    
    result = [claimsim_result_as_claimcred(csr, cfg)
              for csr in claimsim_results]
    for claimcred in result:  # include search timings in results
        agg_t = claimcred['timings']
        claimcred['timings'] = citimings.timing(
            'claimcred', start, [relsents_t, agg_t])

    return result


def base_AggQSentCredReview(cfg):
    return {
        '@context': ci_context,
        '@type': 'AggQSentCredReview',
        'additionalType': ['CredibilityReview', 'Review'],
        'dateCreated': isodate.now_utc_timestamp(),
        'author': default_bot_info(cfg) # default sub_bots
    }

def default_rating():
    return {
        '@type': 'Rating',
        'reviewAspect': 'credibility',
        'ratingValue': 0.0,
        'confidence': 0.0,
        # the sentence ...
        'ratingExplanation': 'has no (close) matches in the Co-inform database, so we cannot assess its credibility.'
    }

def no_verifiable_rating():
    return {
        '@type': 'Rating',
        'reviewAspect': 'credibility',
        'ratingValue': 0.0,
        'confidence': 0.0,
        # the sentence ...
        'ratingExplanation': "doesn't seem to be a factual statement, or doesn't seem worth checking."
    }

def claimsim_result_as_aggQSentCredReview(claimsim_result, worth_rev, cfg):
    """Convert a `SemanticClaimSimilarityResult` into a `AggQSentCredReview`

    This refactors `claimsim_result_as_claimcred`.

    :param claimsim_result: list of SimSent reviews
    :param worth_rev: dict with check worthiness review
    :param cfg: config options
    :returns: a `AggQSentCredReview`
    :rtype: dict
    """
    qsent = claimsim_result['q_claim']  # qsent
    relsents = claimsim_result['results'] # simsents

    itemReviewed = content.as_sentence(qsent, cfg=cfg)
    if len(relsents) == 0:
        rating = default_rating()
        aggqsent = {
            **base_AggQSentCredReview(cfg),
            'itemReviewed': itemReviewed,
            'text': 'Sentence `%s` seems *not verifiable* as it %s' % (
                itemReviewed['text'], rating['ratingExplanation']),
            'reviewRating': {
                **rating,
                'identifier': itnorm.calc_identifier(rating, cfg)
            },
            'isBasedOn': [worth_rev] if worth_rev else []
        }
        result = {**aggqsent,
                  # 'identifier': itnorm.calc_identifier(aggqsent, cfg),
        }
        return result
    
    qsent_credrevs = [
        qsent_credrev.similarSent_as_QSentCredReview(simSent, claimsim_result, cfg)
        for simSent in relsents]
    # TODO: remove subReviews if based on websiteCredRev for a factchecker (but not a claimReview)
    for qscr in qsent_credrevs:
        assert qscr['itemReviewed'] == itemReviewed
        assert dictu.get_in(qscr, ['reviewRating', 'reviewAspect']) == 'credibility'

    subRatings = [rev.get('reviewRating')
                  for rev in qsent_credrevs
                  if rev.get('reviewRating') is not None] + ([worth_rev.get('reviewRating')] if worth_rev
                                                                and worth_rev.get('reviewRating') is not None else [])


    top_qscr = agg.select_most_confident_review(qsent_credrevs, cfg)
    top_rating = top_qscr.get('reviewRating', {})
    reviewRating = {
        '@type': 'AggregateRating',
        'reviewAspect': 'credibility',
        'ratingValue': top_rating.get('ratingValue', 0.0),
        'confidence': top_rating.get('confidence', 0.0),
        'ratingExplanation': top_rating.get('ratingExplanation', None),
        'ratingCount': agg.total_ratingCount(subRatings),
        'reviewCount': agg.total_reviewCount(subRatings) + len(qsent_credrevs) + len([worth_rev] if worth_rev else [])
    }

    result = {
        **base_AggQSentCredReview(cfg),
        'itemReviewed': itemReviewed,
        'text': 'Sentence `%s` seems *%s* as it %s' % (
            itemReviewed.get('text', '??'),
            credlabel.rating_label(reviewRating, cfg),
            reviewRating['ratingExplanation']
        ),
        'reviewRating': {
            **reviewRating,
            'identifier': itnorm.calc_identifier(reviewRating, cfg)
        },
        'isBasedOn': qsent_credrevs + ([worth_rev] if worth_rev else [])
    }
    return result


def claimsim_result_as_claimcred(claimsim_result, cfg):
    """Convert a `SemanticClaimSimilarityResult` into a `ClaimCredibility`

    :param claimsim_results: 
    :param cfg: 
    :returns: 
    :rtype: 
    """
    # TODO: delegate to reviewers to convert claimsim_result into
    # QSentCredReview, DBClaimCredibilityReview, WebSiteCredReview, etc.
    agg_start = citimings.start()
    qsent = claimsim_result['q_claim']  # qsent
    relsents = claimsim_result['results'] # simsents

    # sentSimReviews = [ # TODO: remove, just for feedback during refactoring
    #     semsent_simrev.similarSent_as_SentSimilarityReview(simSent, claimsim_result, cfg)
    #     for simSent in relsents]

    for rs in relsents:
        # claim search no longer does domain credibility, so we have to do it here
        if 'domain_credibility' not in rs:
            rs['domain_credibility'] = website_credrev.calc_domain_credibility(
                rs['domain'])
    
    relsents = [add_relative_credibility(rs, cfg) for rs in relsents]
    cred_dict = aggregate_credibility(relsents, cfg)
    cred_dict['source'] = 'credibility of %d related claims ' % len(
        relsents)
    agg_t = citimings.timing('claim_relsent_agg', agg_start)
    return {
        '@context': ci_context,
        '@type': 'ClaimCredibility',
        'claim': qsent,
        'item_assessed': {
            '@context': ci_context,
            '@type': 'Claim',
            'claim': qsent
        },
        # 'sentenceSimilarityReview': sentSimReviews,
        'aggQSentCredReview': claimsim_result_as_aggQSentCredReview(claimsim_result, cfg),
        'related_claims': _partition_related_sents(relsents, cfg),
        'date_assessed': isodate.now_utc_timestamp(),
        'assessor': {'@context': ci_context,
                     '@type': 'CredibilityAssessor',
                     'name': 'SemanticSimilarityClaimCredibilityAssessor',
                     'version': '20200208'},
        'credibility': cred_dict,
        'timings': agg_t 
    }
    

def add_relative_credibility(relsent, cfg):
    """Add an aggregate `similarity_credibility` to a `SimilarSent`

    Additional utility fields may also be added.

    :param relsent: a SimilarSent dict for which to add a relative credibility
    :param cfg: config options to guide the credibility assessment
    :returns: a modified relsent with additional fields and possibly modified
      values.
    :rtype: dict (SimilarSent)
    """
    relsent = dbsent_credrev.enhance_relsent(relsent, cfg)
    return qsent_credrev.ensure_credibility(relsent, cfg)


def aggregate_credibility(relsents, cfg):
    # exclude relsents which are by factcheckers but are not claimReviews
    def is_claimReview(rs):
        return rs.get('claimReview', None) is not None

    def by_factchecker_but_not_cr(rs):
        return dbsent_credrev.is_by_factchecker(rs, cfg) and not is_claimReview(rs)

    all_sim_creds = [rs.get('similarity_credibility', {})
                     for rs in relsents
                     if not by_factchecker_but_not_cr(rs)]
    if len(all_sim_creds) == 0:
        return {
            'value': 0.0,
            'confidence': 0.0,
            'explanation': "No similar claims found"
        }
    all_sim_creds = sorted(all_sim_creds,
                           key=lambda cred: cred.get('confidence', -1.0),
                           reverse=True)
    top_cred = all_sim_creds[0]  # select most confident
    return top_cred


def _partition_related_sents(relsents, cfg):
    no_cr_relsents, claimReviewed = partition(
        relsents,
        lambda relsent: relsent.get('claimReview', None) is None)
    factchecker_relsents, non_fc_relsents = partition(
        no_cr_relsents,
        lambda relsent: dbsent_credrev.is_by_factchecker(relsent, cfg))
    credible_pub_sents, noncredible_pub_sents = partition(
        non_fc_relsents,
        lambda relsent: has_credible_pub(relsent))
    return {
        '@context': ci_context,
        '@type': 'PartitionedRelatedSentences',
        'reviewed-claims': claimReviewed,
        'fact-checker-sentences': factchecker_relsents,
        'credible-pub-sentences': credible_pub_sents,
        'non-credible-pub-sentences': noncredible_pub_sents
    }


def partition(seq, filter_fn):
    yes_part = [elt for elt in seq if filter_fn(elt)]
    no_part = [elt for elt in seq if not filter_fn(elt)]
    assert len(yes_part) + len(no_part) == len(seq)
    return yes_part, no_part


def has_credible_pub(related_sentence):
    try:
        val = related_sentence['domain_credibility']['credibility']['value']
        return val > 0.25  # range is [-1, 1]
    except Exception as e:
        logger.error("Missing domain credibility")
        return False
