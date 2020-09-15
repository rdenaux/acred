#
# Copyright (c) 2019 Expert System Iberia
#
"""
API Views for serving user requests
"""
import logging
import werkzeug
from flask import json, jsonify, request, make_response
from worthiness import worthinesspred
from worthiness import app, config, resources
from esiutils import citimings, hashu, bot_describer, dictu


logger = logging.getLogger(__name__)
app_name = config['worthinesschecker']['app_name']


@app.route('/' + app_name + '/worthiness_predictor', methods=['GET'])
def worthiness_predictor():
    try:
        tokmodmeta = resources.worthiness_tokmodmeta
        return jsonify(tokmodmeta['model_info'])
    except werkzeug.exceptions.BadRequest as e:
        logger.exception(e)
        return 'bad request! ' + str(e), 400
    except Exception as e:
        logger.exception(e)
        resp = jsonify({"error": str(e)})
        resp.status_code = 500
        return resp
    

@app.route('/' + app_name + '/predict_worthiness', methods=['POST'])
def predict_worthiness():
    try:
        tokmodmeta = resources.worthiness_tokmodmeta
        start = citimings.start()
        req_json = request.get_json()
        q_sents = req_json['sentences']
        if q_sents is None:
            raise ValueError("sentences parameter is mandatory, only got %s" % (req_json))
        if type(q_sents) is str:
            q_sents = [q_sents]
        if type(q_sents) is not list:
            raise ValueError("Type %s not accepted. Valid formats: string or list" % type(req_json['sentences']))

        if len(q_sents) == 0:
            label, conf, ids = [], [], []
        else:
            label, conf = worthinesspred.cw_pred_batched(tokmodmeta, q_sents)
            logger.debug('predicted %s labels and %s confidences' % (len(label),  len(conf)))
            ids = [hashu.calc_str_hash(ids) for ids in q_sents]

        return jsonify({
            'worthiness_checked_sentences': {
                'sentences': q_sents,
                'predicted_labels': label,
                'prediction_confidences': conf,
                'sentence_ids': ids,
            },
            'meta': {
                'model_info': tokmodmeta['model_info'],
                'timings': citimings.timing('predict_worthiness', start),
            }
        })

    except werkzeug.exceptions.BadRequest as e:
        logger.exception(e)
        return 'bad request! ' + str(e), 400
    except Exception as e:
        logger.exception(e)
        resp = jsonify({"error": str(e)})
        resp.status_code = 500
        return resp

