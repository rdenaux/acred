#
# Copyright (c) 2020 Expert System Iberia
#
"""Loads the STS-B dev set and evaluates a model on it
"""

import pandas as pd
import torch.utils.data
import math
import time
from scipy import stats
import torch.nn.functional as F
import os


def read_sts_csv(path, columns=['source', 'type', 'year', 'id', 'score', 'sent_a', 'sent_b']):
  rows = []
  with open(path, mode='r', encoding='utf-8') as f:
    lines = f.readlines()
    print('Reading', len(lines), 'lines from', path)
    for lnr, line in enumerate(lines):
      cols = line.split('\t')
      assert len(cols) >= 7, 'line %s has %s columns instead of %s:\n\t%s' % (
          lnr, len(cols), 7, "\n\t".join(cols)
      ) 
      cols = cols[:7]
      assert len(cols) == 7
      rows.append(cols)
  result = pd.DataFrame(rows, columns=columns)
  # score is read as a string, so add a copy with correct type
  result['score_f'] = result['score'].astype('float64')
  return result


class STSDataset(torch.utils.data.Dataset):
    # We'll use PyTorch's Dataset and DataLoader mechanisms, so we need to
    # wrap our STS train and dev sets into classes:
    def __init__(self, sts_df, batch_size=20):
        super(STSDataset).__init__()
        self.sts_df = sts_df
        self.batch_size = batch_size

    def __len__(self):
        n_sents = self.sts_df.shape[0]
        n_batch = n_sents/self.batch_size
        result = math.ceil(n_batch)
        #print("Dframe shape: %s, i.e %s sentences, batchSz %s, so %s batches -> %s batches" % (
        #    self.sts_df.shape, n_sents, self.batch_size, n_batch, result
        #))
        return result

    def __getitem__(self, index):
        begin, end = index*self.batch_size, (index+1)*self.batch_size
        values = self.sts_df[begin:end].values
        result = []
        for row in values:
            result.append({col: row[i] for i, col in enumerate(self.sts_df.columns.values)})
        return result

    def __iter__(self):
        raise NotImplementedError()
        #return self.sts_df.iterrows()

    
def eval_sts_dev(encoder, cfg):
    path = cfg.get('stsb_dev_path', 'data/evaluation/sts-dev.csv')
    if not os.path.exists(path):
      return {"pearson": {"r": 0, "p": 0, "n": 0}}
    if not os.path.isfile(path):
      return {"pearson": {"r": 0, "p": 0, "n": 0}}
    
    sts_dev_df = read_sts_csv(path) 
    assert sts_dev_df.shape[0] == 1500
    if 'stsb_test_samples' in cfg:
        samples = int(cfg.get('stsb_test_samples'))
        assert samples > 0
        print('Initial evaluation with %s samples' % (samples))
        if samples < 1500:
            # for reproducibility, we use a fixed random_state
            sts_dev_df = sts_dev_df.sample(n=samples, random_state=42)
    dataloaders = {'val': torch.utils.data.DataLoader(STSDataset(sts_dev_df, batch_size=32))}
    device = 'cuda' if torch.cuda.is_available() else 'cpu'
    return run_semantic_encoder(encoder, dataloaders, device=device)


def run_semantic_encoder(semantic_encoder, 
                         dataloaders, 
                         #cosim2predfn=power_fun_cosim2predfn,
                         device="cuda"):
    """ Trains a semantic encoder model
    """
    since = time.time()
  
    assert getattr(semantic_encoder, 'state_dict', None) is not None, "No model to train!!"

    def run_epoch(phase):
        """Execute a single epoch through the datasets. 
        returns a result dict with `loss` and `pearson`
        """

        def run_step(sts_itembatch):
            """Execute a step in this epoch, ie process a batch. 
            Returns a triple with the batch (loss int, labels floats, predictions floats) 
            """
            #print('sts_itembatch', type(sts_itembatch))
            sent_as = [item['sent_a'][0] for item in sts_itembatch]
            sent_bs = [item['sent_b'][0] for item in sts_itembatch]
            assert type(sent_as[0]) == str
            label_scores = torch.tensor([float(item['score'][0]) for item in sts_itembatch])

            label_scores = label_scores.to(device)

            semembs_as = semantic_encoder.encode(sent_as)
            semembs_bs = semantic_encoder.encode(sent_bs)
            #print('semembs_as', type(semembs_as))
            cosim = F.cosine_similarity(semembs_as, semembs_bs)
            # make prediction a value between 0.0 and 1.0
            pred_score = semantic_encoder.np_power_fun_cosim2predfn(cosim.tolist())
            #pred_score = semantic_encoder.power_fun_cosim2predfn(cosim) 

            return label_scores.tolist(), pred_score.tolist()

        # run epoch:
        semantic_encoder.eval()   # Set model to evaluate mode (important for Dropout layers)
      
        _label_scores, _pred_scores = [], []
        for sts_itembatch in dataloaders[phase]: # Iterate over data in epoch
            batch_labels, batch_preds = run_step(sts_itembatch)
            _label_scores += batch_labels
            _pred_scores += batch_preds
      

        assert len(_label_scores) == len(_pred_scores), "%s %s" % (len(_label_scores), len(_pred_scores))
        epoch_correl, p_val = stats.pearsonr(_label_scores, _pred_scores)
        print('{} Pearson: r={:.4f} p={:.4f} n={}'.format(
            phase, epoch_correl, p_val, len(_label_scores)))
        return {"pearson": {"r": epoch_correl,
                            "p": p_val,
                            "n": len(_label_scores)}}


    # Each epoch has a training and validation phase
    epoch_result = run_epoch('val')

    time_elapsed = time.time() - since
    print('Eval complete in {:.0f}m {:.0f}s'.format(
        time_elapsed // 60, time_elapsed % 60))

    return epoch_result
    
