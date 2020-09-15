import re
import logging

logger = logging.getLogger(__name__)


def is_full_match(regex, s):
    match = re.search(regex, s)
    if match:
        return match.span() == (0, len(s))
    return False


def is_fact_tax_hl_field(name):
    regex = 'fact_\w+_tax_hl'
    return is_full_match(regex, name)


def is_tax_hl_field(name):
    regex = 'taxonomy_(\w|_)+_tax_hl'
    return is_full_match(regex, name)


def is_ent_hl_field(name):
    regex = '(\w|_)+_hl'
    return is_full_match(regex, name) and not (
        is_fact_tax_hl_field(name) or is_tax_hl_field(name))


def gen_hl_spans(doc, hl_fields):
    for field in hl_fields:
        for hl_val in doc[field]:
            items = hl_val.split('|')
            for hl in items[1:]:
                beg, end = hl.split('-')
                yield {
                    'field': field,
                    'value': items[0],
                    'span': (int(beg), int(end))
                }


def append_field_val(dct, field, newval, dedup=True):
    prev = dct.get(field, [])
    if dedup:
        if newval not in prev:
            prev.append(newval)
    else:
        prev.append(newval)
    dct[field] = prev


def index_ent_spans(doc):
    ent_hl_fields = [f for f in doc.keys() if is_ent_hl_field(f)]
    logger.debug('Found %s entity hl fields: %s' % (
        len(ent_hl_fields), ent_hl_fields))
    if len(ent_hl_fields) == 0:
        logger.debug('fields:\n\t' + '\n\t'.join(list(doc.keys())))
    index = {}
    for hl_span in gen_hl_spans(doc, ent_hl_fields):
        append_field_val(index, hl_span['span'],
                         hl_span['value'])
    return index


def valid_span(s):
    assert type(s) is tuple, type(s)
    assert len(s) == 2, str(s)
    b, e = s
    assert type(b) == int, str(s)
    assert type(e) == int, str(s)
    #  cogito spans end at e+1, so 1-char entities could
    #  have e == b
    return e >= b


def in_span(outer, inner):
    assert valid_span(outer), str(outer)
    assert valid_span(inner), str(inner)
    ob, oe = outer
    ib, ie = inner
    return ib >= ob and ie <= oe


def relative_span(orig_span, ref_span):
    ref_b = ref_span[0]
    b, e = orig_span
    return (b-ref_b, e-ref_b)


def as_ent_replacement(text, ent_span, ents, cfg):
    beg, end = ent_span
    to_norm = text[beg:end+1]
    lower_ents_to_ents = {ent.lower(): ent for ent in ents}
    lower_ents = list(lower_ents_to_ents.keys())
    if to_norm.lower() in lower_ents:
        # different capitalisation
        return []
    superstrs = [ent for ent in lower_ents
                 if to_norm.lower() in ent]
    if len(superstrs) > 0:
        # span is a substring e.g. 'Obama' instead of 'Barack Obama'
        return []

    substrs = [ent for ent in lower_ents
               if ent in to_norm.lower()]
    if len(substrs) > 0:
        # span is a superstring e.g. 'proceedings' intead of 'precoeeding'
        return []

    # TODO: handle pronouns (who, whom, he, she, they)
    #  possilby only if the entity does not already appear in the
    #  text (otherwise, we hope the text should be clear enough for
    #  reader to resolve the anaphora)
    pronouns = ['he', 'she', 'they', 'the company', 'the country',
                'who', 'whom']
    if to_norm.lower() in pronouns:
        lents_mentioned = [ent for ent in lower_ents
                           if ent in text.lower()]
        if len(lents_mentioned) > 0:
            # return {span: lents_not_mentioned[0]} ?
            return []
        else:
            ent = lower_ents_to_ents[lower_ents[0]]
            return [(to_norm, ent)]

    # TODO: handle possessives (his, her, their, its)
    # TODO: handle abbreviations (to_norm is capitals and points?)
    # TODO: handle synonyms (e.g. prosecution and proceedings)
    return []


def contextualise_sentence(sentence, span, ent_index, cfg):
    ents_in_span = {
        relative_span(ent_span, span): ents
        for ent_span, ents in ent_index.items()
        if in_span(span, ent_span)}
    replacements = {
        span: replacement
        for span, ents in ents_in_span.items()
        for replacement in as_ent_replacement(sentence, span, ents, cfg)
    }
    if len(replacements) > 0:
        spans = sorted([ent_span for ent_span in replacements])
        spans.reverse()
        out_sent = sentence[0:len(sentence)]
        for s in spans:
            beg, end = s
            old, ent = replacements[s]
            out_sent = out_sent[:beg] + ent + out_sent[end+1:]
        logger.debug(
            'content:\n\t%s\n->%s\n\t%s' % (
                sentence,
                replacements,
                out_sent))
        return out_sent
    return None


def extract_content(full_content, span, ent_index, cfg):
    beg, end = span
    result = full_content[beg:end+1]
    contextualised = contextualise_sentence(result, span, ent_index, cfg)
    resultd = {'content': result}
    if contextualised is not None:
        resultd['contextual_content'] = contextualised
    return resultd


def calc_claim_content(doc, cfg):
    """Given a semantic analysis, adds field `claim_content`

    :param doc: dict with at least fields `content`,
      `title` and one or more `fact_*_tax_hl` fields
    :param cfg: config parameters to control how to extract claims
    :returns: a list of `claim_content` values. Note this method
      **does not** modify `doc` (nor `cfg`)
    :rtype: list
    """
    full_content = doc.get('title', '') + '\n\n' + doc.get('content', '')
    hl_fact_fields = [f for f in doc if is_fact_tax_hl_field(f)]
    ent_index = index_ent_spans(doc)
    logger.debug('Found %s entity spans in doc' % len(ent_index))
    result = [{
        'fact_field': hl_span['field'],
        'value': hl_span['value'],
        **extract_content(full_content, hl_span['span'], ent_index, cfg)
    }
              for hl_span in gen_hl_spans(doc, hl_fact_fields)]
    # for field in hl_fact_fields:
    #     for hl_val in doc[field]:
    #         items = hl_val.split('|')
    #         item, hls = items[0], items[1:]
    #         for hl in hls:
    #             beg, end = hl.split('-')
    #             result.append({
    #                 'fact_field': field,
    #                 'value': item,
    #                 'content': full_content[int(beg):int(end)+1]
    #             })
    return result
