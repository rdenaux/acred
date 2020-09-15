#
# Copyright (c) 2019 Expert System Iberia
#
"""
API Views for serving user requests
"""
import logging
import werkzeug
from flask import json, jsonify, request, make_response
from claimencoder.claim_encoder import semantic_encoder
from claimencoder import app, config
import numpy as np

logger = logging.getLogger(__name__)
app_name = config['claimencoder']['app_name']


@app.route('/' + app_name + '/log',
           methods=['POST'])
def log():
    try:
        req_json = request.get_json()
        logger.info('Received echo request with object %s' % str(req_json))
        return "ok", 200
    except Exception as e:
        resp = jsonify({"error": str(e)})
        resp.status_code = 500
        return resp


@app.route('/' + app_name + '/encoder_info',
           methods=['GET'])
def encoder_info():
    try:
        return jsonify({
            'semanticEncoder': semantic_encoder.description()})
    except Exception as e:
        logger.exception(e)
        resp = jsonify({"error": str(e)})
        resp.status_code = 500
        return resp
    

@app.route('/' + app_name + '/encode_sents',
           methods=['POST'])
def encode_sents():
    try:
        req_json = request.get_json()
        sentences = req_json['sentences']
        assert type(sentences) == list
        assert len(sentences) > 0
        logger.info('Encoding %d sentences' % len(sentences))
        vecs = semantic_encoder.encode(sentences)
        logger.info("Converting tensor to list")
        vecs = vecs.detach().tolist()
        assert len(vecs) == len(sentences)
        return jsonify({'semantic_encodings': vecs,
                        'author': semantic_encoder.description()})
    except werkzeug.exceptions.BadRequest as e:
        logger.exception(e)
        return 'bad request!', 400
    except Exception as e:
        logger.exception(e)
        resp = jsonify({"error": str(e)})
        resp.status_code = 500
        return resp

@app.route('/' + app_name + '/compare_sents',
           methods=['POST'])
def compare_sents():
    try:
        req_json = request.get_json()
        sentA = req_json['sentA']
        sentB = req_json['sentB']
        sentences = [sentA, sentB]
        assert type(sentences) == list
        assert len(sentences) > 0
        logger.info('Encoding %d sentences' % len(sentences))
        vecs = semantic_encoder.encode(sentences)
        logger.info("Converting tensor to list")
        vecs = vecs.detach().tolist()
        assert len(vecs) == len(sentences)
        print("a.type", type(vecs[0]))
        print("len(a)", len(vecs[0]))
        a, b = np.array(vecs[0]), np.array(vecs[1])
        anorm, bnorm = np.linalg.norm(a), np.linalg.norm(b)
        print("anorm.type", type(a))
        print("a.shape", a.shape, "b.shape", b.shape)
        cos_sim = np.dot(a, b)/(anorm * bnorm)

        preds = semantic_encoder.np_power_fun_cosim2predfn([cos_sim])
        preds = preds.tolist()

        return jsonify({'cosim': cos_sim,
                        'pred': preds[0]})
    except werkzeug.exceptions.BadRequest as e:
        logger.exception(e)
        return 'bad request!', 400
    except Exception as e:
        logger.exception(e)
        resp = jsonify({"error": str(e)})
        resp.status_code = 500
        return resp
        

@app.route('/' + app_name + '/cosim_to_pred_score',
           methods=['POST'])
def cosim2predscore():
    try:
        req_json = request.get_json()
        cosims = req_json['cosims']
        assert type(cosims) == list
        assert len(cosims) > 0
        logger.info('Converting %d cosine similarity scores' % len(cosims))
        preds = semantic_encoder.np_power_fun_cosim2predfn(cosims)

        preds = preds.tolist()
        assert len(preds) == len(cosims)
        return jsonify({'similarity_scores': preds,
                        'author': semantic_encoder.description()})
    except werkzeug.exceptions.BadRequest as e:
        logger.exception(e)
        return 'bad request!', 400
    except Exception as e:
        logger.exception(e)
        resp = jsonify({"error": str(e)})
        resp.status_code = 500
        return resp
