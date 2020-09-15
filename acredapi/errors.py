#
# Copyright (c) 2019 Expert System Iberia
#
"""
API Errors Jsonified
"""
import logging
# from flask import Flask, jsonify, request, g, make_response
from flask import jsonify, request, make_response
from acredapi import app

logger = logging.getLogger(__name__)

@app.errorhandler(404)
def not_found(error=None):
    message = {
            'status': 404,
            'message': 'Not Found: ' + request.url,
    }
    resp = jsonify(message)
    resp.status_code = 404
    return resp


@app.errorhandler(429)
def ratelimit_handler(e):
    return make_response(
            jsonify(error="ratelimit exceeded %s" % e.description),
            429
    )

@app.errorhandler(400)
def bad_request(error):
    print("Bad Request")
    message = {
            'status': 400,
            'message': 'Bad Request: ' + request.url,
    }
    resp = jsonify(message)
    resp.status_code = 400
    return resp
