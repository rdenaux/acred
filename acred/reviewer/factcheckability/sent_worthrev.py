#
# Copyright (c) 2020 Expert System Iberia
#
"""Check-worthiness reviewer for a sentence (or a list of sentences) based on a trained model
"""
import logging
from esiutils import citimings, hashu, dictu, isodate
from acred import content
import requests

logger = logging.getLogger(__name__)
ci_context = 'http://coinform.eu'


content.register_acred_type('SentCheckWorthinessReviewer', {
    'super_types': ['SoftwareApplication', 'Bot'],
    'ident_keys': ['@type', 'name', 'dateCreated', 'softwareVersion',
                   'isBasedOn', 'launchConfiguration'],
    'route_template': '/bot/{@type}/{softwareVersion}/{identifier}',
    'itemref_keys': ['isBasedOn']
})

content.register_acred_type('SentCheckWorthinessReview', {
    'super_types': ['CheckWorthinessReview', 'Review'],
    'ident_keys': ['@type', 'dateCreated', 'author', 'itemReviewed', 'reviewRating'],
    'route_template': '/review/{identifier}',
    'itemref_keys': ['author', 'itemReviewed', 'reviewRating']
})

sentWorthReview_schema = {
    'super_types': ['CheckWorthinessReview', 'Review'],
    'ident_keys': ['@type', 'dateCreated', 'author', 'itemReviewed', 'reviewRating'],
    'route_template': '/review/{identifier}',
    'itemref_keys': ['author', 'itemReviewed', 'reviewRating']
}


def review(item, config):
    """Reviews the incoming item and returns a Review for it

    :param item: a single item or a list of items, in this case the
      items must be `Sentence` instances.
    :param config: a configuration map
    :returns: one or more Review objects for the input items
    :rtype: dict or list of dict
    """
    preds = predict_sentworthiness(item, config)
    return [worthinesspreds_as_SentCheckWorthinessReview(pred, config) for pred in preds]


def checkWorthinessReviewer(config):
    worthinesschecker_url = config['worthinesschecker_url']
    url = worthinesschecker_url + "/worthiness_predictor"
    resp = requests.get(url, verify=False)
    logger.info("Response from %s %s" % (url, resp))
    return resp.json()


def predict_sentworthiness(items, config):
    worthinesschecker_url = config['worthinesschecker_url']
    url = worthinesschecker_url + "/predict_worthiness"
    req = {'sentences': [it['text'] for it in items]}
    resp = requests.post(url, json=req, verify=False)
    logger.info("Response from %s %s" % (url, resp))
    resp.raise_for_status()
    jresp = resp.json()
    predictions = map_predictions(jresp.get('worthiness_checked_sentences'))
    return predictions


def map_predictions(preds):
    labels = preds.get('predicted_labels')
    confs = preds.get('prediction_confidences')
    sent_ids = preds.get('sentence_ids')
    sents = preds.get('sentences')

    mapped_preds = []
    for lab, conf, id, sent in zip(labels, confs, sent_ids, sents):
        mapped_preds.append({
            "ratingValue": worth_val(lab),
            "confidence": conf,
            "sentence": sent,
            "id": id
        })
    return mapped_preds


def worth_val(label):
    if label == 'CFS':
        return "worthy"
    else:
        return "unworthy"


def worthinesspreds_as_SentCheckWorthinessReview(mapped_pred, config):
    result = {
        "@context": ci_context,
        "@type": "SentCheckWorthinessReview",
        "additionalType": content.super_types('SentCheckWorthinessReview'),
        'reviewAspect': 'checkworthiness',
        'itemReviewed': content.as_sentence(mapped_pred['sentence']),
        'reviewRating': {
            '@type': 'Rating',
            'reviewAspect': 'checkworthiness',
            'ratingValue': mapped_pred['ratingValue'],
            'confidence': mapped_pred['confidence'],
            'ratingExplanation': rating_exp(mapped_pred['ratingValue'], mapped_pred['sentence'])
        },
        'dateCreated': isodate.now_utc_timestamp(),
        "author": checkWorthinessReviewer(config)
    }
    result['identifier'] = calc_worth_review_id(result)
    return result


def calc_worth_review_id(worth_review):
    """Calculates a unique id code for a worth review

    :param worth_review: a `SentWorthReview` dict
    :returns: a hashcode that tries to capture the identity of the worth review
    :rtype: str
    """
    return hashu.hash_dict(dictu.select_keys(
        worth_review, sentWorthReview_schema['ident_keys']
    ))


def rating_exp(rating_value, sent):
    if rating_value == 'worthy':
        exp = "Sentence **%s** seems like a factual sentence worth checking." % (sent)
    else:
        exp = "Sentence **%s** seems like it's not a factual statement; and if it is, it doesn't seem worth checking." %(sent)
    return exp
