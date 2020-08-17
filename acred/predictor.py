#
# Copyright (c) 2019 Expert System Iberia
#
"""Provides functionality to predict the credibility of content based
on a database of claims/sentences.

Currently the supported content types are Tweets, Articles and WebPages.

"""
import logging
import random
from esiutils import isodate
from esiutils import citimings, bot_describer, dictu, hashu
import re
from acred import tweetstoreclient
from acred.reviewer.credibility import tweet_credrev
from acred.reviewer.credibility import article_credrev, website_credrev, aggqsent_credrev
from acred import content, itnorm
from urllib.parse import urlparse


logger = logging.getLogger(__name__)


version = '0.1.0'
ci_context = "http://coinform.eu"

content.register_acred_type('CredReviewer', {
    'super_types': ['Bot', 'SoftwareApplication'],
    'ident_keys': ['@type', 'name', 'dateCreated', 'softwareVersion', 'isBasedOn', 'launchConfiguration'],
    'route_template': '/bot/{@type}/{softwareVersion}/{identifier}',
    'itemref_keys': ['isBasedOn']
})

content.register_acred_type('DocumentCredReview', {
    'super_types': ['CreativeWork', 'Review'],
    'ident_keys': ['@type', 'reviewAspect', 'itemReviewed', 'dateCreated', 'author', 'reviewRating'],
    'route_template': '/review/{identifier}',
    'itemref_keys': ['itemReviewed', 'author', 'reviewRating']
})

def bot_info(sub_bots, cfg):
    result = {
        '@context': ci_context,
        '@type': 'CredReviewer',
        'additionalType': content.super_types('CredReviewer'),
        'name': 'ESI Top-level Credibility Reviewer',
        'description': 'Reviews the credibility of various supported content items, mainly by delegating to the appropriate content-level reviewer',
        'author': bot_describer.esiLab_organization(),
        'dateCreated': '2020-04-02T18:05:00Z',
        'applicationCategory': ['Disinformation Detection'],
        'softwareRequirements': ['python'],
        'softwareVersion': version,
        'executionEnvironment': bot_describer.inspect_execution_env(),
        'isBasedOn': sub_bots,
        'launchConfiguration': {},
        'taskConfiguration': {}
    }
    return {
        **result,
        'identifier': hashu.hash_dict(dictu.select_keys(
            result,
            content.itemref_keys(result)
        ))}

def ensure_content(docs):
    """Ensure the docs have a `content` field

    :param docs: list of valid docs or a single doc. See
      content.validate_docs.
    :returns: a list of docs with either already provided `content` or
      a content value resolved by this function
    :rtype: list or dict

    """
    if type(docs) == list:
        return [ensure_content(d) for d in docs]
    doc = docs
    if 'content' in doc:
        return doc
    if content.is_tweet_doc(doc):
        # we got a doc without `content`, but with at least `tweet_id`
        # we need to retrieve the twitter information somehow...
        # option 1: use co-inform tweet-store api to retrieve cached tweet info
        fromstore = tweetstoreclient.tweet(doc['tweet_id'])
        if fromstore is not None:
            return {**doc, **fromstore}
        else:
            # option 2: use Twitter API
            raise NotImplemented(
                "Not retrieving content from Twitter API yet, value required.")
    elif content.is_article_doc(doc):
        # articles do not require content as long as a url is provided
        # as we can fetch the content
        # TODO: alternatively fetch the content here?
        return doc
    else:
        raise ValueError('Documents must provide a content field %s' % (
            list(doc.keys())))


# 'http[s]?://(?:[a-zA-Z]|[0-9]|[$-_@.&+]|[!*\(\), ]|(?:%[0-9a-fA-F][0-9a-fA-F]))+'
url_re = '%s://(?:%s|%s|%s|%s|%s)+' % (
            'http[s]?',  # scheme
            '[a-zA-Z]',  # alpha chars
            '[0-9]',  # nums
            '[$-_@.&+]',  # url special chars
            '[!*\(\), ]',  # more special chars? separators
            '(?:%[0-9a-fA-F][0-9a-fA-F])'  # hex encoded chars
        )


def find_url(string):
    if type(string) == str:
        return re.findall(url_re, string)
    else:
        logger.warning('No string content? %s' % (type(string)))
        return []


