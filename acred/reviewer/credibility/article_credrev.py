#
# Copyright (c) 2020 Expert System Iberia
#
"""Credibility reviewer for an Article.
"""
import logging
from esiutils import citimings
from esiutils import isodate, bot_describer, dictu, hashu
from acred.reviewer.credibility import website_credrev, aggqsent_credrev
from acred.reviewer.credibility import label as credlabel
from acred import content
from acred.rating import agg

# TODO: maybe move these dependencies to a separate module
#  which fetches a reference article
from coinfoapy import cisearch  # TODO: io should be cross-cutting
from semantic_analyzer import url_scraper
from semantic_analyzer import analyzer as semalyzer
from semantic_analyzer import tweetrelsents as tweetsents


logger = logging.getLogger(__name__)

version = '0.1.1'

content.register_acred_type('ArticleCredReviewer', {
    'super_types': ['Bot', 'SoftwareApplication'],
    'ident_keys': ['@type', 'name', 'dateCreated', 'softwareVersion', 'isBasedOn', 'launchConfiguration'],
    'route_template': '/bot/{@type}/{softwareVersion}/{identifier}',
    'itemref_keys': ['isBasedOn']
})


content.register_acred_type('ArticleCredReview', {
    'super_types': ['CredibilityReview', 'Review'],
    'ident_keys': ['@type', 'dateCreated', 'author', 'itemReviewed', 'reviewRating', 'isBasedOn'],
    'route_template': '/review/{identifier}',
    'itemref_keys': ['author', 'itemReviewed', 'reviewRating', 'isBasedOn']
})


def review(item, cfg):
    """Reviews the incoming item and returns a Review for it

    :param item: a single item or a list of items, in this case the 
      items must be an `Article` instances.
    :param cfg: a configuration map
    :returns: one or more Review objects for the input items
    :rtype: dict or list of dict
    """
    # TODO: return only the review, for now return both
    #  the pre-refactoring `ArticleCredibilityAssessment` and
    #  an embedded `ArticleCredReview`. There's no need to do both
    rev_format = cfg.get('acred_review_format', 'schema.org')

    if rev_format == 'cred_assessment':
        result = assess_article_cred(item, cfg)
        del result['analyzed_doc']
        return result
    elif rev_format == 'schema.org':
        if 'content' in item and 'claims_content' in item:
            adoc = item # looks like it's been pre-analysed
        else:
            adoc = analyzed_doc(item, cfg)
        credReview = review_article(adoc, cfg)
        return credReview
    else:
        raise ValueError('revewFormat %s' % rev_format)

def default_sub_bots(cfg):
    return [website_credrev.misinfoMeSourceCredReviewer(),
            aggqsent_credrev.default_bot_info(cfg)]

def bot_info(sub_bots, cfg):
    """Returns a description for this ArticleCredReviewer

    :param sub_bots: bot items used by this ArticleCredReviewer
    :param cfg: config options
    :returns: an `ArticleCredReviewer`
    :rtype: dict
    """
    result = {
        '@context': content.ci_context,
        '@type': 'ArticleCredReviewer',
        'additionalType': content.super_types('ArticleCredReviewer'),
        'name': 'ESI Article Credibility Reviewer',
        'description': 'Reviews the credibility of an article by (i) semantically analysing it to detect relevant claims (ii) getting credibility reviews for the claims and (iii) getting a credibility reviews for the site(s) that published the article.',
        'author': bot_describer.esiLab_organization(),
        'dateCreated': '2020-04-01T17:02:00Z',
        'applicationCategory': ['Disinformation Detection'],
        'softwareRequirements': ['python', 'Cogito'],
        'softwareVersion': version,
        'executionEnvironment': bot_describer.inspect_execution_env(),
        'isBasedOn': sub_bots,
        'launchConfiguration': {
            # any launch configs?
        },
        'taskConfiguration': {
            'cred_conf_threshold': cfg.get('cred_conf_threshold', 0.7),
            'max_claims_in_doc': int(cfg.get('max_claims_in_doc', 5)),
            'relsents_in_colls': cfg.get('relsents_in_colls',
                                         ['generic', 'pilot-se', 'pilot-gr', 'pilot-at',
                                          'factcheckers', 'fc-dev']),
            'target_url_collect_coll': cfg.get('target_url_collect_coll',
                                               cfg.get('default_url_collect_coll', None)),
            'acred_review_format': cfg.get('acred_review_format', 'schema.org')
        }}
    return {
        **result,
        'identifier': hashu.hash_dict(dictu.select_keys(
            result,
            content.ident_keys(result)
        ))
        
    }

