#
# Copyright (c) 2020 Expert System Iberia
#
"""Stance detector
"""
import os
import logging
from transformers import RobertaForSequenceClassification
from transformers import RobertaTokenizer
import torch
import json
import numpy as np
from esiutils import bot_describer, dictu, hashu


logger = logging.getLogger(__name__)


sentStanceReviewer_schema = {
    'super_types': ['SoftwareApplication', 'Bot'],
    'ident_keys': ['@type', 'name', 'dateCreated', 'softwareVersion',
                   'isBasedOn', 'launchConfiguration'],
    'itemref_keys': ['isBasedOn']
}

def load_saved_fnc1_model(in_dir):
    model = RobertaForSequenceClassification.from_pretrained(in_dir)
    if torch.cuda.is_available():
        model = model.cuda()
    tokenizer = RobertaTokenizer.from_pretrained(in_dir)
    model_meta = {}
    with open(os.path.join(in_dir, 'fnc1-classifier.json')) as in_f:
        model_meta = json.load(in_f)
    return {
        'tokenizer': tokenizer,
        'model': model,
        'model_meta': model_meta,
        'model_info': stance_reviewer(model_meta, in_dir)
    }


def stance_reviewer(model_meta, in_dir):
    result = {
        '@context': 'http://coinform.eu',
        '@type': 'SentStanceReviewer',
        'additionalType': sentStanceReviewer_schema['super_types'],
        'name': 'ESI Sentence Stance Reviewer',
        'description': 'Assesses the stance between two sentences (e.g. agree, disagree, discuss) it was trained and evaluated on FNC-1 achieving 92% accuracy.',
        'author': bot_describer.esiLab_organization(),
        'dateCreated': '2020-01-13T15:18:00Z',
        'applicationCategory': ['NLP'],
        'applicationSubCategory': ['Stance Detection'],
        'applicationSuite': ['Co-inform'],
        'softwareRequirements': ['python', 'pytorch', 'transformers', 'RoBERTaModel', 'RoBERTaTokenizer'],
        'softwareVersion': '0.1.1',
        'executionEnvironment': {
            **bot_describer.inspect_execution_env(),
            'cuda': torch.cuda.is_available()},
        'isBasedOn': [],
        'launchConfiguration': {
            'model': model_meta,
            'model_config': bot_describer.path_as_media_object(
                os.path.join(in_dir, 'config.json')),
            'pytorch_model': bot_describer.path_as_media_object(
                os.path.join(in_dir, 'pytorch_model.bin'))
        }
    }
    result['identifier'] = calc_stance_reviewer_id(result)
    return result


def calc_stance_reviewer_id(stance_reviewer):
    """Calculates a unique id code for a stance reviewer

    :param stance_reviewer: a `SentStanceReviewer` dict
    :returns: a hashcode that tries to capture the identity of the stance reviewer
    :rtype: str
    """
    return hashu.hash_dict(dictu.select_keys(
        stance_reviewer, sentStanceReviewer_schema['ident_keys']
        ))
    

def softmax(X, theta=1.0, axis=None):
    """
    Compute the softmax of each element along an axis of X.

    From https://nolanbconaway.github.io/blog/2017/softmax-numpy.html

    Parameters
    ----------
    X: ND-Array. Probably should be floats.
    theta (optional): float parameter, used as a multiplier
        prior to exponentiation. Default = 1.0
    axis (optional): axis to compute values along. Default is the
        first non-singleton axis.

    Returns an array the same size as X. The result will sum to 1
    along the specified axis.
    """
    y = np.atleast_2d(X)  # make X at least 2d
    if axis is None:  # find axis
        axis = next(j[0] for j in enumerate(y.shape) if j[1] > 1)
    y = y * float(theta)  # multiply y against the theta parameter,
    # subtract the max for numerical stability
    y = y - np.expand_dims(np.max(y, axis=axis), axis)
    y = np.exp(y)
    # take the sum along the specified axis
    ax_sum = np.expand_dims(np.sum(y, axis=axis), axis)
    p = y / ax_sum  # finally: divide elementwise
    if len(X.shape) == 1:  # flatten if X was 1D
        p = p.flatten()
    return p