def ensure_urls(docs):
    if type(docs) == list:
        return [ensure_urls(d) for d in docs]
    doc = docs  # otherwise a single doc
    if content.is_tweet_doc(doc):
        # only tweets require a list of urls
        if 'urls' in doc and type(doc['urls']) == list:
            return doc
        # tweet dict is missing 'urls' field... add it from text
        urls = find_url(doc['content'])
        doc['urls'] = [{'short_url': url.strip()} for url in urls]
        print('Found urls %s in tweet content %s' % (urls, doc['content']))
        return doc
    elif content.is_article_doc(doc):
        if 'url' in doc:
            url = doc['url']
            if type(url) is not str:
                raise ValueError('Expecting a url, but found %s' % (type(url)))
            parsed_url = urlparse(url)
            if not parsed_url.scheme:
                # missing scheme, assuming http
                doc['url'] = 'http://%s' % url
                return doc
            else:
                return doc
        else:
            raise ValueError('Articles and Webpages must specify a url %s' % (doc))
    else:
        # other doc types don't require a list of urls
        return doc


def ensure_text_no_urls(docs):
    if type(docs) == list:
        return [ensure_text_no_urls(d) for d in docs]
    doc = docs  # else single doc case
    if content.is_tweet_doc(doc):
        # we only need to strip urls from text for tweets
        tweet = doc
        assert 'urls' in tweet and type(tweet['urls']) == list
        text_no_url = tweet['content']
        logger.debug("Found urls " + str(tweet['urls']))
        for url in tweet['urls']:
            text_no_url = text_no_url.replace(url['short_url'], " ")
        logger.debug("Text without urls: %s" % text_no_url)
        tweet['text'] = text_no_url
        return tweet
    else:
        return doc


def dummyPrediction(tweet):
    start = citimings.start()
    return {
        '@context': ci_context,
        '@type': 'TweetCredibilityAssessment',
        'tweet_id': int(tweet['tweet_id']),
        'item_assessed': tweet,
        'credibility': random.random(),
        'confidence': 0.0,
        'explanation': 'Dummy prediction, no actual analysis performed.',
        'sub_assessments': [],
        'date_assessed': isodate.now_utc_timestamp(),
        'assessor': {'@context': ci_context,
                     'name': 'dummyCredibilityPredictor'},
        'timings': citimings.timing('dummyPrediction', start)
        # deprecated, now as sub_assessments
        # 'sentences_in_tweets': [],
        # 'sentences_linked': []
    }


def normalise_docs(docs, cfg):
    """Produce uniform doc datastructures for valid docs

    The goal is to make sure we have all doc information is uniform
    so that we process them.

    For tweets, this may involve retrieving the full
    tweets from Twitter API, twitter-scraper or the co-inform tweet
    store. For tweet credibility assessment we need tweets to have the
    fields:
      `text` (the raw text, excluding any urls).
      `urls` a list of dicts with at least field `short_url`
    """
    docs = ensure_content(docs)
    docs = ensure_urls(docs)
#    tweets = ensure_resolved_urls(tweets) # resolve when linking
    docs = ensure_text_no_urls(docs)
    return docs


supported_doc_types = ['tweet', 'article']


def assess_doc_cred(doc, cfg):
    """Main credibility assessment for a single doc

    :param doc: a validated and normalised document, ready for credibility
      assessment
    :param cfg: any configs we need to execute/customise the assessment
    :returns: a credibility assessment for the doc
    :rtype: dict
    """
    start = citimings.start()
    if content.is_tweet_doc(doc):
        result = tweet_credrev.review(doc, cfg)
        return result
    elif content.is_article_doc(doc):
        result = article_credrev.review(doc, cfg)
        return result
    else:
        rev_format = cfg.get('acred_review_format', 'schema.org')
        msg = 'Unsupported document (not a %s))' % supported_doc_types
        if rev_format == 'cred_assessment':
            return {
                '@context': ci_context,
                '@type': 'DocumentCredibilityAssessment',
                'doc_url': doc['url'],
                'item_assessed': doc,
                'cred_assessment_error': msg,
                'date_assessed': isodate.now_utc_timestamp(),
                'timings': citimings.timing('assess_doc_cred', start),
                'credibility': 0,
                'confidence': 0,
                'explanation': msg}
        else:
            rating = {
                '@type': 'Rating',
                'ratingValue': 0.0,
                'confidence': 0.0,
                'ratingExplanation': msg}
            result = {
                '@context': ci_context,
                '@type': 'DocumentCredReview',
                'reviewAspect': 'credibility',
                'itemReviewed': doc,
                'dateCreated': isodate.now_utc_timestamp(),
                'author': bot_info([], cfg),
                'reviewRating': {
                    **rating,
                    'identifier': itnorm.calc_identifier(rating, cfg)}
            }
            return {
                **result,
                'identifier': itnorm.calc_identifier(result, cfg)
            }