def default_bot_info(cfg):
    return bot_info(default_sub_bots(cfg), cfg)

def review_article(adoc, cfg):
    """Main credibility review for a single article

    Refactoring of `assess_article_cred`

    :param adoc: analyzed doc as returned by `analyzed_doc`
    :param cfg: config to guide this assessment
    :returns: a `ArticleCredReview`
    :rtype: dict
    """
    # TODO: ? start = citimings.start()
    domcredReview = adoc_to_website_credReview(adoc, cfg)
    content_credReview = review_doc_content_cred(adoc, cfg)

    # TODO: ? extract sub_bots from website_cr and aggqsent_cr and make sure it matches default_sub_bots?
    agg_rating = aggregate_subReviews(domcredReview, content_credReview, adoc, cfg)
    
    return {
        **base_ArticleCredReview(cfg),
        'author': default_bot_info(cfg),
        'dateCreated': isodate.now_utc_timestamp(),
        'itemReviewed': adoc, # maybe just return ref?
        'text': '%s seems *%s* %s' % (
            markdown_ref_for_article(adoc, cfg),
            credlabel.rating_label(agg_rating, cfg),
            agg_rating.get('ratingExplanation', '(missing explanation)')),
        'reviewRating': agg_rating,
        'isBasedOn': [domcredReview, content_credReview]
    }

def base_ArticleCredReview(cfg):
    return {
        '@context': content.ci_context,
        '@type': 'ArticleCredReview',
        'additionalType': content.super_types('ArticleCredReview'),
        'dateCreated': isodate.now_utc_timestamp(),
    }

def assess_article_cred(article, cfg):
    """Main credibility assessment for a single article

    *Deprecated* you should move to `review_article`

    :param article: valid and normalised article
    :param cfg: config to guide this assessment
    :returns: a credibility assessment for the article
    :rtype: dict
    """
    start = citimings.start()

    adoc = analyzed_doc(article, cfg)
    adoc_t = adoc['timings']

    domcred = adoc_to_domain_cred(adoc, cfg)
    content_cred = assess_doc_content_cred(adoc, cfg)

    agg_cred = aggregate_article_cred(domcred, content_cred, cfg)

    return {
        '@context': content.ci_context,
        '@type': 'ArticleCredibilityAssessment',
        'doc_url': article['url'],
        'item_assessed': article,
        'date_asessed': isodate.now_utc_timestamp(),
        'assessor': {'@context': content.ci_context,
                     '@type': 'CredibilityAssessor',
                     'name': 'ArticleCredibilityAssessor',
                     'version': '20200207'},
        'doc_resolved_url': adoc.get('resolved_url',
                                     adoc.get('url')),
        'analyzed_doc': adoc,
        **agg_cred,
        'sub_assessments': [domcred, content_cred],
        'timings': citimings.timing(
            'assess_article_cred', start,
            [adoc_t, domcred.get('timings', None),
             content_cred.get('timings', None)])
        # 'claims_in_doc': claim_creds,
        # 'domain_credibility': domcred,
        # 'content_credibility': content_cred
    }