def pad_encode(headline, body, tokenizer, max_length=50):
    """creates token ids of a uniform sequence length for a given sentence"""
    tok_ids_0 = tokenizer.convert_tokens_to_ids(tokenizer.tokenize(headline))
    tok_ids_1 = tokenizer.convert_tokens_to_ids(tokenizer.tokenize(body))
    tok_ids2 = tokenizer.build_inputs_with_special_tokens(tok_ids_0, tok_ids_1)
    tok_types = tokenizer.create_token_type_ids_from_sequences(
        tok_ids_0, tok_ids_1)
    att_mask = [1 for _ in tok_ids2]
    assert len(tok_ids2) == len(tok_types), "%d != %d" (
        len(tok_ids2), len(tok_types))
    # n_spectoks = len(tok_ids2) - (len(tok_ids_0) + len(tok_ids_1))
    # print('encoding pair as', len(tok_ids_0), len(tok_ids_1), n_spectoks)
    if len(tok_ids2) > max_length:  # need to truncate
        #print('Truncating from', len(tok_ids2))
        n_to_trunc = len(tok_ids2) - max_length
        tot0_1 = len(tok_ids_0) + len(tok_ids_1)
        assert tot0_1 > 0
        n_to_trunc0 = int(n_to_trunc * (len(tok_ids_0) / tot0_1))
        n_to_trunc1 = n_to_trunc - n_to_trunc0
        ttids0 = tok_ids_0[:-n_to_trunc0] if n_to_trunc0 > 0 else tok_ids_0
        ttids1 = tok_ids_1[:-n_to_trunc1] if n_to_trunc1 > 0 else tok_ids_1
        tok_ids2 = tokenizer.build_inputs_with_special_tokens(ttids0, ttids1)
        tok_types = tokenizer.create_token_type_ids_from_sequences(
            ttids0, ttids1)
        att_mask = [1 for _ in tok_ids2]
    elif len(tok_ids2) < max_length:  # need to pad
        padding = []
        for i in range(len(tok_ids2), max_length):
            padding.append(tokenizer.pad_token_id)
        att_mask += [0 for _ in padding]
        tok_types += [0 for _ in padding]
        tok_ids2 = tok_ids2 + padding
    assert len(tok_ids2) == max_length, '%s != %s \n%s\n%s' % (
        len(tok_ids2), max_length, headline, body)
    assert len(att_mask) == max_length
    assert len(tok_types) == max_length
    return tok_ids2, att_mask, tok_types


def tokenize_batch(inputs, tok_model, max_len=50, debug=False):
    assert type(inputs) == list
    encoded = [pad_encode(headline, body, tokenizer=tok_model['tokenizer'],
                          max_length=max_len) for (headline, body) in inputs]
    input_ids = torch.tensor([e[0] for e in encoded])
    att_masks = torch.tensor([e[1] for e in encoded])
    type_ids = torch.tensor([e[2] for e in encoded])
    if debug:
        print('Input_ids shape: %s' % (input_ids.shape))

    if torch.cuda.is_available():
        input_ids = input_ids.cuda()
        att_masks = att_masks.cuda()
        type_ids = type_ids.cuda()
    return input_ids, att_masks, type_ids


def pred_label(inputs, tok_model, strategy="pooled", seq_len=50,
               use_tok_type=True,  # for RoBERTa, we need to train them first!
               debug=False):
    """Returns the embeddings for the input sentences, based on the `tok_model`
    :param tok_model dict with keys `tokenizer` and `model`
    :param strategy see `embedding_from_bert_output`
    """
    input_ids, att_masks, type_ids = tokenize_batch(
        inputs, tok_model, debug=debug, max_len=seq_len)

    model = tok_model['model']
    model.eval()  # needed to deactivate any Dropout layers

    # if debug:
    logger.info('Stancepred with input_ids %s mask %s, tok_types %s' % (
       input_ids.shape, att_masks.shape, type_ids.shape))
    with torch.no_grad():
        model_out = model(input_ids, attention_mask=att_masks,
                          token_type_ids=type_ids if use_tok_type else None)
    assert len(model_out) == 1
    return model_out[0]


def predict_stances(tokmodmeta, claim_bod_pairs):
    inputs = claim_bod_pairs
    meta = tokmodmeta['model_meta']
    stance2i = meta['stance2i']
    preds = pred_label(inputs, tokmodmeta,
                       seq_len=int(meta.get('seq_len')),
                       use_tok_type=False)
    soft_preds = softmax(preds, theta=1, axis=1)
    labids = soft_preds.argmax(axis=1)
    max_vals = np.take_along_axis(
        soft_preds,
        np.expand_dims(labids, axis=1),
        axis=1)
    i2stance = {i: stance for stance, i in stance2i.items()}
    labels = [i2stance[sid] for sid in labids]
    confs = [float(mv[0]) for mv in max_vals]
    assert len(labels) == len(confs), '%d != %d' % (
        len(labels), len(confs))
    return labels, confs


def predict_stance(tokmodmeta, claim, doc_bodies):
    """Predict stance labels for a `claim` and one or more `doc_bodies`

    :param tokmodmeta: a pre-trained dict with fields
      `model` the pre-trained model
      `tokenizer` the tokenizer to use for encoding string inputs
      `model_meta` metadata useful for configuring and identifying the
        model
    :param claim: str the claim for which to predict stance of documents
    :param doc_bodies: list of strings. The bodies of articles for which
      you want to assess stance relative to the input `claim`
    :returns: a tuple of two aligned lists. The first list contains the
       stance labels (one of `agree`, `disagree`, `discuss`, `unrelated`)
       the second list contains confidence values for the prediction.
    :rtype: tuple
    """
    inputs = [(claim, docbod) for docbod in doc_bodies]
    return predict_stances(tokmodmeta, inputs)
