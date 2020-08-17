#
# Copyright (c) 2020 Expert System Iberia
#
"""Credibility reviewer for a WebSite
Implemented via the MisinfoMe source service.
"""
import requests
import logging
import functools
import datetime
from urllib.parse import urlparse
from acred import content
from acred.reviewer.credibility import label as credlabel
from esiutils import citimings, isodate, dictu, bot_describer, hashu


logger = logging.getLogger(__name__)

ci_context = 'http://coinform.eu'
misinfome_url = 'https://socsem.kmi.open.ac.uk/misinfo'
source_cred_url = "%s/api/credibility/sources/" % misinfome_url

content.register_acred_type('MisinfoMeSourceCredReviewer', {
    'super_types': ['SoftwareApplication', 'Bot'],
    'ident_keys': ['@type', 'name', 'dateCreated', 'softwareVersion', 'isBasedOn', 'launchConfiguration'],
    'route_template': '/bot/{@type}/{softwareVersion}/{identifier}',
    'itemref_keys': ['isBasedOn']
})

content.register_acred_type('WebSiteCredReview', {
    'super_types': ['CredibilityReview', 'Review'],
    'ident_keys': ['@type', 'dateCreated', 'author', 'itemReviewed', 'reviewRating'], # isBasedOn?
    'route_template': '/review/{identifier}',
    'itemref_keys': ['author', 'itemReviewed', 'reviewRating']
})

def misinfoMeSourceCredReviewer():
    result = {
    '@context': 'http://coinform.eu',
    '@type': 'MisinfoMeSourceCredReviewer',
    # Since we don't control this bot, we assume versions,
    #  an thus results, may change on a weekly basis
    #  So we use the start of the current week as the version
    'softwareVersion': isodate.start_of_week_utc_timestamp(datetime.datetime.utcnow()),
    'additionalType': content.super_types('MisinfoMeSourceCredReviewer'),
    'url': misinfome_url,
    'applicationSuite': 'MisinfoMe'
    }
    return {
        **result,
        'identifier': hashu.hash_dict(dictu.select_keys(
            result, content.ident_keys(result)))
    }

def review(item, config):
    """Reviews the incoming item and returns a Review for it

    :param item: a single item or a list of items, in this case the 
      items should be `WebSite` instances.
    :param config: a configuration map
    :returns: one or more Review objects for the input items
    :rtype: dict or list of dict
    """
    if type(item) == list:
        return [review(it, config) for it in item]

    start = citimings.start()
    if type(item) == str:
        logger.warning('Assuming this is a website, you should wrap it into a `WebSite`')
        item = content.str_as_website(item)

    assert content.is_website(item)
    assert 'url' in item
    url = item['url']
    assert type(url) == str
    domcred = calc_domain_credibility(url, config)
    result = from_old_DomainCredibility(domcred, config)
    return result


def similarSent_as_WebSiteCredRev(simSent, cfg):
    assert content.is_SimilarSent(simSent), '%s' % (simSent)
    if 'domain_credibility' in simSent:
        return from_old_DomainCredibility(simSent['domain_credibility'], cfg)
    elif 'domain' in simSent:
        dom = simSent['domain']
        if type(dom) is str:
            dom = content.str_as_website(dom)
        return review(dom, cfg)
    else:
        doc_url = simSent['doc_url']
        domain = content.str_as_website(content.domain_from_url(doc_url))
        return review(domain, cfg)


