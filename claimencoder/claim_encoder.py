#
# Copyright (c) 2019 Expert System Iberia
#
"""Provides a sentence encoder using pre-trained weights
"""
import os
import torch
import numpy as np
from transformers import RobertaModel, RobertaTokenizer
import torch.nn.functional as F
import json
import copy
import logging
from claimencoder import config, sts_b_eval


logger = logging.getLogger(__name__)

sentenceEncoder_schema = {
  'super_types': ['SoftwareApplication', 'Bot'],
  'ident_keys': ['@type', 'name', 'dateCreated', 'softwareVersion',
                 'author', 'launchConfiguration'],
  'itemref_keys': ['author']
}

def as_bot_data(launchConfig):
  return {
    '@context': 'http://coinform.eu',
    '@type': 'SentenceEncoder',
    'additionalType': sentenceEncoder_schema['super_types'],
    'name': 'RoBERTa_Finetuned_Encoder',
    'description': 'Encodes sentences in a way that, hopefully, places semantically similar sentences close to each other. It was trained on SNS-B and achieved 83% accuracy.',
    'author': {
      '@type': 'Organization',
      'name': 'Expert System Lab Madrid',
      'url': 'http://expertsystem.com'
    },
    'dateCreated': '2019-10-17T10:40:00Z',
    'applicationCategory': [ 'NLP', 'SentenceEncoder' ],
    'applicationSuite': ['Co-inform'],
    'softwareRequirements': ['python', 'pytorch', 'transformers', 'RoBERTaTokenizer', 'RoBERTaModel'],
    'softwareVersion': '0.1.1',
    'executionEnvironment': {}, # TODO: esiutils.bot_describer.inspect_execution_env()?
    'launchConfiguration': launchConfig
  }


def pad_encode(text, tokenizer, max_length=50):
  """creates token ids of a uniform sequence length for a given sentence"""
  tok_ids = tokenizer.convert_tokens_to_ids(tokenizer.tokenize(text))
  tok_ids2 = tokenizer.build_inputs_with_special_tokens(tok_ids)
  att_mask = [1 for _ in tok_ids2]
  n_spectoks = len(tok_ids2) - len(tok_ids)
  #print("Tokenizer added %d special tokens" % n_spectoks)
  if len(tok_ids2) > max_length: # need to truncate
    #print('Truncating from', len(tok_ids2))
    n_to_trunc = len(tok_ids2) - max_length
    tok_ids2 = tokenizer.build_inputs_with_special_tokens(tok_ids[:-n_to_trunc])
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


def tokenize_batch(sentences, tok_model, max_len=50, debug=False):
  assert type(sentences) == list
  enc_masks = [pad_encode(s, tokenizer=tok_model['tokenizer'],
                        max_length=max_len) for s in sentences]
  encoded = [enc_mask[0] for enc_mask in enc_masks]
  att_masks = [enc_mask[1] for enc_mask in enc_masks]
  input_ids = torch.tensor(encoded)
  att_masks = torch.tensor(att_masks)
  if debug: print(input_ids.shape)

  if torch.cuda.is_available():
    input_ids = input_ids.cuda()
    att_masks = att_masks.cuda()
  return input_ids, att_masks


def embedding_from_bert_output(bert_output, strategy="pooled"):
  """Given the output tensor from a BERT model, return embeddings for the batch.
  :param strategy can be:
    1. a tuple ("reduce_mean_layer", n) where n is the index of the layer in model
    2. a tuple ("layer", n)
    2. "pooled" returns the default pooled embedding for the model. E.g. for BERT, 
      this is the last output for token [CLS]
  """
  assert len(bert_output) == 3, "Expecting 3 outputs, make sure model outputs hidden states"
  last_layer, pooled, hidden_layers = bert_output
  if strategy == "pooled":
    return pooled
  if not type(strategy) == tuple:
    raise ValueError("Expecting a tuple, but found %s " % (type(strategy)))
  strat_name, strat_val = strategy
  if strat_name == "reduce_mean_layer":
    layer_index = strat_val
    layer_to_pool = hidden_layers[layer_index]
    pooled_layer = torch.sum(layer_to_pool, dim=1) / (layer_to_pool.shape[1] + 1e-10)
    #if debug: print('pooled layer %s of %s' % (layer_index, len(hidden_layers)), 
    #                pooled_layer.shape,
    #                'pooled from', layer_to_pool.shape)
    return pooled_layer
  if strat_name == "layer":
    layer_index = strat_val
    return hidden_layers[layer_index]
  raise ValueError("Unsupported strategy %s " % strategy)