def aggregate_subReviews(domcredReview, content_credReview, adoc, cfg):
    """Combines the domain and content credibility reviews for adoc into
      an AggregateRating.

    Refactoring of `aggregate_article_cred`

    :param domcredReview: a `WebsiteCredReview` for the domain/url of adoc
    :param content_credReview: a ``
    :param adoc: the article being rated, useful for generating explanations
    :param cfg: config options
    :returns: an `AggregateRating`
    :rtype: dict
    """
    doc_mdref = markdown_ref_for_article(adoc, cfg)
    thresh = cfg.get('cred_conf_threshold', 0.7)
    content_conf = dictu.get_in(content_credReview, ['reviewRating', 'confidence'], 0.0)
    domcred_conf = dictu.get_in(domcredReview,      ['reviewRating', 'confidence'], 0.0)
    if content_conf >= thresh:
        credval = dictu.get_in(content_credReview, ['reviewRating', 'ratingValue'], 0.0)
        cred_conf = content_conf
        explanation = dictu.get_in(content_credReview, ['reviewRating', 'ratingExplanation'], '')
        if domcred_conf >= thresh:
            explanation += '\nTake into account that it appeared in website `%s`. %s' % (
                dictu.get_in(domcredReview, ['itemReviewed', 'name'],
                             dictu.get_in(domcredReview, ['itemReviewed', 'url'], '(missing)')),
                domcredReview.get('text', '(Explanation for site credibility missing)'))
    elif domcred_conf >= thresh:
        credval = dictu.get_in(domcredReview, ['reviewRating', 'ratingValue'], 0.0)
        penalty_factor = float(cfg.get('article_from_website_conf_factor', 0.9))
        webcred_thresh = float(cfg.get('article_from_website_cred_threshold_penalise', 0.2))
        # penalise confidence if above a threshold
        #  credible website can still publish false claims
        #  but all claims in non-credible website should be questioned
        cred_conf = domcred_conf * penalty_factor if credval >= webcred_thresh else domcred_conf
        explanation = "as it appeared in website `%s`. %s" % (
            dictu.get_in(domcredReview, ['itemReviewed', 'name'],
                         dictu.get_in(domcredReview, ['itemReviewed', 'url'], '(missing)')),
            domcredReview.get('text', '(Explanation for site credibility missing)'))
    else:
        credval = 0.0
        cred_conf = 0.0
        explanation = 'we have insufficient credibility signals from text and website analyses.'
        contentExpl = dictu.get_in(content_credReview, ['text'])
        websiteExpl = dictu.get_in(domcredReview, ['text'])
        if contentExpl or websiteExpl:
            explanation += 'In case it is useful, we include the **weak** credibility signals we found:%s%s' % (
                '\n * %s' % contentExpl if contentExpl else '',
                '\n * %s' % websiteExpl if websiteExpl else '')
    subRatings = [r['reviewRating'] for r in [domcredReview, content_credReview]]
    return {
        '@type': 'AggregateRating',
        'reviewAspect': 'credibility',
        'ratingValue': credval,
        'confidence': cred_conf,
        'ratingExplanation': explanation,
        'ratingCount': agg.total_ratingCount(subRatings),
        'reviewCount': agg.total_reviewCount(subRatings) + 2
    }
    
    

def aggregate_article_cred(domcred, content_cred, cfg):
    """Combines the domain and content sub credibilities for an article
       into an overall credibilty rating.

    *Deprecated* this is the pre-refactoring implementation, see
     `aggregate_article_cred`

    :param domcred: the article's domain credibility map
    :param content_cred: the article's aggregate content credibility
    :param cfg: config options
    :returns: a credibility map
    :rtype: dict
    """
    thresh = cfg.get('cred_conf_threshold', 0.7)
    if content_cred['confidence'] >= thresh:
        cred = content_cred
        if domcred['credibility']['confidence'] >= thresh:
            cred['explanation'] += '\nTake into account that %s' % (
                domcred.get('credibility', {}).get(
                    'explanation',
                    "(missing website credibility explanation)"))
        return cred
    elif domcred['credibility']['confidence'] >= thresh:
        dc = domcred['credibility']
        return {
            'credibility': dc['value'],
            'confidence': dc['confidence'],
            'credibility_label': credlabel.describe_credval(
                dc['value'], cred_dict=None),
            'explanation': "Based on 3rd party trust metrics for %s" % (
                domcred['itemReviewed'])}
    else:
        return {
            'credibility': 0,
            'confidence': 0,
            'credibility_label': credlabel.describe_credval(0, cred_dict=None),
            'explanation':
            'Insufficient confidence in content and domain analyses.'}



def adoc_to_domain_cred(adoc, cfg):
    domain = adoc.get('domain', adoc.get('source_id'))
    if type(domain) == list:
        domain = None if len(domain) == 0 else domain[0]
    if domain is None:
        domain = content.domain_from_url(adoc['url'])
    if domain is None or domain == '':
        logger.warning('Missing domain for url? %s (keys %s)' % (
            adoc['url'], list(adoc.keys())))
        return website_credrev.default_domain_crediblity(
            domain, "unknown domain")
    else:
        return website_credrev.calc_domain_credibility(domain)


