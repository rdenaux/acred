#
# Copyright (c) 2020 Expert System Iberia
#
"""Credibility reviewer for Tweet
"""
import logging
from esiutils import citimings, bot_describer, dictu, isodate, hashu
from semantic_analyzer import tweetrelsents as tweetsents
from acred import content
from acred.rating import agg
from acred.reviewer.credibility import article_credrev, aggqsent_credrev
from acred.reviewer.credibility import label as credlabel

logger = logging.getLogger(__name__)

version = '0.1.0'
ci_context = 'http://coinform.eu'

content.register_acred_type('TweetCredReviewer', {
    'super_types': ['SoftwareApplication', 'Bot'],
    'ident_keys': ['@type', 'name', 'dateCreated', 'softwareVersion', 'isBasedOn', 'launchConfiguration'],
    'route_template': '/bot/{@type}/{softwareVersion}/{identifier}',
    'itemref_keys': ['isBasedOn']
})

content.register_acred_type('TweetCredReview', {
    'super_types': ['CredibilityReview', 'Review'],
    'ident_keys': ['@type', 'dateCreated', 'author', 'itemReviewed', 'reviewRating', 'isBasedOn'],
    'route_template': '/review/{identifier}',
    'itemref_keys': ['author', 'itemReviewed', 'reviewRating', 'isBasedOn']
})

def review(item, config):
    """Reviews the incoming item and returns a Review for it

    :param item: a single item or a list of items, in this case the 
      items must be a `Tweet` instances.
    :param config: a configuration map
    :returns: one or more Review objects for the input items
    :rtype: dict or list of dict
    """
    rev_format = config.get('acred_review_format', 'schema.org')
    if rev_format == 'cred_assessment':
        return assess_tweet_cred(item, config)
    else:
        return review_tweet(item, config)

def default_sub_bots(cfg):
    return [aggqsent_credrev.default_bot_info(cfg),
            article_credrev.default_bot_info(cfg)]

def bot_info(sub_bots, cfg):
    """Returns a description for this TweetCredReviewer

    :param sub_bots: a list of bot items used by this TweetCredReviewer
    :param cfg: config options
    :returns: a `TweetCredReviewer` item
    :rtype: dict
    """
    result = {
        '@context': ci_context,
        '@type': 'TweetCredReviewer',
        'additionalType': content.super_types('TweetCredReviewer'),
        'name': 'ESI Tweet Credibility Reviewer',
        'description': 'Reviews the credibility of a tweet by reviewing the sentences in the tweet and the (textual) documents linked by the tweet',
        'author': bot_describer.esiLab_organization(),
        'dateCreated': '2020-04-02T18:00:00Z',
        'applicationCategory': ['Disinformation Detection'],
        'softwareRequirements': ['python', 'nltk', 'Cogito'],
        'softwareVersion': version,
        'executionEnvironment': bot_describer.inspect_execution_env(),
        'isBasedOn': sub_bots,
        'launchConfiguration': {},
        'taskConfiguration': {}
    }
    return {
        **result,
        'identifier': hashu.hash_dict(dictu.select_keys(
            result, content.ident_keys(result)))}
    

def default_bot_info(cfg):
    return bot_info(default_sub_bots(cfg), cfg)

def review_tweet(tweet, cfg):
    """Reviews the credibility for a single tweet

    Refactoring of `assess_tweet_cred`

    :param tweet: a normalised tweet. Must have field `text` with
      textual content, and fields `urls` with shortened urls appearing
      in the original tweet content.
    :param cfg: config options
    :returns: a `TweetCredReview`
    :rtype: dict

    """
    rev_format = cfg.get('acred_review_format', 'schema.org')
    assert rev_format == 'schema.org', rev_format

    # generate (or retrieve) sub reviews
    sent_credReviews, subts = review_sents_in_tweet(tweet, cfg)
    doc_credReviews, doc_creds_t = review_linked_docs_in_tweet(tweet, cfg)

    return aggregate_subReviews(sent_credReviews + doc_credReviews, tweet, cfg)

    
