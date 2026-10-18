"""Check GPS review records, not historical truth. Python standard library only."""
import hashlib
import json
from datetime import date
from pathlib import Path

ASSETS = Path(__file__).resolve().parents[1] / 'assets'
ELEMENTS = ('research', 'citations', 'analysis', 'conflicts', 'writing')


def evidence_digest(case):
    """Conservative case-wide evidence fingerprint; excludes operational metadata.

    Review records are excluded to allow multiple reviews of one evidence snapshot.
    Any change to evidence, identity links, questions or conclusion text/status
    invalidates reviews. Checkpoint/task/mail changes alone do not.
    """
    names = ('questions', 'persons', 'mentions', 'relationships', 'events', 'places',
             'sources', 'citations', 'observations', 'hypotheses', 'searches')
    payload = {name: case.get(name, []) for name in names}
    payload['case_id'] = case.get('case_id')
    payload['goal'] = case.get('goal')
    payload['conclusions'] = [
        {k: v for k, v in c.items() if k not in ('gps_review', 'legacy_assessment')}
        for c in case.get('conclusions', [])
    ]
    raw = json.dumps(payload, sort_keys=True, ensure_ascii=False, separators=(',', ':'))
    return hashlib.sha256(raw.encode('utf-8')).hexdigest()


def validate_reviews(case, shape_checker, required=True):
    schema = json.loads((ASSETS / 'gps-review.schema.json').read_text(encoding='utf-8'))
    tables = {name: {row['id']: row for row in case[name]}
              for name in ('sources', 'citations', 'observations', 'searches', 'hypotheses', 'conclusions')}
    digest = evidence_digest(case)
    errors = []
    for conclusion in case['conclusions']:
        cid = conclusion['id']
        review = conclusion.get('gps_review')
        final = conclusion['status'] in ('supported', 'rejected')
        if review is None:
            if required and final:
                errors.append(f'{cid}: GPS review required before {conclusion["status"]}')
            continue
        shape = shape_checker(review, schema, schema, f'{cid}.gps_review')
        if shape:
            errors.extend(shape)
            continue
        ready = review['decision'] == 'ready'
        if final and not ready:
            errors.append(f'{cid}: {conclusion["status"]} requires a ready GPS review')
        if ready and review['evidence_digest'] != digest:
            errors.append(f'{cid}: GPS review is stale; reassess changed evidence')
        try:
            date.fromisoformat(review['reviewed_on'])
        except ValueError:
            errors.append(f'{cid}: GPS review date must be YYYY-MM-DD')

        def refs(values, collection, field):
            for value in values:
                if value not in tables[collection]:
                    errors.append(f'{cid}.{field}: missing {collection} ID {value}')

        for element in ELEMENTS:
            if ready and review[element]['status'] != 'met':
                errors.append(f'{cid}: GPS {element} remains open')
        research = review['research']
        refs(research['search_ids'], 'searches', 'research')
        for sid in research['search_ids']:
            search = tables['searches'].get(sid)
            if search and search['question_id'] != conclusion['question_id']:
                errors.append(f'{cid}: search {sid} belongs to another question')
        if ready and (not research['search_ids'] or not research['coverage']):
            errors.append(f'{cid}: research needs a search log and coverage assessment')
        for item in research['coverage']:
            refs(item['search_ids'], 'searches', 'coverage')
            if not set(item['search_ids']).issubset(research['search_ids']):
                errors.append(f'{cid}: coverage search absent from research search_ids')
            if ready and item['disposition'] == 'searched':
                if not item['search_ids']:
                    errors.append(f'{cid}: searched coverage needs search IDs')
                for sid in item['search_ids']:
                    search = tables['searches'].get(sid)
                    if search and search['outcome'] not in ('found', 'no_match'):
                        errors.append(f'{cid}: incomplete search {sid} cannot count as searched coverage')
            if ready and item['disposition'] == 'pending' and item['material']:
                errors.append(f'{cid}: material research avenue still pending')
        if ready and any(g['material'] for g in research['remaining_gaps']):
            errors.append(f'{cid}: material evidence gaps remain')

        cited = review['citations']['citation_ids']
        assessed = review['analysis']['observation_ids']
        refs(cited, 'citations', 'citations')
        refs(assessed, 'observations', 'analysis')
        refs(review['analysis']['hypothesis_ids'], 'hypotheses', 'analysis')
        if ready and not set(conclusion['observation_ids']).issubset(assessed):
            errors.append(f'{cid}: analysis omits conclusion observations')
        if ready and not assessed:
            errors.append(f'{cid}: ready assessment needs observations')
        for hid in review['analysis']['hypothesis_ids']:
            hypothesis = tables['hypotheses'].get(hid)
            if hypothesis and hypothesis['question_id'] != conclusion['question_id']:
                errors.append(f'{cid}: hypothesis {hid} belongs to another question')
            if ready and hypothesis:
                evidence = hypothesis.get('support_ids', []) + hypothesis.get('counterevidence_ids', [])
                if not set(evidence).issubset(assessed):
                    errors.append(f'{cid}: analysis omits hypothesis support/counterevidence')
        relevant_hypotheses = {h['id'] for h in case['hypotheses'] if h['question_id'] == conclusion['question_id']}
        if ready and not relevant_hypotheses.issubset(review['analysis']['hypothesis_ids']):
            errors.append(f'{cid}: analysis omits recorded alternatives for this question')
        source_ids = set()
        for oid in assessed:
            observation = tables['observations'].get(oid)
            if not observation:
                continue
            source_ids.add(observation['source_id'])
            if ready and observation.get('citation_id') not in cited:
                errors.append(f'{cid}: observation {oid} needs an audited citation')
        for citid in cited:
            citation = tables['citations'].get(citid)
            if citation and ready and not str(citation.get('text', '')).strip():
                errors.append(f'{cid}: citation {citid} needs full citation text, not only a locator')
        source_assessments = review['analysis']['source_assessments']
        refs([a['source_id'] for a in source_assessments], 'sources', 'source_assessments')
        if ready and not source_ids.issubset({a['source_id'] for a in source_assessments}):
            errors.append(f'{cid}: source/informant/independence assessments missing')
        information = review['analysis']['information_assessments']
        refs([a['observation_id'] for a in information], 'observations', 'information_assessments')
        if ready and set(assessed) != {a['observation_id'] for a in information}:
            errors.append(f'{cid}: assess information quality and relevance for each observation')
        for a in information:
            if ready and a['evidence_relevance'] == 'negative' and not a.get('absence_basis', '').strip():
                errors.append(f'{cid}: negative evidence needs record expectation, survival and search basis')
        for conflict in review['conflicts']['items']:
            refs(conflict['observation_ids'], 'observations', 'conflict')
            if ready and not set(conflict['observation_ids']).issubset(assessed):
                errors.append(f'{cid}: conflict observations omitted from analysis')
            if ready and conflict['material'] and conflict['status'] != 'resolved':
                errors.append(f'{cid}: material conflict remains unresolved')
        if ready:
            for depid in conclusion['depends_on']:
                dep = tables['conclusions'].get(depid)
                if dep and dep['status'] != 'supported':
                    errors.append(f'{cid}: dependency {depid} is not supported')
    return errors
