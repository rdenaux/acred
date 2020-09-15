#
# Copyright (c) 2020 Expert System Iberia
#
"""Provides methods for rading and evaluating a `stancepred`ictor on
the FNC-1 dataset

https://github.com/FakeNewsChallenge/fnc-1
"""

import torch.utils.data
import math
import pandas as pd
import os
import json
import time
import copy
from scipy import stats
from sklearn import metrics
from stance import stancepred
import logging

logger = logging.getLogger(__name__)


class FNC1Dataset(torch.utils.data.Dataset):
  def __init__(self, fnc_stances_df, fnc_bodies_df, batch_size=8):
    super(FNC1Dataset).__init__()
    self.stances_df = fnc_stances_df
    # we'll need to do joins on this field, so set as df's key
    self.bodies_df = fnc_bodies_df.set_index('Body ID')  
    self.batch_size = batch_size

  def __len__(self):
    n_stances = self.stances_df.shape[0]
    n_batch = n_stances/self.batch_size
    result = math.ceil(n_batch)
    return result

  def __getitem__(self, index):
    begin, end = index*self.batch_size, (index+1)*self.batch_size
    joined_df = self.stances_df[begin:end].join(self.bodies_df, 
                                             on ='Body ID')
    result = [{col: row[i] for i, col in enumerate(joined_df.columns.values)}
              for row in joined_df.values]
    #result = []
    #for row in joined_df.values:
    #  result.append({col: row[i] for i, col in enumerate(self.stances_df.columns.values)})
    return result

  def __iter__(self):
    raise NotImplementedError()
    #return self.sts_df.iterrows()


def test_model(tok_model, cfg):
    """Tests a stance predictor model using FNC-1

    :param tok_model: a stance predictor model as returned by `stancepred.load_saved_fnc1_model`
    :param cfg: config options
    :returns: a review for the model describing its accuracy on the tested dataset
    :rtype: dict
    """
    since = time.time()
    logger.info('Evaluating stance pred based on %s' % (cfg))
    te_bodies_path = cfg.get('fnc_test_bodies_path', 'data/evaluation/fnc1/competition_test_bodies.csv')
    te_stances_path = cfg.get('fnc_test_stances_path', 'data/evaluation/fnc1/competition_test_stances.csv')

    empty_result = {"metrics": {
      "acc": 0.0, "f1_weighted": 0.0,
      "prec_micro": 0.0, "recall_micro": 0.0,
      "n": 0}}
    if not os.path.exists(te_bodies_path):
      return empty_result
    if not os.path.exists(te_stances_path):
      return empty_result
    
    te_bodies_df = pd.read_csv(te_bodies_path)
    te_stances_df = pd.read_csv(te_stances_path)
    bsize = int(cfg.get('fnc_test_batch_size', 64))
    if 'fnc_test_stances_samples' in cfg:
        samples = int(cfg.get('fnc_test_stances_samples'))
        assert samples > 0
        if samples < 25413:
            # for reproducibility, we use a fixed random_state
            te_stances_df = te_stances_df.sample(n=samples, random_state=42)
    dataloaders = {'val': torch.utils.data.DataLoader(FNC1Dataset(
        te_stances_df, te_bodies_df, batch_size=bsize))}

    model = tok_model['model']
    assert getattr(model, 'state_dict', None) is not None, "No model to train!!"
    stance2i = tok_model['model_meta']['stance2i']
    use_tok_type=False # by default don't use them. Would need to train them, maybe store in model_meta?
    debug = bool(cfg.get('fnc_test_debug', False))
    seq_len = int(tok_model['model_meta']['seq_len'])
    
    def run_epoch(phase):
        """Execute a single epoch through the datasets. 
        :param phase must be `val`
        returns a result dict with `loss` and `pearson`
        """

        def run_step(fnc1_itembatch):
            """Execute a step in this epoch, ie process a batch. 
            Returns a triple with the batch (loss int, label_stance_ids ints, pred_stance_ids ints) 
            """
            inputs = [(item['Headline'][0], item['articleBody'][0])
                      for item in fnc1_itembatch]
            assert type(inputs[0]) == tuple

            stance_ids = [stance2i[item['Stance'][0]] for item in fnc1_itembatch]
            stance_ids = torch.tensor(stance_ids)
            if torch.cuda.is_available():
                stance_ids = stance_ids.cuda()

            input_ids, att_masks, type_ids = stancepred.tokenize_batch(
                inputs, tok_model, debug=debug, max_len=seq_len)
      
            model_out = model(input_ids, attention_mask=att_masks, 
                              token_type_ids=type_ids if use_tok_type else None)
            assert len(model_out) == 1
            logits = model_out[0]

            return stance_ids.tolist(), torch.argmax(logits, dim=1).tolist()

        # run epoch:
        model.eval()   # Set model to evaluate mode (important for Dropout layers)
      
        _label_ids, _pred_ids = [], []
        for fnc1_itembatch in dataloaders[phase]: # Iterate over data in epoch
            batch_labels, batch_preds = run_step(fnc1_itembatch)
            _label_ids += batch_labels
            _pred_ids += batch_preds
      
        assert len(_label_ids) == len(_pred_ids), "%s %s" % (len(_label_ids), len(_pred_ids))
        epoch_acc = metrics.accuracy_score(_label_ids, _pred_ids)
        epoch_f1 = metrics.f1_score(_label_ids, _pred_ids, average='weighted')
        epoch_prec = metrics.precision_score(_label_ids, _pred_ids, average='micro')
        epoch_recall = metrics.recall_score(_label_ids, _pred_ids, average='micro')
        logger.info('{} acc={:.4f}, f1={:.4f}, p={:.4f}, r={:.4f}, n={}'.format(
            phase, epoch_acc, epoch_f1, epoch_prec, epoch_recall, len(_label_ids)))
        return {"metrics": {
                    "acc": epoch_acc,
                    "f1_weighted": epoch_f1,
                    "prec_micro": epoch_prec,
                    "recall_micro": epoch_recall,
                    "n": len(_label_ids)}} # run_epoch

    phase = 'val'
    epoch_result = run_epoch(phase)

    time_elapsed = time.time() - since
    logger.info('Training complete in {:.0f}m {:.0f}s'.format(
        time_elapsed // 60, time_elapsed % 60))
    logger.info('acc: {:.4f}'.format(epoch_result['metrics']['acc']))

    return epoch_result
    
