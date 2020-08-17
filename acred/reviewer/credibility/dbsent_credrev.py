#
# Copyright (c) 2020 Expert System Iberia
#
"""Credibility reviewer for a sentence that is already in the
co-inform DB. Produces a `DBSentCredReview`.

This rating is based either on:
 * a (normalised) `ClaimReview` for the sentence in the DB, or
 * a domain credibility for documents where the sentence was found

"""
import logging
from acred.reviewer.credibility import website_credrev
from acred.reviewer.credibility import label as credlabel
from acred.reviewer.credibility import claimreview_normalizer as crn
from acred import content
from acred.rating import agg
from esiutils import dictu, isodate, bot_describer, hashu


version = '0.1.0'
dateCreated = '2020-03-20T20:03:00Z'
ci_context = 'http://coinform.eu'
logger = logging.getLogger(__name__)


content.register_acred_type('DBSentCredReviewer', {
    'super_types': ['SoftwareApplication', 'Bot'],
    'ident_keys': ['@type', 'name', 'dateCreated', 'softwareVersion',
         'isBasedOn', 'launchConfiguration'],
    'route_template': '/bot/{@type}/{softwareVersion}/{identifier}',
    'itemref_keys': ['isBasedOn']
})

content.register_acred_type('DBSentCredReview', {
    'super_types': ['CredibilityReview', 'Review'],
    'ident_keys': ['@type', 'dateCreated', 'author', 'itemReviewed', 'reviewRating', 'isBasedOn'],
    'route_template': '/review/{identifier}',
    'itemref_keys': ['author', 'itemReviewed', 'reviewRating', 'isBasedOn']
})


def review(item, config):
    """Reviews the incoming item and returns a Review for it

    :param item: a single item or a list of items, in this case the 
      items must be `Sentence` instances.
    :param config: a configuration map
    :returns: one or more Review objects for the input items
    :rtype: dict or list of dict
    """
    raise NotImplemented()


def default_sub_bots(cfg):
    return [website_credrev.misinfoMeSourceCredReviewer(), crn.bot_info(cfg)]


def bot_info(sub_bots, cfg):
    result = {
        '@context': ci_context,
        '@type': 'DBSentCredReviewer',
        'name': 'ESI DB Sentence Credibility Reviewer',
        'description': 'Estimates the credibility of a sentence in the Co-inform DB based on known ClaimReviews or websites where the sentence has been published.',
        'additionalType': content.super_types('DBSentCredReviewer'),
        'author': bot_describer.esiLab_organization(),
        'dateCreated': dateCreated,
        'softwareVersion': version,
        'url': 'http://coinform.eu/bot/DBSentCredReviewer/%s' % version,
        'applicationSuite': 'Co-inform',
        'isBasedOn': sub_bots, 
        'launchConfiguration': {
            'factchecker_website_to_qclaim_confidence_penalty_factor': float(
                cfg.get('factchecker_website_to_qclaim_confidence_penalty_factor', 0.5)),
            'acred_factchecker_urls': cfg.get('acred_factchecker_urls', [])
        }
    }
    ident = hashu.hash_dict(dictu.select_keys(
        result, content.ident_keys(result)))
    return {
        **result,
        'identifier': ident
    }

def default_bot_info(cfg):
    return bot_info(default_sub_bots(cfg), cfg)


def similarSent_as_DBSentCredRev(simSent, cfg):
    """Converts the `simSent` into an equivalent `DBSentCredRev`iew

    :param simSent: a `SimilarSent` object as produced by the claim search
    :param cfg: configuration options
    :returns: a `DBSentCredReview`
    :rtype: dict
    """
    db_Sentence = similarSent_as_DB_Sentence(simSent, cfg)
    claimReview = simSent.get('claimReview')
    webSiteCred = website_credrev.similarSent_as_WebSiteCredRev(simSent, cfg)

    return aggregate_subReviews(db_Sentence, claimReview, webSiteCred, cfg)


