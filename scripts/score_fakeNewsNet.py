#
# 2020 ExpertSystem
#
'''Script for generating acred reviews for the fakeNewsNet dataset

See https://github.com/KaiDMML/FakeNewsNet for instructions on how to
retrieve the texts from the article URLs

See also scripts/fetch-data.sh, which should download the input json file
and place it in the `data/evaluation/` folder.

'''
import argparse
import time
import os
import pandas as pd
import sklearn.metrics as metrics

parser = argparse.ArgumentParser(
     description='Scores credibility reviews for part of the FakeNewsNet dataset',
     formatter_class=argparse.ArgumentDefaultsHelpFormatter)
parser.add_argument(
     '-fakeNewsNetFolder',
     help='Path to the fakenewsnet_dataset folder',
     required=True)
parser.add_argument(
     '-data_feature', choices=['news_articles'], default='news_articles',
     help='Currently, only support for "news_articles" (in future we could add support for "tweets")')
parser.add_argument(
     '-news_source', choices=['politifact', 'gossipcop'], default='politifact',
     help='Either "politifact" or "gossipcop"')
parser.add_argument(
     '-predictions_csv', type=str,
     help='Path to the csv with predictions')

def gen_item_ids(base_dir, news_label):
    for item_dir in os.listdir('%s/%s' % (base_dir, news_label)):
        yield item_dir

if __name__ == '__main__':
    #_setup_logging()
    args = parser.parse_args()

    start = time.time()

    gold = []
    base_dir = '%s/%s' % (args.fakeNewsNetFolder, args.news_source)
    print('base_dir %s' % base_dir)
    for item_id in gen_item_ids(base_dir, 'fake'):
        gold.append({
            'item_id': item_id,
            'label': 'fake'
        })

    for item_id in gen_item_ids(base_dir, 'real'):
        gold.append({
            'item_id': item_id,
            'label': 'real'
        })
    gold_df = pd.DataFrame(gold)
    pred_df = pd.read_csv(args.predictions_csv)

    print('gold_df.rows %s, unique ids %s' % (gold_df.shape[0], len(gold_df.item_id.unique())))
    print('pred_df.shape %s, unique ids %s' % (pred_df.shape[0], len(pred_df.item_id.unique())))

    goldls = gold_df.label.tolist()
    predls = pred_df.label.tolist()

    print('Scoring credibility accuracy of %s fakeNewsNet articles' % (len(goldls)))
    print('\taccuracy:  %.4f' % (metrics.accuracy_score(goldls, predls)))
    print('\tf1_macro:  %.4f' % (metrics.f1_score(goldls, predls, average='macro')))
    print('\tprecision: %.4f' % (metrics.precision_score(goldls, predls, average='macro', zero_division=0)))
    print('\trecall:    %.4f' % (metrics.recall_score(goldls, predls, average='macro', zero_division=0)))

    pred_valid_df = pred_df[pred_df['explanation'] != 'Missing FakeNewsNet input json']
    print('pred based on data rows %s' % (pred_valid_df.shape[0]))
    merged_valid_df = pred_valid_df.merge(gold_df, on='item_id', suffixes=['_acred','_gold'])
    print('merged valid based on data rows %s' % (merged_valid_df.shape[0]))
    predls = merged_valid_df.label_acred.tolist()
    goldls = merged_valid_df.label_gold.tolist()
    print('Scoring credibility accuracy of %s valid fakeNewsNet articles' % (len(goldls)))
    print('\taccuracy:  %.4f' % (metrics.accuracy_score(goldls, predls)))
    print('\tf1_macro:  %.4f' % (metrics.f1_score(goldls, predls, average='macro')))
    print('\tprecision: %.4f' % (metrics.precision_score(goldls, predls, average='macro', zero_division=0)))
    print('\trecall:    %.4f' % (metrics.recall_score(goldls, predls, average='macro', zero_division=0)))

    
    
    end = time.time()
    timing = "%s s" % (end - start)
    print('done')
