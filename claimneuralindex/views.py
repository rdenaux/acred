#
# Copyright (c) 2019 Expert System Iberia
#
"""
API Views for serving user requests with examples
Add your own methods here
"""
import logging
import werkzeug
from flask import jsonify, request
from claimneuralindex import claim_neural_index
from claimneuralindex import app, config, resources
from stance import stancepred
from esiutils import citimings


logger = logging.getLogger(__name__)
app_name = config['claimneuralindex']['app_name']


@app.route('/' + app_name + '/sim_reviewer', methods=['GET'])
def sim_reviewer():
    try:
        index_format = request.args.get('index_format', 'numpy') # by default we use numpy
        return jsonify(claim_neural_index.sim_reviewer(resources.vec_space, index_format))
    except werkzeug.exceptions.BadRequest as e:
        logger.exception(e)
        return 'bad request! ' + str(e), 400
    except Exception as e:
        logger.exception(e)
        resp = jsonify({"error": str(e)})
        resp.status_code = 500
        return resp
        

@app.route('/' + app_name + '/search_semantic_vecspace',
           methods=['POST'])
def search_sem_vecspace():
    try:
        req_json = request.get_json()
        qsentences = req_json['query_sentences']
        topn = req_json.get('topn', 10)
        prov = req_json.get('provenance') in ['True', True, 'true', 'yes']
        index_format = req_json.get('index_format', 'numpy')
        assert type(qsentences) == list
        if len(qsentences) == 0:
            raise werkzeug.exceptions.BadRequest('Missing query_sentences')
        assert len(qsentences) > 0
        assert type(topn) == int
        assert topn > 0

        logger.info('Neural semantic search for %d query sentences topn=%d' % (
            len(qsentences), topn))
        q_preds, q_labels, simReviewer = claim_neural_index.search_semantic_vecspace(
            resources.vec_space,
            qsentences, topn, index_format)
        assert len(q_preds) == len(qsentences)
        assert len(q_labels) == len(qsentences)
        prov_dict = {}
        if prov:
            prov_dict = {
                'author': simReviewer 
                }
        return jsonify({
            'similarities': q_preds,
            'claim_ids': q_labels,
            **prov_dict
        })
    except werkzeug.exceptions.BadRequest as e:
        logger.error(e, exc_info=True)
        logger.error(str(e))
        return 'bad request! ' + str(e), 400
    except Exception as e:
        logger.error(e, exc_info=True)
        resp = jsonify({"error": str(e)})
        resp.status_code = 500
        return resp


def validate_stance_pred_q(qclaim, doc_bodies):
    assert type(qclaim) == str
    assert type(doc_bodies) == list
    if len(doc_bodies) == 0:
        raise werkzeug.exceptions.BadRequest('Missing doc_bodies')
    assert len(doc_bodies) > 0


@app.route('/' + app_name + '/stance_predictor', methods=['GET'])
def stance_predictor():
    try:
        tokmodmeta = resources.stance_tokmodmeta
        return jsonify(tokmodmeta['model_info'])
    except werkzeug.exceptions.BadRequest as e:
        logger.exception(e)
        return 'bad request! ' + str(e), 400
    except Exception as e:
        logger.exception(e)
        resp = jsonify({"error": str(e)})
        resp.status_code = 500
        return resp

    
@app.route('/' + app_name + '/predict_stance', methods=['POST'])
def predict_stance():
    try:
        start = citimings.start()
        req_json = request.get_json()
        inputs = []
        if type(req_json) == list:
            for claim_bods in req_json:
                qclaim = claim_bods['qclaim']
                doc_bodies = claim_bods['doc_bodies']
                validate_stance_pred_q(qclaim, doc_bodies)
                inputs.extend([(qclaim, docbod) for docbod in doc_bodies])
        else:  # assume single input
            qclaim = req_json['qclaim']
            doc_bodies = req_json['doc_bodies']
            validate_stance_pred_q(qclaim, doc_bodies)
            inputs.extend([(qclaim, docbod) for docbod in doc_bodies])

        tokmodmeta = resources.stance_tokmodmeta
        if len(inputs) == 0:
            return jsonify({'labels': [],
                            'confidences': [],
                            'meta': {
                                'model_info': tokmodmeta['model_info'],
                                'timings': citimings.timing(
                                    'predict_stance', start),
                                'n_pairs': len(inputs)
                            }})
        labels, confs = stancepred.predict_stances(tokmodmeta, inputs)
        return jsonify({
            'labels': labels,
            'confidences': confs,
            'meta': {
                'model_info': tokmodmeta['model_info'],
                'timings': citimings.timing('predict_stance', start),
                'n_pairs': len(inputs)
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
