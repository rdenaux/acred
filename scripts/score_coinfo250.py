#
# 2020 ExpertSystem
#
'''Script for scoring predictions for the coinform250 dataset

See https://github.com/co-inform/Datasets

See also scripts/fetch-data.sh, which should download the input json file
and place it in the `data/evaluation/` folder.

Finally, see scripts/pred_coinfo240.py, which let's you use an instance of 
acred to generate predictions.
'''
import argparse
import time
import json
import os
import os.path as osp
import pandas as pd
import sklearn.metrics as metrics
from collections import Counter


if __name__ == '__main__':
    parser = argparse.ArgumentParser(
        description='Score accuracy of credibility reviews for the coinform250 dataset',
        formatter_class=argparse.ArgumentDefaultsHelpFormatter)
    parser.add_argument(
        '-goldJson',
        help='Path to the coinform250.json file',
        default='data/evaluation/coinform250.json')
    parser.add_argument(
        '-pred_csv',
        help='Path to the prediction csv as output by the pred_coinfo250.py script',
        default='data/evaluation/coinform250_reviews/predictions.csv')

    args = parser.parse_args()
    all_start = time.time()

    assert osp.isfile(args.goldJson), 'Invalid path to dataset %s' % (args.goldJson)
    assert osp.isfile(args.pred_csv), 'Invalid path to predictions %s' % (args.pred_csv)

    gold = []
    with open(args.goldJson) as jsonl_file:
        gold = [json.loads(line) for line in jsonl_file]
    assert len(gold) > 0, '%s' % (len(gold))
    gold_df = pd.DataFrame(gold)
    preds_df = pd.read_csv(args.pred_csv)

    assert gold_df.shape[0] == preds_df.shape[0], 'Cannot score %s predictions for %s tweets. %s' % (
        preds_df.shape[0], gold_df.shape[0], 'Maybe prediction failed for some reason? Check your logs.')

    goldl = gold_df.label.tolist()
    predl = preds_df.label.tolist()
    
    print('Scoring credibility accuracy of %s coinform250 tweets' % (len(gold)))
    print('\taccuracy:  %.4f' % (metrics.accuracy_score(goldl, predl)))
    print('\tf1_macro:  %.4f' % (metrics.f1_score(goldl, predl, average='macro')))
    print('\tprecision: %.4f' % (metrics.precision_score(goldl, predl, average='macro', zero_division=0)))
    print('\trecall:    %.4f' % (metrics.recall_score(goldl, predl, average='macro', zero_division=0)))
    print('\tconfusion_matrix:\n', metrics.confusion_matrix(goldl, predl))
    print(sorted(Counter(goldl).items()))
    print(sorted(Counter(predl).items()))

    print('Finished in %.3fs' % (time.time() - all_start))
