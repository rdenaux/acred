#
# Copyright (c) 2020 Expert System Iberia
#
"""Provides methods to perform semantic analysis of documents
"""
import logging
import json
from semantic_analyzer import url_scraper
from datetime import datetime
import requests
import langdetect
from esiutils import dictu, citimings


logger = logging.getLogger(__name__)


def append_field_val(dct, field, newval, dedup=True):
    prev = dct.get(field, [])
    if dedup:
        if newval not in prev:
            prev.append(newval)
    else:
        prev.append(newval)
    dct[field] = prev


def sa_resp_to_aw_ents(sem_analysis):
    if sem_analysis is None:
        return {}    
    result = {}
    for ent in sem_analysis.get('entities', []):
        ent_type = ent['type']  # eg "Military Actions", "PLACES"
        entity = ent['value']  # eg "conflict", "Barack Obama"
        hl = ent['hl']  # eg "|292-299|614-621"

        aw_field = ent_type.lower().replace(' ', '_')
        append_field_val(result, '%s_ss' % aw_field, entity)
        append_field_val(result, '%s_hl' % aw_field, entity + hl)
    return result


def sa_resp_to_aw_categs(sem_analysis):
    result = {}
    for cat in sem_analysis.get('taxonomies', []):
        taxonomy = cat['type']
        codepath = cat['value']
        hl = cat['hl']

        aw_field = 'taxonomy_%s_tax' % taxonomy.lower()
        append_field_val(result, aw_field, codepath)
        append_field_val(result, '%s_hl' % aw_field,
                         codepath + hl)
    return result


def norm_title(value):
    if value.isupper():
        normval = value.lower().title()
        # logger.debug('Normalised "%s" as "%s"' % (value, normval))
        return normval
    else:
        return value


def sa_resp_to_aw_facts(sem_analysis):
    result = {}
    for fact in sem_analysis.get('facts', []):
        taxonomy = fact['type']
        codepath = fact['factName']
        ent_type = dictu.get_in(fact, ['entity', 'type'])
        entity = dictu.get_in(fact, ['entity', 'value'])
        hl = fact['hl']

        aw_field = 'fact_%s_tax' % taxonomy.lower()
        append_field_val(result, aw_field, '%s/%s/%s' % (
            codepath, norm_title(ent_type), entity))
        append_field_val(result, '%s_hl' % aw_field,
                         codepath + hl)

        append_field_val(result,
                         'facts_domain_%s_tax' % taxonomy.lower(),
                         codepath)
    return result


def normalise_rel_ent_type(typ):
    if typ == 'Person':
        return 'People'
    elif typ == 'Organization':
        return 'Organizations'
    else:
        return typ


def normalise_rel_ent(rel_ent):
    return {
        'type': normalise_rel_ent_type(rel_ent['type']),
        'value': rel_ent['value'],
        'id': rel_ent['id']
    }


def normalise_relation(rel):
    return {
        'source': normalise_rel_ent(rel['source']),
        'destination': normalise_rel_ent(rel['destination']),
        'action': rel['action'],
        'start': rel['start'],
        'end': rel['end']
    }


def sa_resp_to_aw_mainElements(sem_analysis):
    result = {}
    for mElt in sem_analysis.get('mainElements', []):
        val = mElt['value']
        hl = mElt['hl']
        # score = mElt['score'] # not used

        aw_field = 'main_elements'
        append_field_val(result, aw_field, val)
        append_field_val(result, '%s_hl' % aw_field, val+hl)
    return result


def sa_resp_to_aw_relations(sem_analysis):
    nrels = [normalise_relation(r)
             for r in sem_analysis.get('relations', [])]
    if len(nrels) == 0:
        return {}
    result = {
        'relations': json.dumps(nrels)}
    for rel in nrels:
        src_type = dictu.get_in(rel, ['source', 'type'])
        src_val = dictu.get_in(rel, ['source', 'value'])
        dest_type = dictu.get_in(rel, ['destination', 'type'])
        dest_val = dictu.get_in(rel, ['destination', 'value'])
        act_type = dictu.get_in(rel, ['action', 'classification'])
        act_val = dictu.get_in(rel, ['action', 'value'])

        append_field_val(result, 'relations_entities',
                         '%s/%s' % (src_type, src_val))
        append_field_val(result, 'relations_entities',
                         '%s/%s' % (dest_type, dest_val))
        append_field_val(result, 'relations_actions',
                         '%s/%s' % (act_type, act_val))
    return result


def _print_field_highlight(field, doc):
    assert not field.endswith('_hl')
    full_content = doc.get('title', '') + '\n\n' + doc['content']
    hl_field = '%s_hl' % field
    if hl_field in doc:
        # print outputs to verify that extracted hl are correct
        for hl_val in doc[hl_field]:
            items = hl_val.split('|')
            item, hls = items[0], items[1:]
            for hl in hls:
                beg, end = hl.split('-')
                print('%s "%s" at %s: %s' % (
                    field, item, hl, full_content[int(beg):int(end)+1]))
    else:
        print('No %s in document' % hl_field)


def try_lang_detect(content):
    try:
        return langdetect.detect(content)
    except Exception as e:
        return "unk"


