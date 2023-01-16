#
# 2020 ExpertSystem
#
'''Script for generating predictions for Task2 of CLEF 2018 using the 
acred predictor

See https://github.com/clef2018-factchecking/clef2018-factchecking

See also scripts/fetch-data.sh, which should download the v1.0 release
and place it in the `data/evaluation/` folder.
'''
import argparse
import sys
import os
import os.path as osp
import time
import requests
import json
import pandas as pd
import logging

logger = logging.getLogger(__name__)


def get_in(dct, path, default_val=None):
    """Gets a nested value in a dict by following the path

    :param dct: a python dictionary
    :param path: a list of keys pointing to a node in dct
    :returns: the value at the specified path
    :rtype: any
    """
    if dct is None:
        return default_val
    assert len(path) > 0
    next_dct = dct.get(path[0], None)
    if len(path) == 1:
        return next_dct
    return get_in(next_dct, path[1:], default_val=default_val)


def read_all_factuality_claims(folder):
  files = [f for f in os.listdir(folder) if 'README' not in f]
  columns = ['line_number', 'speaker', 'text', 'claim_number', 'normalized_claim', 'label']
  fds = {f: pd.read_csv(osp.join(folder, f), sep='\t', names=columns)
          for f in files}
  return {f: df[df['label'] != '-']
          for f, df in fds.items()}


def acred_as_clef_label(ci_cred, thresh=0.4):
    assert thresh >= 0.0
    assert thresh <= 1.0
    if '@type' in ci_cred:
      val = ci_cred['ratingValue']
    else:
      val = ci_cred['value']
    if val >= thresh:
        return 'TRUE'
    elif val <= -thresh:
        return 'FALSE'
    else:
        return 'HALF-TRUE'


def build_parser():
    parser = argparse.ArgumentParser(
        description='Genrate predictions for Task2 of CLEF 2018',
        formatter_class=argparse.ArgumentDefaultsHelpFormatter)
    parser.add_argument(
        '-inputFolder',
        help='Path to a folder with tsv files ending in .txt',
        required=True)
    parser.add_argument(
        '-outFolder',
        help='Path to a folder where the results should be written to',
        required=True)
    parser.add_argument(
        '-config',
        help='Path to a json file with configurations for calling the predictor')
    return parser


def setup_logging():
    root_logger = logging.getLogger('')
    root_logger.setLevel(logging.DEBUG)
    lformat = logging.Formatter(
        '%(asctime)s %(name)s:%(levelname)s: %(message)s')
    lsh = logging.StreamHandler(sys.stdout)
    lsh.setFormatter(lformat)
    root_logger.addHandler(lsh)
  
if __name__ == '__main__':
    parser = build_parser()
    setup_logging() # do here so we can log issues during CLI parsing
    args = parser.parse_args()

    all_start = time.time()
    f2df = read_all_factuality_claims(args.inputFolder)
    assert os.path.exists(args.outFolder), 'Output folder %s must exist' % (args.outFolder)
    assert os.path.isdir(args.outFolder), 'Value for outFolder is not a folder'
    
    cfg = {}
    if args.config is not None:
        with open(args.config, encoding='utf8') as cf:
            cfg = json.load(cf)

    acredapi_url = cfg['acredapi_url']
    cred_thresh = float(cfg['cred_threshold'])
    cred_path = ['reviewRating']

    for f, df in f2df.items():
        clef_pred = []
        handled_ids = []
        claims = df.to_dict(orient='records')
        for ci, claim in enumerate(claims):
            logger.info('Claim %d of %d in %s' % (ci, len(claims), f))
            cid = int(claim['claim_number'])
            if cid in handled_ids:
                logger.info('Skipping as previously handled')
                continue
            url = '%s/api/v1/claim/predict/credibility?claim=%s' % (
                acredapi_url, claim['normalized_claim'])
            resp = requests.get(url, verify=False)
            resp.raise_for_status()
            claimcreds = resp.json()
            credRating = get_in(claimcreds[0], cred_path)
            clef_pred.append({
                'id': cid,
                'label': acred_as_clef_label(
                    credRating, cred_thresh)})
            handled_ids.append(cid)

            
            out_dir = '%s/reviews' % (args.outFolder)
            if not os.path.exists(out_dir):
              print('Creating dir %s for the reviews' % (out_dir))
              os.makedirs(out_dir)

            # write CredibilityReview to outFolder
            fname = f.replace('.txt', '_%s.json' % cid)
            with open('%s/%s' % (out_dir, fname), 'w') as f_out:
              json.dump(claimcreds[0], f_out, indent=2)


        # Finished processing all input files, now write collected ratings
        outf = '%s/%s' % (args.outFolder, f.replace('task2-en-', 'primary-en-'))
        pd.DataFrame(clef_pred).to_csv(
            outf, header=False, index=False, sep='\t')
    total_s = time.time() - all_start
    print('Finished in %.3fs i.e. %.3fclaims/s' % (
        total_s, len(clef_pred)/total_s))
    print('Finished pred_clef2018')