class RoBERTa_Finetuned_Encoder(torch.nn.Module):
  def __init__(self,  
               bert_model_name='roberta-base',
               pooling_strategy="pooled",
               train_from_layer=None,
               seq_len=50,
               powerfun_min_val=0.8, #0.93,
               powerfun_k = 20.0 # 5.0
               ):
    super(RoBERTa_Finetuned_Encoder, self).__init__()
    tokenizer = RobertaTokenizer.from_pretrained(bert_model_name, do_lower_case=False)
    bert_model= RobertaModel.from_pretrained(bert_model_name, output_hidden_states=True)
    
    self.tokenizer = tokenizer
    self.bert_model = bert_model
    self.pooling_strategy = pooling_strategy
    self.seq_len = seq_len

    # power func parameters
    self.min_val = powerfun_min_val # for roberta-base pooled 0.993 
    self.k = powerfun_k # for roberta-base pooled 3.0
    if train_from_layer is not None:
      self.set_train_from_layer(train_from_layer)
    self.bot_data = as_bot_data({
      **self.config(),
      'model_name_or_path': bert_model_name
    })

  def config(self):
    return {
      'pooling_strategy': self.pooling_strategy,
      'seq_len': self.seq_len,
      'powerfun_min_val': self.min_val,
      'powerfun_k': self.k,
      'class': self.__class__.__name__
  }

  def description(self):
    """Returns a schema.org compatible description of this SemanticEncoder

    :returns: 
    :rtype: dict
    """
    return copy.deepcopy(self.bot_data)

  def save_semenc_config(self, semenc_config_file):
    with open(semenc_config_file, mode='w', encoding='utf-8') as out_f:
      json.dump(self.config(), out_f, indent=2)

  def set_train_from_layer(self, from_layer):
    assert type(from_layer) == int
    assert from_layer >= 0 and from_layer <= len(self.bert_model.encoder.layer)
    print("Freezing wordpiece embeddings")
    for param in self.bert_model.embeddings.parameters():
      param.requires_grad = False
    for i, layer in enumerate(self.bert_model.encoder.layer):
      if i < from_layer:
        print("Freezing layer", i)
        for param in layer.parameters():
          param.requires_grad = False
      else:
        print("Trainable layer", i)
    print("Trainable pooling layer") # pooler layer is always trained

  def forward(self, sentences, sents_to_compare=None):
    assert type(sentences) == list
    if sents_to_compare is not None:
      return self.predict_similarity(sentences, sents_to_compare)
    else:
      return self.encode(sentences)

  def predict_encoded_similarity(self, semembs_as, semembs_bs):
    cosim = F.cosine_similarity(semembs_as, semembs_bs) # (batch_size, 1)
    # make prediction a value between 0.0 and 1.0
    return self.power_fun_cosim2predfn(cosim) 

  def predict_similarity(self, sentsA, sentsB):
    """Predict pairwise similarity between two lists of sentences
    Predicted values range from 0 (no similarity) and 1(semantically equal)
    """
    assert type(sentsB) == list
    assert len(sentsB) == len(sentsA)
    #print('semembs_as', type(semembs_as))
    return self.predict_encoded_similarity(
        self.encode(sentsA), self.encode(sentsB)) 


  def power_fun_cosim2predfn(self, cosim,
                             #min_val=0.8,
                             #k= 25,
                             steps=100):
    """Converts a cosine similarity result onto a value in range [0.0, 1.0] using 
    a non-linear mapping. This is useful because cosine similarities betweeen 
    vectors in embedding spaces are usually skewed towards a specific value."""
    min_val, k = self.min_val, self.k
    assert min_val < 1.0
    cosim_step = (1.0-min_val)/steps
    val = torch.clamp(cosim, min=min_val, max=1.0)
    step_i = (val - min_val)/cosim_step
    pred = (step_i/steps)**k
    assert len(pred.shape) == 1, pred.shape  # (batch_size) 
    return torch.clamp(pred, min=0.0, max=1.0)


  def np_power_fun_cosim2predfn(self, cosim, steps=100):
    """Powerfun implementation in numpy

    :param cosim: 
    :param steps: 
    :returns: 
    :rtype: 
    """
    if type(cosim) == list:
      cosim = np.array(cosim, dtype=np.float64)
    assert type(cosim) == np.ndarray, '%s' % (type(cosim))
    min_val, k = self.min_val, self.k
    assert min_val < 1.0
    cosim_step = (1.0-min_val)/steps
    val = np.clip(cosim, min_val, 1.0)
    step_i = (val - min_val)/cosim_step
    pred = (step_i/steps)**k
    #assert len(pred.shape) == 1, pred.shape  #(batch_size)
    return np.clip(pred, 0.0, 1.0)


  def linear_cosim2predfn(self, cosim):
    """Alternative mapping from a cosim tensor to a prediction range
    Use `power_fun_cosim2predf` instead since it better aligns with the 
    distribution of cosine similarities.
    """
    return (cosim + 1.0) / 2.0 # make prediction a value between 0.0 and 1.0


  def encode(self, sentences):
    # essentially the same as calc_sent_emb, but without explicitly setting model
    #  for evaluation (since we can be in training mode)
    def prepend_space(s):
      # RoBERTa requires a whitespace at the start of the seq
      return s if s.startswith(' ') else ' %s' % s
    logger.info("Preparing sentences to encode")

    try:
      sentences = [prepend_space(s) for s in sentences]
      logger.info("Tokenizing %d sentences" % len(sentences))
      input_ids, att_masks = tokenize_batch(
          sentences, {"tokenizer": self.tokenizer,
                      "model": self.bert_model}, max_len=self.seq_len)
      #model_out = self.bert_model(input_ids, attention_mask=att_masks)
      logger.info("Encoding batch of token ids %s %s with model %s" % (
          str(type(input_ids)), input_ids.shape, str(type(self.bert_model))))
      #model_out = self.bert_model(input_ids)  # no mask?, attention_mask=att_masks)
      model_out = self.bert_model.forward(input_ids)  # no mask?, attention_mask=att_masks)
      logger.info("Extracting/pooling embeddings")
      return embedding_from_bert_output(model_out, self.pooling_strategy)
    except Exception as e:
      logger.error('failed to encode ' + str(e))
      raise e