def aggregate_subReviews(db_Sentence, claimReview, webSiteCred, cfg):
    """Aggregates (claim and WebSite) reviews about a DB Sentence into a
       credibility review

    :param db_Sentence: a `Sentence` in the Co-inform database

    :param claimReview: a `ClaimReview` for the db_Sentence. May be
      None if no claim review is available for the sentence. In
      general, the claim review will not have been normalised
      (i.e. mapped onto the co-inform accuracy/credibility scales)

    :param webSiteCred: a `WebSiteCredReview` for a webSite where the
    `db_Sentence` was published.

    :param cfg: configuration options
    :returns: a `DBSentCredReview`
    :rtype: dict
    """
    nClaimReview = crn.normalise(claimReview, cfg)
    if nClaimReview is None:
        nClaimReview = {}
    
    nWebSiteRating = websiteCredRev_as_qclaimCredRating(webSiteCred, cfg)

    assert type(nWebSiteRating['confidence']) == float
    assert type(dictu.get_in(nClaimReview, ['reviewRating', 'confidence'], 0.0)) == float
    subRatings = [nWebSiteRating, nClaimReview.get('reviewRating', None)]
    subRatings = [r for r in subRatings if r is not None]
    sel_rating = agg.select_most_confident_rating(subRatings)

    isBasedOn = [webSiteCred, nClaimReview]
    isBasedOn = [ibo for ibo in isBasedOn
                 if ibo is not None and ibo != {}]

    reviewCount = agg.total_reviewCount(subRatings) + len(isBasedOn)
    ratingCount = agg.total_ratingCount(subRatings)

    # should be a superset of [ibo.get('author') for ibo in isBasedOn]
    sub_bots = default_sub_bots(cfg)
    appears_in_docs = db_Sentence.get('appearance', [])
    appears_in_doc = appears_in_docs[0] if appears_in_docs else None
    link_to_doc = md_link_to_doc(appears_in_doc)
    revRating = {
        '@type': 'AggregateRating',
        'reviewAspect': 'credibility',
        'reviewCount': reviewCount,
        'ratingCount': ratingCount,
        'ratingValue': sel_rating.get('ratingValue', 0.0),
        'confidence': sel_rating.get('confidence', 0.0),
        'ratingExplanation': sel_rating.get('ratingExplanation')
    }
    return {
        '@context': "http://coinform.eu",
        '@type': "DBSentCredReview",
        'additionalType': content.super_types('DBSentCredReview'),
        'itemReviewed': db_Sentence,
        'text': 'Sentence `%s` %sseems *%s* %s' % (
            db_Sentence.get('text', '??'),
            ', in %s, ' % (link_to_doc) if link_to_doc else '',
            credlabel.rating_label(revRating, cfg),
            sel_rating.get('ratingExplanation')
        ),
        'reviewRating': revRating, 
        'reviewAspect': 'credibility',
        'isBasedOn': isBasedOn,
        'dateCreated': isodate.now_utc_timestamp(),
        'author': bot_info(sub_bots, cfg)
    }

def md_link_to_doc(article):
    url = article.get('url')
    site = article.get('domain')
    if url and site:
        return '[%s](%s)' % (site, url)
    elif url:
        return '[this page](%s)' % (url)
    else:
        return None

def websiteCredRev_as_qclaimCredRating(websiteCredRev, cfg):
    wscr = websiteCredRev
    result = {
        '@type': 'AggregateRating',
        'reviewAspect': 'credibility',
        'reviewCount': dictu.get_in(wscr, ['reviewRating', 'reviewCount'], 0),
        'ratingCount': dictu.get_in(wscr, ['reviewRating', 'ratingCount'], 0),
        'ratingValue': dictu.get_in(wscr, ['reviewRating', 'ratingValue'], 0.0),
        'dateCreated': isodate.now_utc_timestamp()
    }
    if is_by_factchecker(websiteCredRev, cfg):
        # reduce domain credibility for fact-checkers, as we want to
        #  focus on their claim reviews even if their confidence is
        #  relatively low.
        #  Refactoring of website_credrev.penalise_credibility
        penalty = float(cfg.get('factchecker_website_to_qclaim_confidence_penalty_factor', 0.5))
        return {
            **result,
            'confidence': dictu.get_in(wscr, ['reviewRating', 'confidence'], 0.0) * penalty,
            'ratingExplanation': "as it was published in site `%s`. %s %s" % (
                dictu.get_in(websiteCredRev, ['itemReviewed', 'name']),
                websiteCredRev.get('text', '(Explanation for website credibility missing)'),
                "However, the site is a factchecker so it publishes sentences with different credibility values.")
        }
    else:
        return {
            **result,
            'confidence': dictu.get_in(wscr, ['reviewRating', 'confidence'], 0.0),
            'ratingExplanation': "as it was published on site `%s`. %s" % (
                dictu.get_in(websiteCredRev, ['itemReviewed', 'name']),
                websiteCredRev.get('text', '(Explanation for website credibility missing)'))
        }