def try_translate_from(title, content, lang_orig, cfg):
    if 'translation_service_url' not in cfg:
        logger.info("Skipping translation since no MT URL configed")
        return {'title': title,
                'content': content,
                'lang': lang_orig,
                'translateDocument': "Skipped"}
    try:
        t_url = cfg['translation_service_url']
        resp = requests.post(t_url, json={
            'inputs': [
                title,
                content
            ],
            'source': lang_orig,
            'target': 'en',
            'key': cfg['translation_service_key']})
        resp.raise_for_status()
        # not raised, so response OK
        resp_d = resp.json()
        outs = resp_d['outputs']
        assert len(outs) == 2
        return {'title': outs[0]['output'],
                'content': outs[1]['output'],
                'lang': 'en',
                'translatedDocument': 'automatic'}
    except Exception as e:
        logger.error("Failed to translate", e)
        return {'title': title,
                'content': content,
                'lang': lang_orig,
                'translateDocument': "Failed %s" % (e)}


def try_translate(doc, cfg):
    lang_content = try_lang_detect(doc['content'])
    if lang_content == 'unk':
        return doc
    if lang_content != 'en':
        doc['lang_orig'] = lang_content
        content_lang = doc['content']
        title_lang = doc['title']
        translated = try_translate_from(
            title_lang, content_lang, lang_content, cfg)
        doc.update(translated)
        doc['content_language'] = content_lang
        doc['title_language'] = title_lang
    return doc


def merge_semantic_analysis(in_doc, sem_analysis):
    now_iso = datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ")
    # full_content = '%s\n\n%s' % (d2.get('title', ''),  content)
    # title_offset = len(d2.get('title', '')) + 2
    if sem_analysis is None:
        sa_fields = {}
    else:
        sa_fields = {
            **sa_resp_to_aw_ents(sem_analysis),
            **sa_resp_to_aw_categs(sem_analysis),
            **sa_resp_to_aw_facts(sem_analysis),
            **sa_resp_to_aw_mainElements(sem_analysis),
            **sa_resp_to_aw_relations(sem_analysis),
            'essex_id': sem_analysis.get('essex_id')
        }    
    d2 = {**in_doc,
          **sa_fields,
          'status': 'done',
          'submitted_time': now_iso}

    # should be set by crawler?
    # d2['dl_update_date_dt'] = now_iso

    # I'm guessing we should have received this in in_doc
    # d2['size'] = len(full_content) # should we do this here or just receive
    # it looks like every source in AW (RSS, nutch, facebook, twitter etc.)
    # can define their own digest, AW tends to use md5
    # not sure how the standard (if there is such a thing) is defined in AW
    # d2['digest'] = hashlib.md5(
    #    full_content.encode('utf-8')).hexdigest()
    # _print_field_highlight('influential_people', d2)
    # _print_field_highlight('taxonomy_intelligence_tax', d2)
    return d2


def analyze_doc(doc, cfg):
    """Semantically analyses a partial `doc` and outputs a
    document similar to those in AW Solr

    :param doc: dict that must contain at least fields `content` and
      `id`, optional but recommended fields: `title` and various
      metadata fields about where the document comes from and how it
      was processed up to this point.

    :param cfg: any configuration to influence how we analyze the doc.
      In particular, this should tell us about AW services we can
      reuse to perform the analysis such as an available AW
      semantic-api endpoint. We assume that this endpoint will be
      suitable for the language of the content.

    :returns: an analyzed doc that aims to be compatible with the
      standard AW Solr schema.  In particular, the output doc should
      combine the fields in the input doc with fields from semantic
      analysis such as categorization fields `taxonomy_x_tax`, entity
      fields `y_ss`, fact fields `fact_*_tax` However, **if you want
      full compatibility, you should perform a final check** based on
      the Solr schema in order to avoid adding fields by mistake.

    :rtype: dict
    """
    assert type(doc) is dict, str(type(doc))
    if 'content' not in doc:
        assert 'url' in doc, 'Expecting at least a url to resolve doc'
        scraped = url_scraper.scrape(doc['url'])
        doc = {**doc,
               **scraped}

    start = citimings.start()
    doc = try_translate(doc, cfg)

    analyzer_fn = get_analyzer_fn(cfg)
    sem_analysis = analyzer_fn(doc['content'], doc['title'], cfg)
    result = merge_semantic_analysis(doc, sem_analysis)
    timing = citimings.timing('elaboration', start)
    result['elaboration_elapsedtime'] = int(timing['total_ms'])
    if cfg.get('expand_claims', False):
        import semantic_analyzer.claim_content_expander as cce
        result['claims_content'] = cce.calc_claim_content(result, cfg)
    return result

def get_analyzer_fn(cfg):
    analyzer_name = cfg.get('analyzer_name', 'nltk')
    if analyzer_name == 'ciapiclient':
        from ciapiclient import ciapiclient
        return ciapiclient.get_ciapi_semantic_analysis
    elif analyzer_name == 'nltk':
        from semantic_analyzer import nltkanalyzer
        return nltkanalyzer.get_semantic_analysis
    else:
        raise ValueError('Unsupported analyzer_name %s' % (analyzer_name))