def from_old_DomainCredibility(dom_cred, cfg):
    """Converts a `DomainCredibility` into a `WebSiteCredReview`

    :param dom_cred: a `DomainCredibility` dict
    :param cfg: configuration options
    :returns: a `WebSiteCredReview`
    :rtype: dict
    """
    domain_url = dom_cred.get('itemReviewed', 'missing_website')  # str
    itemReviewed = content.str_as_website(domain_url)  # reconstruct WebSite

    ratingVal = dictu.get_in(dom_cred, ['credibility', 'value'], 0.0)
    explanation = 'based on %d review(s) by external rater(s)%s' % (
                len(dom_cred['assessments']), example_raters_markdown(dom_cred))
    return {
        '@context': 'http://coinform.eu',
        '@type': 'WebSiteCredReview',
        'additionalType': content.super_types('WebSiteCredReview'),
        'itemReviewed': itemReviewed,
        'text': 'Site `%s` seems *%s* %s' % (
            itemReviewed.get('name', '??'), credlabel.describe_credval(ratingVal, None), explanation),
        'author': misinfoMeSourceCredReviewer(),
        'reviewRating': {
            '@type': 'AggregateRating',
            'reviewAspect': 'credibility',
            'ratingValue': ratingVal,
            'confidence': dictu.get_in(dom_cred, ['credibility', 'confidence'], 0.5),
            'ratingExplanation': explanation,
            'reviewCount': len(dom_cred['assessments']),
            'ratingCount': len(dom_cred['assessments'])
        },
        'dateCreated': dom_cred.get('dateCreated', isodate.now_utc_timestamp()),
        'reviewAspect': 'credibility',
        'isBasedOn': [], # TODO:
        'isBasedOn_assessments': dom_cred['assessments'],
        'timings': dom_cred.get('timings', {})
    }


def example_raters_markdown(dom_cred):
    site_raters = [assessment.get('origin')
                   for assessment in dom_cred.get('assessments',[])
                   if assessment.get('origin', None) is not None]
    site_rater_mdlinks = ['[%s](%s)' % (sr.get('name'), sr.get('homepage'))
                         for sr in site_raters]
    if len(site_rater_mdlinks) == 0:
        return ' (missing data about raters)'
    if len(site_rater_mdlinks) == 1:
        return ' (%s)' % site_rater_mdlinks[0]
    elif len(site_rater_mdlinks) == 2:
        return ' (%s)' % ' or '.join(site_rater_mdlinks)
    else:
        return ' (e.g. %s)' % ' or '.join(site_rater_mdlinks[:2])
    

def penalise_credibility(domcred, cfg):
    cred = domcred['credibility']
    orig_confid = cred['confidence']
    cred['confidence'] = orig_confid * 0.5
    cred['explanation'] = "%s %s" % (
        "Domain credibility for a factchecker should be mixed.",
        "Reduced from standard confidence.")
    return domcred


#####
## MisinfoMe client
####


def calc_domain_credibility(domain, cfg={}):
    """Calculates a `DomainCredibility` for a domain via MisinfoMe

    Note that `DomainCredibility` is deprecated, use the `review` method 
    which produces a `WebSiteCredReview` instead.

    :param domain: str e.g. `www.snopes.com`
    :returns: a `DomainCredibility`
    :rtype: dict
    """
    if domain is None:
        return default_domain_crediblity(
            domain, "Default credibility for unknown domain")
    else:
        assert type(domain) == str, 'Expecting str, but was %s' (
            type(domain))
        start = citimings.start()
        try:
            return {
                **misinfome_source_credibility(domain),
                '@context': 'DomainCredibility',
                '@type': 'DomainCredibility',
                'dateCreated': isodate.now_utc_timestamp(),
                'timings': citimings.timing(
                    'misinfome_source_credibility', start)
            }
        except Exception as e:
            logger.error("Failed misinfome source credibility. " + str(e))
            return default_domain_crediblity(
                domain, "Unable to retrieve credibility assessment")


@functools.lru_cache(maxsize=256)
# @cache.memoize(timeout=500)
def misinfome_source_credibility(domain):
    req_url = "%s?source=%s" % (source_cred_url, domain)
    resp = requests.get(req_url)
    resp.raise_for_status()
    return resp.json()


def default_domain_crediblity(domain, explanation):
    start = citimings.start()
    return {
        "credibility": {
            '@context': ci_context,
            '@type': 'DomainCredibility',
            'item_assessed': domain,
            "value": 0.0,  # in range [-1, 1]
            "confidence": 0.0,
            "explanation": explanation,
            'timings': citimings.timing('default_domain_crediblity', start)
        },
        "assessments": []
    }