def adoc_to_website_credReview(adoc, cfg):
    result = website_credrev.from_old_DomainCredibility(
        adoc_to_domain_cred(adoc, cfg), cfg)
    if website_is_socmedia_platform(result.get('itemReviewed'), cfg):
        # reduce confidence in credibility since content can be written by anyone
        result['reviewRating']['confidence'] = 0.2
    return result

def website_is_socmedia_platform(webSite, cfg):
    if webSite is None:
        return False
    assert content.is_webSite(webSite)
    return is_socmedia_platform(
        webSite.get('url', None),
        webSite.get('name', None), cfg)

def is_socmedia_platform(url, domain, cfg):
    url_nl = content.domain_from_url(url)
    fc_urls = cfg.get('acred_socmedia_urls', ['http://twitter.com',
                                              'http://facebook.com',
                                              'http://instagram.com'])
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


def assess_doc_content_cred(adoc, cfg):
    # deprecated: use review_doc_content_cred instead
    # fetch pre-assessed if assessor is the same as our current assessor
    # otherwise, either compute or queue
    return do_assess_doc_content_cred(adoc, cfg)

def review_doc_content_cred(adoc, cfg):
    """Produces an ArticleCredReview for `adoc` based on its claims

    In practice, only some of its claims may be used.

    Refactoring of `assess_doc_content_cred`

    :param adoc: an analysed document, this is necessary in order to
    have pre-analysed sentences
    :param cfg: config options
    :returns: a `ArticleCredReview`
    :rtype: dict
    """
    # TODO: add timings? start = citimings.start()
    sents_in_doc = select_claims_in_doc(adoc, cfg)
    qsent_credReviews = aggqsent_credrev.review(sents_in_doc, cfg)
    logger.info("Found %d doc subclaim credibilities" % len(qsent_credReviews))
    return aggregate_sentReviews(qsent_credReviews, adoc, cfg)


def gen_sents_from_analysed_doc(adoc, cfg):
    """Generator of `Sentence` instances for `claims` in an analysed doc

    :param adoc: an analyzed doc (see `semantic_analyzer.analyzer.analyze_doc`)
    :param cfg: configuration options
    :returns: a sequence of `Sentence` dicts 
    :rtype: seq
    """
    def cleanup_content(content):
        "Needed for content returned by Solr?"
        result = content.encode("ascii", errors="ignore").decode()  # should be 'utf-8'?
        result = result.replace("\n", "").replace("\t", "").replace("\r", "")
        return result

    claim_contents = doc.get('claims_content', [])
    sent_output_list = [cleanup_content(cc['content'])
                        for cc in claim_contents]
    for sent in sent_output_list:
        yield content.as_sentence(sent, appearance=[adoc], cfg=cfg)
    

def fetch_recent_content_cred(adoc, cfg):
    # fetch pre-assessed if assessor is the same as our current assessor
    # TODO: implement
    return None


def do_assess_doc_content_cred(adoc, cfg):
    start = citimings.start()
    claims_in_doc = select_claims_in_doc(adoc, cfg)
    claim_creds = aggqsent_credrev.calc_claim_cred([claim['text'] for claim in claims_in_doc],
                                  cfg)
    logger.info("Found %d doc subclaim credibilities" % len(claim_creds))
    content_cred = aggregate_sub_creds(claim_creds, 'document', cfg)
    content_cred['timings'] = citimings.timing(
        'assess_doc_content_cred', start,
        [cc.get('timings', None) for cc in claim_creds])
    return content_cred

def select_claims_in_doc(adoc, cfg):
    """Select a list of claims in an analysed doc that merit further analysis

    :param adoc: an analysed document
    :param cfg: config options
    :returns: a list of sentences, presumed to be claims
    :rtype: list
    """
    claims_in_doc = list(tweetsents.gen_claims_from_analysed_doc(adoc, cfg))
    logger.info('Extracted %d claims from doc url' % len(claims_in_doc))
    max_claims_in_doc = int(cfg.get('max_claims_in_doc', 5))
    if len(claims_in_doc) > max_claims_in_doc:
        logger.info('Capping to %d claims from doc' % max_claims_in_doc)
        claims_in_doc = claims_in_doc[:max_claims_in_doc]
    return claims_in_doc