def assess_tweet_cred(tweet, cfg):
    """Main credibility assessment for a single tweet

    *Deprecated* use `review_tweet` instead

    :param tweet: must have field `text` with the textual content,
      and field `urls` with shortened urls appearing in the original tweet
      content
    :returns: a credibility assessment for the tweet
    :rtype: dict
    """
    start = citimings.start()
    
    rev_format = cfg.get('acred_review_format', 'schema.org')
    assert rev_format == 'cred_assessment', rev_format

    # generate (or retrieve) sub reviews
    sents_in_tweet, subts = review_sents_in_tweet(tweet, cfg)
    doc_creds, doc_creds_t = review_linked_docs_in_tweet(tweet, cfg)
    
    start4 = citimings.start()
    tweet_cred = aggregate_tweet_cred(sents_in_tweet, doc_creds, cfg)
    result = {
        '@context': ci_context,
        '@type': 'TweetCredibilityAssessment',
        'tweet_id': int(tweet['tweet_id']),
        'sub_assessments': sents_in_tweet + doc_creds,
        'item_assessed': tweet,
        'sentences_in_tweet': sents_in_tweet,
        **tweet_cred
    }
    result = remove_tweet_assessment_details(result)
    agg_t = citimings.timing('aggregation_cleaning_time', start4)
    
    subts += [doc_creds_t, agg_t]
    result['timings'] = citimings.timing(
            'assess_tweet_cred', start, subts)
    return result


def extract_relevant_sentences(tweet, cfg):
    """Extracts all relevant sentences

    :param tweet:
    :param cfg: configuration map

    :returns: dict with keys `in_tweet` and `in_linked_doc` The first
    returns a list of sentences extracted from the tweet text proper,
    possibly cleaned. `in_linked_doc` has a list of sentences in
    documents linked by the tweet.

    :rtype: dict
    """
    start = citimings.start()
    sent_detector = tweetsents.build_sent_detector(cfg)
    sent_detector_t = citimings.timing("sent_detector", start)

    start2 = citimings.start()
    sents = sent_detector(tweet['text'])
    sent_detection_t = citimings.timing('sent_detection', start2)

    in_tweet = tweetsents.build_in_tweet_info(
        tweet['tweet_id'], sents, cfg)

    # TODO  1.4 if there are complex sentences, extract clauses
    return {
        'in_tweet': in_tweet,
        'timings': citimings.timing(
            'tweet_relevant_sentences', start,
            [sent_detector_t, sent_detection_t])
    }


def review_sents_in_tweet(tweet, cfg):
    """Extracts sentenes in `tweet` and reviews their credibilities

    :param tweet: a `Tweet` dict
    :param cfg: config options

    :returns: a tuple with a list of credibility reviews and a list of
      timings for the steps. The review format depends on
      `cfg['acred_review_format']`

    :rtype: tuple
    """
    relevant_sentences = extract_relevant_sentences(tweet, cfg)
    relevant_sentences_t = relevant_sentences.get('timings', None)

    start2 = citimings.start()
    intws = relevant_sentences['in_tweet']
    logger.info("Found %d relevant sentences in tweet" % len(intws))
    review_format = cfg.get('acred_review_format', 'schema.org')
    if review_format == 'cred_assessment':
        sent_reviews = aggqsent_credrev.calc_claim_cred([itw['text'] for itw in intws], cfg)
    else:
        sent_reviews = aggqsent_credrev.review(
            [content.as_sentence(itw['text'], appearance=[tweet], cfg=cfg)
             for itw in intws], cfg)
    sents_in_tweet_t = citimings.timing('sents_in_tweet', start2)
    return sent_reviews, [relevant_sentences_t, sents_in_tweet_t]


def review_linked_docs_in_tweet(tweet, cfg):
    """Review the credibility of any docs linked in the tweet

    :param tweet: a `Tweet` dict. We expect it to have a field `urls`
      with a list of URL objects
    :param cfg: 
    :returns: a tuple with (i) a list of credibility reviews for the
      webpages linked in tweet and (ii) a timing object for this method
    :rtype: tuple
    """
    start3 = citimings.start()
    # Retrieve or request doc credibilities
    doc_urls = [url['short_url'] for url in tweet['urls']]
    doc_urls = list(set(doc_urls))  # dedupe
    # TODO retrieve existing credibility from DB or
    # calculate from scratch
    docs = [{'@context': 'http://schema.org',
             '@type': 'Webpage',
             'url': url,
             'mentioned_in': tweet}
            for url in doc_urls]
    doc_creds = [article_credrev.review(doc, cfg)
                 for doc in docs]
    doc_creds_t = citimings.timing(
        'sub_doc_cred', start3,
        [dc['timings'] for dc in doc_creds
         if 'timings' in dc])
    return doc_creds, doc_creds_t


