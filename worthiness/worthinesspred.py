#
# Copyright (c) 2020 Expert System Iberia
#
"""Implements a deepleaning model for determining whether a sentence
is factual and check-worthy
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

sentWorthReviewer_schema = {
    'super_types': ['SoftwareApplication', 'Bot'],
    'ident_keys': ['@type', 'name', 'dateCreated', 'softwareVersion',
                'isBasedOn', 'launchConfiguration'],
    'itemref_keys': ['isBasedOn']
}


def load_saved_cw_model(in_dir):
    model = RobertaForSequenceClassification.from_pretrained(in_dir)
    if torch.cuda.is_available():
        model = model.cuda()
    tokenizer = RobertaTokenizer.from_pretrained(in_dir)
    with open(os.path.join(in_dir, 'checkworthiness-classifier.json')) as in_f:
        model_meta = json.load(in_f)
    return {
        'tokenizer': tokenizer,
        'model': model,
        'model_meta': model_meta,
        'model_info': worth_reviewer(model_meta, in_dir)
    }


def worth_reviewer(model_meta, in_dir):
    result = {
        '@context': 'http://coinform.eu',
        '@type': 'SentCheckWorthinessReviewer',
        'additionalType': sentWorthReviewer_schema['super_types'],
        'name': 'ESI Sentence Worth Reviewer',
        'description': 'Assesses the worthiness of a sentence: CFS (whorty) NCS (unwhorty). It was trained and evaluated on a group of different datasets (CBD+Poynter+Clef\'19T1) achieving 95% accuracy.',
        'author': bot_describer.esiLab_organization(),
        'dateCreated': '2020-05-08T15:18:00Z',
        'applicationCategory': ['NLP'],
        'applicationSubCategory': ['Check-worthiness'],
        'applicationSuite': ['Co-inform'],
        'softwareRequirements': ['python', 'pytorch', 'transformers', 'RoBERTaModel', 'RoBERTaTokenizer'],
        'softwareVersion': '0.1.0',
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
    result['identifier'] = calc_worth_reviewer_id(result)
    return result


def calc_worth_reviewer_id(worth_reviewer):
    """Calculates a unique id code for a worth reviewer

    :param worth_reviewer: a `SentWorthReviewer` dict
    :returns: a hashcode that tries to capture the identity of the worth reviewer
    :rtype: str
    """
    return hashu.hash_dict(dictu.select_keys(
        worth_reviewer, sentWorthReviewer_schema['ident_keys']
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


def pad_encode(sentence, tokenizer, max_length=50):
  """creates token ids of a uniform sequence length for a given sentence"""
  tok_ids = tokenizer.convert_tokens_to_ids(tokenizer.tokenize(sentence))
  tok_ids2 = tokenizer.build_inputs_with_special_tokens(tok_ids)
  att_mask = [1 for _ in tok_ids2]
  n_spectoks = len(tok_ids2) - len(tok_ids)
  if len(tok_ids2) > max_length: # need to truncate
    #print('Truncating from', len(tok_ids2))
    n_to_trunc = len(tok_ids2) - max_length
    tok_ids2 = tokenizer.build_inputs_with_special_tokens(
        tok_ids[:-n_to_trunc])
    att_mask = [1 for _ in tok_ids2]
  elif len(tok_ids2) < max_length: # need to pad
    padding = []
    for i in range(len(tok_ids2), max_length):
      padding.append(tokenizer.pad_token_id)
    att_mask += [0 for _ in padding]
    tok_ids2 = tok_ids2 + padding
  assert len(tok_ids2) == max_length
  assert len(att_mask) == max_length
  return tok_ids2, att_mask


def tokenize_batch(inputs, tok_model, max_len=50, debug=False):
    assert type(inputs) == list
    enc_masks = [pad_encode(s, tokenizer=tok_model['tokenizer'],
                            max_length=max_len) for s in inputs]
    encoded = [enc_mask[0] for enc_mask in enc_masks]
    att_masks = [enc_mask[1] for enc_mask in enc_masks]
    input_ids = torch.tensor(encoded)
    att_masks = torch.tensor(att_masks)
    # type_ids = torch.tensor([e[2] for e in encoded])
    if debug: print(input_ids.shape)

    if torch.cuda.is_available():
        input_ids = input_ids.cuda()
        att_masks = att_masks.cuda()
        # type_ids = type_ids.cuda()
    return input_ids, att_masks  # , type_ids


def pred_label(inputs, tok_model, strategy="pooled", seq_len=50,
               use_tok_type=True,  # for RoBERTa, we need to train them first!
               debug=False):
    """Returns the embeddings for the input sentences, based on the `tok_model`
    :param tok_model dict with keys `tokenizer` and `model`
    :param strategy see `embedding_from_bert_output`
    """
    input_ids, att_masks = tokenize_batch(
        inputs, tok_model, debug=debug, max_len=seq_len)

    model = tok_model['model']
    model.eval()  # needed to deactivate any Dropout layers

    if debug:
        print('Running with input_ids', input_ids.shape, 'mask', att_masks.shape)
    with torch.no_grad():
        model_out = model(input_ids, attention_mask=att_masks,
                          token_type_ids=None)
    assert len(model_out) == 1
    return model_out[0]


def predict_worthiness(tokmodmeta, sents):
  inputs = sents
  meta = tokmodmeta['model_meta']
  worth2i = meta['label2i']
  preds = pred_label(inputs, tokmodmeta,
                     use_tok_type=False,
                     debug=False,
                     seq_len=int(meta.get('seq_len')))#.cpu().numpy()
  soft_preds = softmax(preds, theta=1, axis=1)
  labids = soft_preds.argmax(axis=1)
  max_vals = np.take_along_axis(
      soft_preds,
      np.expand_dims(labids, axis=1),
      axis=1)
  i2worth = {i: worth for worth, i in worth2i.items()}
  labels = [i2worth[sid] for sid in labids]
  confs = [float(mv[0]) for mv in max_vals]
  assert len(labels) == len(confs), '%d != %d' % (
      len(labels), len(confs))
  return labels, confs


def cw_pred_batched(tokmodmeta, sents, batch_size=64):
    def batches(sents):
        for i in range(0, len(sents), batch_size):
            yield sents[i:i + batch_size]

    list_labels, list_confs = [], []
    for b_i, batch in enumerate(batches(sents)):
        #print("Batch %s (%s sents)" % (b_i, len(batch)))
        labels, confs = predict_worthiness(tokmodmeta, batch)
        list_labels.extend(labels), list_confs.extend(confs)
    return list_labels, list_confs