def aggregate_sentReviews(sentReviews, adoc, cfg):
    """Combines CredReviews for sentences in adoc into an ArticleCredReview

    Refactoring of `aggregate_sub_creds`

    :param sentReviews: list of sentence CredibilityReviews. In
      practice, we expect a list of `AggQSentCredReview`s.
    :param adoc: an analysed document. The item to be reviewed.
    :param cfg: config options. Currently for the `cred_conf_threshold`
    :returns: an `ArticleCredReview` aggregating the credibility
      reviews of sentences in the article.
    :rtype: dict
    """
    doc_mdref = markdown_ref_for_article(adoc, cfg)
    sub_bots = []  # extract sub_bot from sentReviews and make sure they match default sub_bots?
    author = default_bot_info(cfg)
    partial_ArticleCredRev = {
        **base_ArticleCredReview(cfg),
        'author': author,
        'itemReviewed': adoc,
        'isBasedOn': sentReviews}
    # simplest case
    if sentReviews is None or len(sentReviews) == 0:
        explanation = 'we could not find any relevant claims in it.'
        return {
            **partial_ArticleCredRev,
            'text': '%s is *not verifiable* as %s' % (doc_mdref, explanation),
            'reviewRating': {
                '@type': 'Rating',
                'reviewAspect': 'credibility',
                'ratingValue': 0.0,
                'confidence': 0.0,
                'ratingExplanation': explanation
            }}

    subRatings = [sr.get('reviewRating') for
                  sr in sentReviews
                  if sr.get('reviewRating') is not None]
    for sr in subRatings: # really, just validating
        assert 'ratingValue' in sr, '%s' % (sr)
        assert sr['ratingValue'] is not None, '%s' % (sr)
        assert 'confidence' in sr, '%s' % (sr)
        assert sr['confidence'] is not None, '%s' % (sr)

    # filter by confidence
    conf_threshold = float(cfg.get('cred_conf_threshold', 0.7))
    filter_fn = agg.filter_review_by_min_confidence(conf_threshold)
    conf_subRevs = [sr for sr in sentReviews if filter_fn(sr)]
    igno_subRevs = [sr for sr in sentReviews if not filter_fn(sr)]
    
    # not enough confidence in sentReviews
    if len(conf_subRevs) == 0:
        msg = 'we could not assess credibility of %d of its sentences with %s.%s' % (
            len(sentReviews),
            'sufficient confidence',
            ' An example: %s ' % igno_subRevs[0]['text'] if len(igno_subRevs) >0 else '')
        return {
            **partial_ArticleCredRev,
            'text': '%s is *not verifiable* as %s.' % (doc_mdref, msg),
            'reviewRating': {
                '@type': 'AggregateRating',
                'reviewAspect': 'credibility',
                'ratingValue': 0.0,
                'confidence': 0.0,
                'ratingExplanation': msg,
                'ratingCount': agg.total_ratingCount(subRatings),
                'reviewCount': agg.total_reviewCount(subRatings) + len(sentReviews)
            }}

    # select least credible above the confidence threshold
    subRevs_by_val = sorted(
        [sr for sr in conf_subRevs],
        key=lambda rev: dictu.get_in(rev, ['reviewRating', 'ratingValue'], 0.0))
    least_cred_rev = subRevs_by_val[0]
    msg = 'like its least credible Sentence `%s` which %s' % (
        dictu.get_in(least_cred_rev, ['itemReviewed', 'text'], '(missing sentence)'),
        dictu.get_in(least_cred_rev, ['reviewRating', 'ratingExplanation'],
                     '(missing explanation)'))
    revRating = {
        '@type': 'AggregateRating',
        'reviewAspect': 'credibility',
        'ratingValue': dictu.get_in(least_cred_rev, ['reviewRating', 'ratingValue'], 0.0),
        'confidence': dictu.get_in(least_cred_rev, ['reviewRating', 'confidence'], 0.0),
        'ratingExplanation': msg,
        'ratingCount': agg.total_ratingCount(subRatings),
        'reviewCount': agg.total_reviewCount(subRatings) + len(sentReviews)
    }
    return {
        **partial_ArticleCredRev,
        'isBasedOn': subRevs_by_val + igno_subRevs,
        'text': '%s is *%s* %s' % (
            doc_mdref, credlabel.rating_label(revRating, cfg), msg),
        'reviewRating': revRating
    }
    
    

def markdown_ref_for_article(adoc, cfg):
    return '%s "[%s](%s)"' % (
        adoc.get('@type', 'Article'),
        adoc.get('headline', adoc.get('title', 'Missing title')),
        adoc.get('url', ''))

    
