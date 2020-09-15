#
# Copyright (c) 2019 Expert System Iberia
#
"""
API Views for serving user requests with examples
"""
import logging
import subprocess
from flask import jsonify, request
import werkzeug
from werkzeug.datastructures import MultiDict
from acredapi import app, config, claim
from esiutils import citimings, dictu
from acredapi.InvalidUsage import InvalidUsage
from acredapi.ServerError import ServerError
from acred import predictor as credpred
from acred import itnorm
import time
import requests
from semantic_analyzer import analyzer


# Setup
logger = logging.getLogger(__name__)
app_name = config['acredapi']['app_name']


# http://localhost:5000/test unauthenticated response of "Hello World"
@app.route('/test')
def app_test():
    """ Test Method, no authentication required """
    logger.info("Hello World Requested")
    response = {"message": "Hello World!", "status": "200"}
    return jsonify(response)


# System Uptime
@app.route('/' + app_name + '/api/v1/uptime')
def app_uptime():
    """ Runs a system command to get the uptime"""
    p = subprocess.Popen('uptime', stdout=subprocess.PIPE,
                         universal_newlines=True)
    uptime = p.stdout.readlines()[0].strip()
    response = {"message": uptime, "status": "200"}
    return jsonify(response)


@app.route('/')
def app_index():
    """Index identifying the server"""
    response = {
        "message": "acred API" +
        " Use one of the documented endpoints.",
        "status": "200"}
    return jsonify(response)



def parse_bool(strval):
    if strval is None:
        return None
    val = strval.strip().lower()
    if val == 'false':
        return False
    if val == 'true':
        return True
    raise ValueError("Not a boolean str: " + strval)


@app.route('/' + app_name + '/api/v1/claim/search', methods=['GET'])
def claim_search():
    try:
        q_claims = request.args.getlist('claim', None)
        if q_claims is None or len(q_claims) == 0:
            raise InvalidUsage("claim parameter is mandatory")
        logger.info('Searching for claims matching "%s"' % q_claims)
        return jsonify(claim.search_claim(q_claims))
    except InvalidUsage as e:
        raise e
    except Exception as e:
        logger.exception(e)
        raise ServerError('Internal server error: ' + str(e), status_code=500)


@app.route('/' + app_name + '/api/v1/claim/internal-search',
           methods=['POST'])
def internal_claim_search():
    try:
        req_json = request.get_json()
        q_claims = req_json.get('claims', None)
        if q_claims is None:
            logger.info('No claims provided, assuming this is just to get information about the bots')
            return jsonify(claim.search_claim_bots())
        # else
        logger.info('Searching for claims related to %d sents: "%s"' % (
            len(q_claims), q_claims))
        return jsonify(claim.search_claim(q_claims))
    except InvalidUsage as e:
        raise e
    except Exception as e:
        logger.exception(e)
        raise ServerError('Internal server error: ' + str(e), status_code=500)

@app.route('/' + app_name + '/api/v1/acred/reviewer/credibility/claim',
           methods=['GET'])
@app.route('/' + app_name + '/api/v1/claim/predict/credibility',
           methods=['GET'])
def claim_predict_credibility():
    try:
        claims = request.args.getlist('claim', None)
        logger.info('predicting credibility of "%s"' % claims)
        cfg = acred_config()
        rev_format = request.args.get('reviewFormat', cfg.get('acred_review_format', 'cred_assessment'))
        rev_checkworthiness = bool(request.args.get('reviewCheckWorthiness', cfg.get('worthiness_review', True)))
        valid_formats = ['schema.org', 'cred_assessment']

        graph_format = request.args.get('graphFormat', cfg.get('acred_graph_format', 'nestedTree'))
        valid_graphFormats = ['nestedTree', 'nodesWithRefs', 'nodesAndLinks']
        if rev_format not in valid_formats:
            raise InvalidUsage('reviewFormat should be either %s, but was %s' % (
                valid_formats, rev_format))
        if rev_format == 'schema.org' and graph_format not in valid_graphFormats:
            raise InvalidUsage('graphFormat should be one of %s, but was %s' % (
                valid_grraphFormats, graph_format))
        cfg = {**cfg,
               'acred_review_format': rev_format,
               'graphFormat': graph_format,
               'worthiness_review': rev_checkworthiness}
        return jsonify(credpred.calc_claim_cred(claims, cfg))
    except InvalidUsage as e:
        raise e
    except Exception as e:
        logger.exception(e)
        raise ServerError('Internal server error: ' + str(e), status_code=500)