def aggregate_subReviews(subReviews, tweet, cfg):
    """Creates an aggregate review based on subReviews for tweet

    Refactoring of `aggregate_tweet_cred`

    :param subReviews: list of credibility reviews for (parts of) the
      tweet to review.
    :param cfg: config options
    :returns: a credibility review for the `tweet` to review that
      contains an `AggregateRating` based on the `subReviews`
    :rtype: dict
    """
    # extract sub_bots and compare to default_sub_bots
    partial_TweetCredReview = {
        '@context': ci_context,
        '@type': 'TweetCredReview',
        'itemReviewed': tweet,
        'isBasedOn': subReviews,
        'dateCreated': isodate.now_utc_timestamp(),
        'author': default_bot_info(cfg)
    }
    tweet_mdref = markdown_ref_for_tweet(tweet, cfg)
    if subReviews is None:
        subReviews = []

    subRatings = [sr.get('reviewRating') for sr in subReviews
                  if sr.get('reviewRating') is not None]
    
    # filter by min confidence
    conf_threshold = float(cfg.get('cred_conf_threshold', 0.7))
    filter_fn = agg.filter_review_by_min_confidence(conf_threshold)
    conf_subRevs = [sr for sr in subReviews if     filter_fn(sr)]
    igno_subRevs = [sr for sr in subReviews if not filter_fn(sr)]

    # no (confident) subReviews
    if len(conf_subRevs) == 0:
        part_rating = {
            '@type': 'Rating',
            'ratingValue': 0.0,
            'confidence': 0.0,
            'reviewAspect': 'credibility'}
        if len(subReviews) == 0:
            msg = "we could not extract (or assess credibility of) its sentences or linked documents" % (
                tweet_mdref)
            rating = {
                **part_rating,
                'ratingExplanation': msg}
        else:
            msg = 'we could not assess the credibility of its %d sentences or linked documents.%s' % (
                len(subReviews),
                '\nFor example:\n * %s' % (igno_subRevs[0]['text']))
            rating = {
                **part_rating,
                '@type': 'AggregateRating',
                'ratingExplanation': msg,
                'ratingCount': agg.total_ratingCount(subRatings),
                'reviewCount': agg.total_reviewCount(subRatings) + len(subReviews)
            }
        return {
            **partial_TweetCredReview,
            'text': '%s seems *%s* as %s' % (
                tweet_mdref, credlabel.rating_label(rating, cfg), msg),
            'reviewRating': rating}

    # select least credible subReview
    subRevs_by_val = sorted(
        [sr for sr in conf_subRevs],
        key=lambda rev: dictu.get_in(rev, ['reviewRating', 'ratingValue'], 0.0))
    least_cred_rev = subRevs_by_val[0]
    msg = 'based on its least credible part:\n%s' % (
        dictu.get_in(least_cred_rev, ['text'],
                     '(missing explanation for part)'))
    revRating = {
        '@type': 'AggregateRating',
        'reviewAspect': 'credibility',
        'ratingValue': dictu.get_in(least_cred_rev, ['reviewRating', 'ratingValue'], 0.0),
        'confidence': dictu.get_in(least_cred_rev, ['reviewRating', 'confidence'], 0.0),
        'ratingExplanation': msg,
        'ratingCount': agg.total_ratingCount(subRatings),
        'reviewCount': agg.total_reviewCount(subRatings) + len(subReviews)
    }
    return {
        **partial_TweetCredReview,
        'isBasedOn': subRevs_by_val + igno_subRevs, # just a re-ordering
        'text': '%s seems *%s* %s' % (
            tweet_mdref, credlabel.rating_label(revRating, cfg), msg),
        'reviewRating': revRating}


def markdown_ref_for_tweet(tweet, cfg):
    return '[%s](%s)' % (
        'the tweet',
        tweet.get('url', '(tweet url missing)'))