def aggregate_sub_creds(sub_creds, scope_name, cfg):
    """Aggregates a list of credibility dicts into a single credibility
      dict. This is done by (i) filtering over a minimum confidence and 
    (ii) selecting the least credible sub credibility.

    *deprecated* you should be moving towards using
     `aggregate_subReviews` which uses the schema.org compliant
     Reviews and Ratings.

    :param sub_creds: a list of dicts. Should have field `credibility`
      with a `value` and `confidence`
    :param scope_name: string to denote the scope where the sub_creds
      were taken from, e.g. `document`
    :param cfg: config options. Currently for the
      `cred_conf_threshold`.
    :returns: the aggregate credibility dict
    :rtype: dict
    """
    # simplest case:
    if sub_creds is None or len(sub_creds) == 0:
        return {
            'credibility': 0.0,
            'confidence': 0.0,
            'credibility_label': 'not verifiable',
            'explanation': "No textual content found"
        }

    #  filter credibilities by confidence
    conf_threshold = float(cfg.get('cred_conf_threshold', 0.7))
    conf_subcreds = [
        sc for sc in sub_creds
        if dictu.get_in(sc, ['credibility', 'confidence'], 0.0) > conf_threshold]
    # not enough confidence in sub creds
    if len(conf_subcreds) == 0:
        sub_str = '%d sentences in %s' % (len(sub_creds), scope_name)
        msg = 'Could not assess credibility of %s with %s' % (
            sub_str, 'sufficient confidence')
        return {
            'credibility': 0.0,
            'confidence': 0.0,
            'credibility_label': 'not verifiable',
            'explanation': msg
        }

    #  select minimum credibility value (with sufficient confidence)
    sc_by_val = [sc for sc in conf_subcreds]
    sc_by_val = sorted(sc_by_val,
                       key=lambda sc: sc['credibility']['value'])
    minval_sc = sc_by_val[0]
    msc_cred = minval_sc['credibility']
    msg = 'Sentence in %s: %s' % (scope_name, msc_cred['explanation'])
    credval = msc_cred['value']
    return {
        'credibility': credval,
        'confidence': msc_cred['confidence'],
        'credibility_label': credlabel.describe_credval(credval, cred_dict=None),
        'explanation': msg
    }

def analyzed_doc(article, cfg):
    """Returns an analysed version for an input article

    :param article: an `Article` item, really anything with fields `url`,
      `content` and `id`. See `semantic_analyzer.analyzer.analyze_doc`.
    :param cfg: config options
    :returns: an analyzed doc. Crucially, it will contain a field `claims_content`.
      See `semantic_analyzer.analyzer.analyze_doc` for basic analysed doc.
      See `coinfoapy.solr2coinforesponse.calculate_claims_content` 
    :rtype: dict
    """
    start = citimings.start()
    ci_colls = cfg.get(
        'relsents_in_colls',
        ['generic', 'pilot-se', 'pilot-gr', 'pilot-at',
         'factcheckers', 'fc-dev'])
    preidx_doc = cisearch.find_preindexed_doc_by_url(
        article['url'], ci_colls)
    if preidx_doc is None:
        fetched = url_scraper.fetch_url(article['url'])
        resolved_url = fetched['resolved_url']
        if resolved_url != article['url']:
            preidx_doc = cisearch.find_preindexed_doc_by_url(
                resolved_url, ci_colls)
            # TODO: we may want to add the article['url'] as an alias
            #  for this, the DB schema needs to support this and we
            #  need to be able to submit new values for this list
            #  of url values. Define `same_as_ss` and update
            #  cisearch to query and update this.
    preidx_t = citimings.timing('retrieve_preindexed', start)
    if preidx_doc is not None:
        preidx_doc['timings'] = preidx_t
        return preidx_doc
    else:
        adoc = semalyzer.analyze_doc(article, {**cfg, 'expand_claims': True})
        if 'content' in adoc and adoc['content']:
            ci_coll = cfg.get('target_url_collect_coll',
                              cfg.get('default_url_collect_coll', None))
            if ci_coll is not None:
                ci_doc, aw_doc = cisearch.analyzed_doc_insert(adoc, ci_coll)
        analyze_subt = adoc.get('timings')
        adoc['timings'] = citimings.timing('analyzed_doc', start, [
            preidx_t, analyze_subt])
        return adoc