def predict_credibility(docs, cfg):
    """Predict the credibility of a list of tweets

    :param docs: list of dicts each must be valid documents and have properties
      `@context`, `@type`.
      Tweets must have properties `tweet_id` and `content`.
      Articles must have property `url`.
    :param cfg: dict with needed configuration options needed to perform the
      credibility assessment, keys include:
      - `acred_factchecker_urls`: list of domains of known fact-checkers
      - `acred_search_url`: url of the claim search service
      - `acred_search_auth_user`: username to access claim search
      - `acred_search_auth_pwrd`: password to access claim search
      - `acred_search_verify`: bool verify SSL certs of claim search?
      - key/values needed by the `tweetrelsents` module
    :returns: assessments for each input tweet
    :rtype: list
    """
    content.validate_docs(docs)
    docs = normalise_docs(docs, cfg)
    logger.info("Docs validated and normalised. Ready for credib assessment")
    try:
        return [assess_doc_cred(d, cfg) for d in docs]
    except Exception as e:
        logger.error(e, exc_info=True)
        raise e

def validate_docs(docs):
    return content.validate_docs(docs)

def calc_website_cred(urls, cfg):
    return website_credrev.review(urls, cfg)

def calc_claim_cred(claims, cfg):
    assert type(claims) == list, type(claims)
    for s in claims:
        assert type(s) == str, s
    rev_format = cfg.get('acred_review_format', 'schema.org')
    if rev_format == 'acred_assessment':  # pre-refactoring
        return aggqsent_credrev.calc_claim_cred(claims, cfg)
    assert rev_format == 'schema.org'
    sents = [content.as_sentence(s) for s in claims]
    return aggqsent_credrev.review(sents, cfg)
        

def format_graph(reviews, cfg):
    if type(reviews) is list and len(reviews) == 0:
        return reviews
    
    revFormat = cfg.get('acred_review_format', 'schema.org')
    if revFormat == 'cred_assessment':
        # nothing to do when using deprecated format
        return reviews
    if revFormat != 'schema.org':
        logger.error('Unexpected reviewFormat %s' % revFormat)
        return reviews
    gFormat = cfg.get('graphFormat', cfg.get('acred_graph_format', 'nestedTree'))
    valid_graphFormats = ['nestedTree', 'nodesWithRefs', 'nodesAndLinks']
    if gFormat not in valid_graphFormats:
        logger.error('Unexpected graphFormat %s. Should be one of %s' %  (
            gFormat, valid_graphFormats))
        gFormat = 'nestedTree'
    basedOn_depth = cfg.get('basedOn_depth', 1) if gFormat == 'nestedTree' else None
    return reformat_schema_graph(reviews, gFormat, basedOn_depth, cfg)

def reformat_schema_graph(reviews, gFormat, basedOn_depth, cfg):
    if type(reviews) is list:
        return [reformat_schema_graph(r, gFormat, basedOn_depth, cfg) for r in reviews]
    assert type(reviews) is dict, '%s' % (type(reviews))
    # assume review is a nested item
    if gFormat == 'nestedTree' and basedOn_depth:
        return itnorm.trim_tree(reviews, 'isBasedOn', basedOn_depth)
    elif gFormat == 'nestedTree':
        return reviews
    elif gFormat == 'nodesWithRefs':
        return itnorm.normalised_nested_item(reviews, cfg)
    elif gFormat == 'nodesAndLinks':
        return itnorm.nested_item_as_graph(reviews, {'composite_rels': ['reviewRating'],
                                                     'ensureUrls': True,
                                                     **cfg})
    else:
        raise ValueError('Unexpected gFormat %s' % (gFormat))

    

    
    