def similarSent_as_DB_Sentence(simSent, cfg):
    inDoc = {
        '@type': 'Article',
        'url': simSent['doc_url'],
        'coinform_collection': simSent['coinform_collection'],
        'publisher': simSent['domain'],
        'inLanguage': simSent['lang_orig'],
        'datePublished': simSent['published_date']
    }
    if 'doc_content' in simSent:
        inDoc['text'] = simSent.get('doc_content')
    return content.as_sentence(simSent['sentence'], appearance=[inDoc], cfg=cfg)

    
def enhance_relsent(relsent, cfg):
    """Add alias fields or default values to relsent and normalise 
    
    Normalise domain_credibility and claimReview.

    But stop short of aggregating domain_cred an claimReview into a
    single DBSentCredibilityReview.

    :param relsent: a `SimilarSent` instance
    :param cfg: 
    :returns: a normalised `SimilarSent`
    :rtype: `SimilarSent` dict
    """
    relsent['coinform_collection'] = relsent.get(
        'coinform_collection', 'unknown')
    return enhance_claimreviewed_relsent(relsent, cfg)


def enhance_claimreviewed_relsent(relsent, cfg):
    if relsent.get('claimReview', None) is None:
        return relsent
    if is_by_factchecker(relsent, cfg):
        # reduce domain credibility for fact-checkers, as we want to
        #  focus on their claim reviews even if their confidence is
        #  relatively low
        website_credrev.penalise_credibility(
            relsent['domain_credibility'], cfg) # modify in place!!
    review = relsent['claimReview']
    return {
        **relsent,
        # 
        'claimReviewed': relsent['sentence'], # alias
        'url': relsent['doc_url'],
        'fact-checker': review.get('author', {}).get('url', None), # alias
        'altName': review.get('reviewRating', {}).get('alternateName', ''),
        'claimReview_credibility_rating': crn.normalised_claimReview_accuracy(review)
    }


def select_top_relsent_cred(relsent):
    """Select the top available credibility source for a relsent
    This will be either the domain_credibility or a normalised 
    claimReview_credibility_rating.
    
    :param relsent: a SimilarSent dict
    :returns: either the domain_credibility, or the claimReview_credibility_rating
      whichever has the highest confidence (although claimReview has precedence). 
      If neither is available, returns an empty dict.
    :rtype: dict
    """
    domcred = relsent.get('domain_credibility', {}).get('credibility', {})
    domcred['source'] = 'domain'
    domcred['domainReviewed'] = relsent.get(
        'domain_credibility', {}).get('itemReviewed', "??")

    cr_cred = relsent.get('claimReview_credibility_rating', {})
    cr_cred['source'] = 'claimReview'

    if 'confidence' in cr_cred and cr_cred.get('confidence', -1.0) > 0.2:
        # avoid domcred, it could point to trustworthy factchecker domain!!
        src_creds = [cr_cred]
    else:
        src_creds = [domcred, cr_cred]
    src_creds = sorted(src_creds,
                       key=lambda cred: cred.get('confidence', -1.0),
                       reverse=True)

    return src_creds[0]  # choose max confidence

def is_by_factchecker(item, cfg):
    if content.is_SimilarSent(item):
        return simSent_is_by_factchecker(item, cfg)
    elif content.is_WebSiteCredReview(item):
        return website_is_factchecker(item.get('itemReviewed'), cfg)
    else:
        return False


def website_is_factchecker(webSite, cfg):
    if webSite is None:
        return False
    assert content.is_webSite(webSite)
    return is_factchecker(webSite.get('url', None),
                          webSite.get('name', None), cfg)
    

def simSent_is_by_factchecker(relsent, cfg):
    url = relsent.get('doc_url', None)
    domain = relsent.get('domain', None)
    return is_factchecker(url, domain, cfg)


def is_factchecker(url, domain, cfg):
    url_nl = content.domain_from_url(url)
    fc_urls = cfg.get('acred_factchecker_urls', [])
    fc_netlocs = [content.domain_from_url(fc_url)
                  for fc_url in fc_urls]
    fc_netlocs = [nl for nl in fc_netlocs if nl is not None]
    if url_nl is not None:
        # match by netloc (scheme independent)
        found = url_nl in fc_netlocs
        if found:
            return found
    elif url is not None:
        # failed to extract netloc, so try to match by prefix
        #  this is *not* scheme independent, so may fail
        found = False
        for fc_url in fc_urls:
            if url.startswith(fc_url):
                logger.info('found match: %s starts with %s' % (
                    url, fc_url))
                found = True
                break
        logger.info('Found no match for %s in %s known factceckers ' % (
            url, len(fc_urls)
        ))
        return found
    
    # no url provided, or no match for url, so match by domain
    if domain is None:
        return False
    else:
        return domain in fc_netlocs
    # return False