def load_finetuned_semencoder(dir_path):
  semenc_config = {}
  with open(os.path.join(dir_path, 'sem_encoder.json')) as in_f:
    semenc_config = json.load(in_f)

  if semenc_config['class'] == 'RoBERTa_Finetuned_Encoder':
    logger.info("Loading RoBERTa_Finetuned_Encoder with params %s" %
                str(semenc_config))
    result = RoBERTa_Finetuned_Encoder(
        bert_model_name=dir_path,
        pooling_strategy=semenc_config['pooling_strategy'],
        seq_len=semenc_config['seq_len'],
        powerfun_min_val=semenc_config['powerfun_min_val'],
        powerfun_k=semenc_config['powerfun_k'])
  else:
    ValueError("Unsupported class %s" % semenc_config['class'])
  return result


sem_encoder_path = config['claimencoder']['semantic_encoder_dir']
logger.info("Loading semantic encoder from %s" % sem_encoder_path)
semantic_encoder = load_finetuned_semencoder(sem_encoder_path)

def test_sentence_encoder():
    logger.info("Encoding a sentence" )
    _test_embs = semantic_encoder.encode(['Test sentence to encode'])
    logger.info('Encoded sentence %s %s' % (str(type(_test_embs)), _test_embs.shape))

test_sentence_encoder()  # Fail fast if there's something wrong with the encoder

eval_result = sts_b_eval.eval_sts_dev(semantic_encoder, config['claimencoder'])