@app.route('/' + app_name + '/api/v1/acred/reviewer/credibility/website',
           methods=['GET'])
def acred_website_credibility():
    try:
        urls = request.args.getlist('url', None)
        logger.info('predicting credibility of website "%s"' % urls)
        return jsonify(credpred.calc_website_cred(urls, acred_config()))
    except InvalidUsage as e:
        raise e
    except Exception as e:
        logger.exception(e)
        raise ServerError('Internal server error: ' + str(e), status_code=500)


@app.route('/' + app_name + '/api/v1/acred/reviewer/credibility/webpage',
           methods=['GET', 'POST'])
def acred_webpage_credibility():
    try:
        req_json = request.get_json() or {}
        ci_args = merge_mdict_params(request.args, req_json)
        webpages = ci_args.getlist('webpages')
        urls = ci_args.getlist('url', None)
        webpages = webpages + [{
            '@context': 'http://schema.org',
            '@type': 'Webpage',
            'url': url} for url in urls]
        logger.info('predicting credibility of webpages "%s"' % webpages)
        cfg = {
            **acred_config(),
            'acred_review_format': 'schema.org',
            **ci_args.get('config', {}),
            **request.args}
        preds = credpred.predict_credibility(webpages, cfg)
        f_preds = credpred.format_graph(preds, cfg)
        return jsonify(f_preds)
    except InvalidUsage as e:
        raise e
    except Exception as e:
        logger.exception(e)
        raise ServerError('Internal server error: ' + str(e), status_code=500)


def merge_mdict_params(a, b):
    result = MultiDict({})
    if a is not None:
        result.update(a)
    if b is not None:
        result.update(b)
    return result


def read_lines(path):
    with open(path, encoding='utf-8') as f:
        lines = f.readlines()
    return [line.strip() for line in lines]


def acred_config():
    sect = config['acred']
    return {
        'acred_factchecker_urls': read_lines(
            sect['acred_factchecker_urls_path']),
        'acred_pred_claim_search_url': sect['acred_pred_claim_search_url'],
        'acred_search_auth_user': sect['acred_search_auth_user'],
        'acred_search_auth_pwrd': sect['acred_search_auth_pwrd'],
        'acred_search_verify': bool(sect.get(
            'acred_search_verify', True)),
        'acred_review_format': sect.get('review_format', 'cred_assessment'),
        'cred_conf_threshold': float(sect.get('cred_conf_threshold', 0.7)),
        'article_from_website_conf_factor': sect.get('article_from_website_conf_factor', 0.9),
        'article_from_website_cred_threshold_penalise': sect.get(
            'article_from_website_cred_threshold_penalise', 0.2),        
        'sentence_extractor': sect['sentence_extractor'],
        'sentence_type': sect['sentence_type'],
        'sensi_dir': sect.get('sensi_dir', None),
        'translation_service_url': sect.get('translation_service_url', None),
        'translation_service_key': sect.get('translation_service_key', None),
        'relsents_in_colls': [
            it.strip() for it in sect['relsents_in_colls'].split(',')],
        'relsents_search_auth_user': sect['relsents_search_auth_user'],
        'relsents_search_auth_pwrd': sect['relsents_search_auth_pwrd'],
        'relsents_search_url': sect['relsents_search_url'],
        'relsents_search_verify': bool(sect['relsents_search_verify']),
        'sentence_similarity_unrelated_factor': float(sect.get('sentence_similarity_unrelated_factor', 0.8)),
        'sentence_similarity_discuss_factor': float(sect.get('sentence_similarity_discuss_factor', 0.9)),
        'worthiness_review': bool(sect['worthiness_review']),
        'worthinesschecker_url': sect.get('worthinesschecker_url', None)
    }


