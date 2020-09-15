#
# Copyright (c) 2020 Expert System Iberia
#
"""Provides methods for rading and evaluating a `worthinesspred`ictor on
the clef19 dataset

https://github.com/apepa/clef2019-factchecking-task1#subtask-1--check-worthiness
"""

import torch.utils.data
import math
import pandas as pd
import os
from sklearn import metrics
import logging
import time
from worthiness import worthinesspred

logger = logging.getLogger(__name__)


class Clef19Dataset(torch.utils.data.Dataset):
  def __init__(self, clef_df, batch_size=8):
    super(Clef19Dataset).__init__()
    self.clef_df = clef_df
    self.batch_size = batch_size

  def __len__(self):
    n_sents = self.clef_df.shape[0]
    n_batch = n_sents/self.batch_size
    result = math.ceil(n_batch)
    return result

  def __getitem__(self, index):
    begin, end = index*self.batch_size, (index+1)*self.batch_size
    sub_df = self.clef_df[begin:end]
    result = [{col: row[i]
               for i, col in enumerate(sub_df.columns.values)}
               for row in sub_df.values]
    return result

  def __iter__(self):
    raise NotImplementedError()
    #return self.sts_df.iterrows()


def load_clef19_df(dir_path):
  if not os.path.exists(dir_path):
    return None
  if not os.path.isdir(dir_path):
    return None
  
  field_names = ['line', 'speaker', 'text', 'label']
  sub_dfs = []
  expected_rows = 0
  for f in os.listdir(dir_path):
    if f.endswith('.tsv'):
      f_df = pd.read_csv('%s/%s' % (dir_path, f),
                       names=field_names, sep='\t')
      f_df['file'] = f
      expected_rows += f_df.shape[0]
      sub_dfs.append(f_df)
  result = pd.concat(sub_dfs)
  assert result.shape[0] == expected_rows, 'Expecting %s rows, but got shape %s' % (
      expected_rows, result.shape)
  return result



def test_model(tok_model, cfg):
    """Tests a worthiness predictor model using Clef'19 dataset

    :param tok_model: a worthiness predictor model as returned by `worthinesspred.load_saved_cw_model`
    :param cfg: config options
    :returns: a review for the model describing its accuracy on the tested dataset
    :rtype: dict
    """
    since = time.time()
    logger.info('Evaluating worth pred based on %s' % (cfg))
    te_clef_df = load_clef19_df(cfg.get('clef19_test_worth_path'))
    if te_clef_df is None:
      return {"metrics": {
            "acc": 0.0,
            "f1_weighted": 0.0,
            "prec_micro": 0.0,
            "recall_micro": 0.0,
            "n": 0}}
    
    bsize = int(cfg.get('clef_test_batch_size', 64))
    if 'clef_test_worth_samples' in cfg:
        samples = int(cfg.get('clef_test_worth_samples'))
        assert samples > 0
        if samples < 7080:
            # for reproducibility, we use a fixed random_state
            te_clef_df = te_clef_df.sample(n=samples, random_state=42)
    dataloaders = {'val': torch.utils.data.DataLoader(Clef19Dataset(
        te_clef_df.sample(frac=1), batch_size=bsize))}

    model = tok_model['model']
    assert getattr(model, 'state_dict', None) is not None, "No model to train!!"
    use_tok_type = False  # by default don't use them. Would need to train them, maybe store in model_meta?
    debug = bool(cfg.get('clef_test_debug', False))
    seq_len = int(tok_model['model_meta']['seq_len'])

    def run_epoch(phase):
        """Execute a single epoch through the datasets.
        :param phase can be `train` or `val`
        returns a result dict with `loss` and `pearson`
        """

        def run_step(clef_itembatch):
            """Execute a step in this epoch, ie process a batch.
            Returns a triple with the batch (loss int, label_ids ints, pred_stance_ids ints)
            """
            inputs = [item['text'][0]
                      for item in clef_itembatch]
            assert type(inputs[0]) == str
            label_ids = [item['label'][0] for item in clef_itembatch]
            label_ids = torch.tensor(label_ids)
            if torch.cuda.is_available():
                label_ids = label_ids.cuda()

            input_ids, att_masks = worthinesspred.tokenize_batch(
                inputs, tok_model, debug=debug, max_len=seq_len)

            model_out = model(input_ids, attention_mask=att_masks)
            assert len(model_out) == 1
            logits = model_out[0]
            return label_ids.tolist(), torch.argmax(logits, dim=1).tolist()

        # run epoch:
        model.eval()  # Set model to evaluate mode (important for Dropout layers)

        _label_ids, _pred_ids = [], []
        for clef_itembatch in dataloaders[phase]:  # Iterate over data in epoch
            batch_labels, batch_preds = run_step(clef_itembatch)
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
            "n": len(_label_ids)}}  # run_epoch


    phase = 'val'
    epoch_result = run_epoch(phase)

    time_elapsed = time.time() - since
    msg1 = 'Testing complete in {:.0f}m {:.0f}s'.format(
        time_elapsed // 60, time_elapsed % 60)
    logger.info(msg1)
    msg2 = 'test results: {}'.format(epoch_result['metrics'])
    logger.info(msg2)
    print(msg1 + '\n' + msg2)

    return epoch_result