def aggregate_tweet_cred(sents_in_tweet, doc_creds, cfg):
    """Combines credibilities for sentences and docs linked in a tweet

    *Deprecated* use aggregate_subReviews to use the refactored
     strategy, which works at the level of CredibilityReviews.

    :param sents_in_tweet: list of `SimilarSent`s
    :param doc_creds: list of doc credibility dicts
    :param cfg: config options

    :returns: an aggregate credibility dict. In general the
      aggregation strategy is to select the least credible sub rating
      above a minimum confidence threshold. In practice the
      explanation may be combined of various subratings.
    :rtype: dict

    """
    # simplest case:
    if len(sents_in_tweet) + len(doc_creds) == 0:
        return {
            'credibility': 0.0,
            'confidence': 0.0,
            'credibility_label': 'not verifiable',
            'explanation': "No textual content found"
        }

    #  filter credibilities by confidence
    conf_threshold = float(cfg.get('cred_conf_threshold', 0.7))
    conf_sents_in_tweet = [
        sit for sit in sents_in_tweet
        if sit['credibility']['confidence'] > conf_threshold]
    conf_doc_creds = [
        dc for dc in doc_creds
        if dc['confidence'] > conf_threshold]
    # not enough confidence in extracted sents
    if len(conf_sents_in_tweet) + len(conf_doc_creds) == 0:
        sit_str = '%d sentences in the tweet' % len(sents_in_tweet)
        ld_str = '%d linked documents' % len(doc_creds)
        msg = 'Could not assess credibility of %s and %s with %s' % (
            sit_str, ld_str, 'sufficient confidence')
        return {
            'credibility': 0.0,
            'confidence': 0.0,
            'credibility_label': 'not verifiable',
            'explanation': msg
        }

    #  select minimum credibility value in_tweet
    sit_by_val = [sit for sit in conf_sents_in_tweet]
    sit_by_val = sorted(sit_by_val,
                        key=lambda sit: sit['credibility']['value'])
    minval_sit = sit_by_val[0] if len(conf_sents_in_tweet) > 0 else None
    if minval_sit is None:
        sit_cred = {
            'credibility': 0.0,
            'confidence': 0.0,
            'credibility_label': 'not verifiable',
            'explanation':
            'No textual content or unverifiable text in tweet'
        }
    else:
        msit_cred = minval_sit['credibility']
        msg = 'Sentence in tweet: %s' % (msit_cred['explanation'])
        credval = msit_cred['value']
        sit_cred = {
            'credibility': credval,
            'confidence': msit_cred['confidence'],
            'credibility_label': credlabel.describe_credval(credval, cred_dict=None),
            'explanation': msg
        }

    #  select minimum credibility value in linked docs
    ld_by_val = [ld for ld in conf_doc_creds]
    ld_by_val = sorted(ld_by_val, key=lambda ld: ld['credibility'])
    minval_ld = ld_by_val[0] if len(conf_doc_creds) > 0 else None
    if minval_ld is None:
        ld_cred = {
            'credibility': 0.0,
            'confidence': 0.0,
            'credibility_label': 'not verifiable',
            'explanation':
            'No textual content or could not assess credibility of %s' % (
                'linked document(s)')
        }
    else:
        credval = minval_ld['credibility']
        msg = 'Linked document: %s' % (minval_ld['explanation'])
        ld_cred = {
            'credibility': credval,
            'confidence': minval_ld['confidence'],
            'credibility_label': credlabel.describe_credval(credval, cred_dict=None),
            'explanation': msg
        }

    if minval_sit is None:
        return ld_cred
    if minval_ld is None:
        return sit_cred
    if ld_cred['credibility'] < sit_cred['credibility']:
        ld_cred['explanation'] = '%s\nAlso/However, %s' % (
            ld_cred['explanation'], sit_cred['explanation'])
        return ld_cred
    else:
        sit_cred['explanation'] = '%s\nAlso/However, %s' % (
            sit_cred['explanation'], ld_cred['explanation'])
        return sit_cred


def remove_tweet_assessment_details(tweetcred):
    for sit in tweetcred.get('sentences_in_tweet', []):
        for relclaimtype, relclaims in sit.get('related_claims', {}).items():
            for relclaim in relclaims:
                if 'domain_credibility' in relclaim:
                    domcred = relclaim.get('domain_credibility', {})
                    domcred.pop('assessments', None)
    for sit in tweetcred.get('sentences_linked', []):
        for relclaimtype, relclaims in sit.get('related_claims', {}).items():
            for relclaim in relclaims:
                if 'domain_credibility' in relclaim:
                    domcred = relclaim.get('domain_credibility', {})
                    domcred.pop('assessments', None)
    return tweetcred    