def backward_compatible_tweetcred_predictions(preds):
    """Ensure that each prediction contains fields needed for backward compatibility

    These are fields which are used by the co-inform rule-engine:
    `tweet_id`, `credibility`, `confidence` and `explanation`. These
    should already be there if the requested acred reviewFormat was
    `cred_assessment`, but should be missing if the it was
    `schema.org` (the new, recommended output).

    :param preds: a list of (or an individual) prediction dicts
    :returns: the same list of predictions but with any missing fields
    for backward compatibility
    :rtype: list or dict
    """
    if type(preds) is list:
        return  [backward_compatible_tweetcred_predictions(pred) for pred in preds]
    assert type(preds) is dict
    pred = preds # single
    if 'tweet_id' not in pred:
        # assume schema.org format
        pred['tweet_id'] = dictu.get_in(pred, ['itemReviewed', 'tweet_id'])
    if 'credibility' not in pred:
        pred['credibility'] = dictu.get_in(pred, ['reviewRating', 'ratingValue'])
    if 'confidence' not in pred:
        pred['confidence'] = dictu.get_in(pred, ['reviewRating', 'confidence'], 0.0)
    if 'explanation' not in pred:
        pred['explanation'] = dictu.get_in(pred, ['reviewRating', 'ratingExplanation'])
    if 'ratingExplanation' not in pred:
        pred['ratingExplanation'] = dictu.get_in(
            pred, ['text'],
            dictu.get_in(pred, ['reviewRating', 'ratingExplanation']))
    if 'ratingExplanationFormat' not in pred:
        pred['ratingExplanationFormat'] = 'markdown'
    return pred
                                        

@app.route('/' + app_name + '/api/v1/acred/reviewer/credibility/tweet',
           methods=['POST'])
@app.route('/' + app_name + '/api/v1/tweet/claim/credibility',
           methods=['POST'])
def tweet_predict_credibility():
    try:
        logger.info("Received request " + str(request) +
                    " with content type " + str(request.content_type) +
                    " with form " + str(request.form) +
                    " with json " + str(request.get_json()))
        req_json = request.get_json()
        tweets = req_json['tweets']
        rev_format = req_json.get('reviewFormat')
        basedOn_depth = req_json.get('basedOn_depth', 1) # by default, return till depth 1
        for tweet in tweets:
            if '@context' not in tweet:
                tweet['@context'] = 'http://schema.org'
            if '@type' not in tweet:
                tweet['@type'] = 'Tweet'
        credpred.validate_docs(tweets)

        cfg = acred_config()
        if rev_format is not None:
            cfg = {**cfg,
                   'acred_review_format': rev_format}
        preds = backward_compatible_tweetcred_predictions(
            credpred.predict_credibility(tweets, cfg))
        if basedOn_depth is not None and rev_format == 'schema.org':
            preds = [itnorm.trim_tree(tree, 'isBasedOn', basedOn_depth)
                     for tree in preds]
        return jsonify(preds)
    except InvalidUsage as e:
        raise e
    except werkzeug.exceptions.BadRequest as e:
        logger.error(e, exc_info=True)
        return 'bad request!', 400
    except Exception as e:
        logger.error(e, exc_info=True)
        raise ServerError('Internal server error: ' + str(e), status_code=500)



@app.errorhandler(InvalidUsage)
def handle_invalid_usage(error):
    response = jsonify(error.to_dict())
    response.status_code = error.status_code
    return response


@app.errorhandler(ServerError)
def handle_server_error(error):
    response = jsonify(error.to_dict())
    response.status_code = error.status_code
    return response
