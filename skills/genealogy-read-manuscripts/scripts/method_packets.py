#!/usr/bin/env python3
"""Prepare four scoped reading packets; summarize agreement without confidence claims."""
import argparse
import hashlib
import importlib.util
import json
from pathlib import Path
import shutil
import sys
import tempfile
import unicodedata
import uuid

ROOT = Path(__file__).resolve().parents[1]
BRIEFS = {'A': 'stroke-analysis.md', 'B': 'same-hand.md',
          'C': 'line-recognition.md', 'D': 'context-decoding.md'}
PRODUCTS = {'A': 'feature_inventory', 'B': 'exemplar_matches',
            'C': 'line_transcription', 'D': 'context_constraints'}
EXECUTIONS = {'A': {'visual_feature_analysis'}, 'B': {'same_hand_comparison'},
              'C': {'vlm_line_reading', 'htr_engine'}, 'D': {'contextual_decoding'}}


FALLBACK = 'blind plus context double reading'


FALLBACK_LABEL = 'double reading in one context'
FALLBACK_HIGHEST_CONFIDENCE = 'tentative'


class PanelUnavailable(ValueError):
    """The four-method panel is invalid because readers did not run in separate fresh contexts."""
    reading_label = FALLBACK_LABEL
    highest_confidence = FALLBACK_HIGHEST_CONFIDENCE


def panel_unavailable(detail):
    return PanelUnavailable('The four-method panel cannot run: ' + detail + '. Do not compare these reports as four methods; '
                            'stop and use the ' + FALLBACK + ' instead (see SKILL.md). Label that result a '
                            + FALLBACK_LABEL + '; its highest confidence is ' + FALLBACK_HIGHEST_CONFIDENCE + '.')


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def load_module(name):
    spec = importlib.util.spec_from_file_location('manuscript_'+name, Path(__file__).with_name(name+'.py'))
    module = importlib.util.module_from_spec(spec); spec.loader.exec_module(module)
    return module


def records_for(target, source_id):
    if target.get('same_hand_images'):
        raise ValueError('Replace same_hand_images with page-qualified same_hand_samples; page identity cannot be inferred from parallel arrays.')
    rows = {}
    for role, image_key, box_key in (
        ('target','target_image','bbox_original'),
        ('line','line_image','line_bbox_original'),
        ('context','context_image','context_bbox_original')):
        rows[role] = {'role':role, 'source_id':source_id, 'page':target['page'],
            'sample_id':target['region_id']+'-'+role, 'image':target.get(image_key),
            'bbox_original':target[box_key]}
    samples = target.get('same_hand_samples', [])
    if not isinstance(samples, list) or any(not isinstance(sample,dict) for sample in samples):
        raise ValueError('same_hand_samples must be a list of page-qualified records.')
    rows['samples'] = [dict({k:sample[k] for k in ('source_id','page','sample_id','bbox_original')},image=sample.get('image'),role='exemplar') for sample in samples]
    return rows


CLUE_CERTAINTY=('certain','probable','uncertain')


def build(spec, base, out):
    """Prepare usable visual inputs with page-qualified provenance; no model execution."""
    if not isinstance(spec,dict):raise ValueError('Build input must be an object.')
    base, out = Path(base), Path(out)
    if spec.get('schema_version') not in (None,'1.2'):
        raise ValueError('Build input must use packet schema 1.2; register original pages and anchor bounds.')
    if out.exists():
        raise ValueError('Use a fresh output directory; never replace frozen packets.')
    if not isinstance(spec.get('source_id'), str) or not spec['source_id'].strip():
        raise ValueError('source_id required')
    targets = spec.get('targets', [])
    if not isinstance(targets,list) or not targets or any(not isinstance(t,dict) for t in targets) or any(not isinstance(t.get('region_id'),str) or not t['region_id'].strip() for t in targets) or len({t['region_id'] for t in targets}) != len(targets):
        raise ValueError('Supply nonempty targets with unique region IDs.')
    round_number = spec.get('round', 1)
    if not isinstance(round_number, int) or isinstance(round_number, bool) or round_number < 1:
        raise ValueError('round must be a positive integer')
    context = spec.get('verified_context', {})
    if not isinstance(context,dict):raise ValueError('verified_context must be an object.')
    if not isinstance(context.get('clues',[]),list):raise ValueError('clues must be a list.')
    if set(context) - {'language', 'period', 'genre', 'clues'}:
        raise ValueError('Unknown contextual fields; no expected readings or identities.')
    for clue in context.get('clues', []):
        if not isinstance(clue,dict):raise ValueError('Each clue must be an object.')
        if set(clue) != {'id', 'fact', 'provenance', 'independent_of_target', 'clue_certainty'}:
            raise ValueError('Clue needs id, fact, provenance, independent_of_target and clue_certainty.')
        if clue['clue_certainty'] not in CLUE_CERTAINTY:
            raise ValueError('clue_certainty must be one of: '+', '.join(CLUE_CERTAINTY)+'.')
        if clue['independent_of_target'] is not True or any(not isinstance(clue[k], str) or not clue[k].strip() for k in ('id','fact','provenance')):
            raise ValueError('Context clues need a non-circular, documented basis.')
    options = spec.get('display', {})
    if not isinstance(options,dict):raise ValueError('display must be an object.')
    if set(options)-{'contrast','margin'} or type(options.get('contrast',False)) is not bool:
        raise ValueError('display accepts only contrast: true/false and margin.')
    if options.get('contrast'):raise ValueError('Contrast views are disabled in reading packets; JPEG artefacts can mimic pen strokes.')
    margin=options.get('margin',0)
    if type(margin) not in (int,float) or not 0<=margin<=1:
        raise ValueError('display.margin must be a number from 0 to 1, a fraction of each target and line box height.')
    warnings=['B will abstain on '+t['region_id']+': no same_hand_samples were supplied.' for t in targets if not t.get('same_hand_samples')]
    views = load_module('image_views')
    prepared = [records_for(t,spec['source_id']) for t in targets]
    out.parent.mkdir(parents=True,exist_ok=True)
    stage=Path(tempfile.mkdtemp(prefix=out.name+'.',dir=out.parent))
    manifest={'schema_version':'1.2','packet_id':uuid.uuid4().hex,'source_id':spec['source_id'],'round':round_number,
        'planned_methods':list(BRIEFS),'model_diversity_required':False,
        'context_requirement':'fresh for each method; same model permitted',
        'preflight':{'status':'not_reviewed','rule':'record-preflight and dispatch are required; build produces draft packets only.'},
        'packets':{},'review_regions':[]}
    try:
        source_tools=load_module('source_crops')
        sources=source_tools.SourcePages(spec.get('pages'),base,stage,views)
        identities={};all_samples=[]
        for t,records in zip(targets,prepared):
            target=records['target']['bbox_original']
            for role in ('line','context'):
                outer=records[role]['bbox_original']
                if not (outer[0]<=target[0]<target[2]<=outer[2] and outer[1]<=target[1]<target[3]<=outer[3]):
                    raise ValueError('Target must be contained in its line and context crop.')
            anchor=t.get('anchor_bbox_original')
            if anchor is None:
                if t.get('target_at_line_start') is not True:raise ValueError('Supply preceding-word anchor_bbox_original or explicitly confirm target_at_line_start.')
                records['anchor']=None
            else:
                if t.get('target_at_line_start'):raise ValueError('Choose a preceding anchor or line-start, not both.')
                line=records['line']['bbox_original']
                if not isinstance(anchor,list) or len(anchor)!=4 or any(type(x) is not int for x in anchor) or not (line[0]<=anchor[0]<anchor[2]<=target[0] and line[1]<=anchor[1]<anchor[3]<=line[3]):
                    raise ValueError('Preceding anchor must lie inside the line and before the target.')
                records['anchor']={'role':'anchor','source_id':spec['source_id'],'page':t['page'],
                    'sample_id':t['region_id']+'-anchor','bbox_original':anchor,'image':t.get('anchor_image')}
            for role in ('target','line','context','anchor'):
                if records[role] is not None:records[role]=sources.crop(records[role])
            if records['anchor'] is not None and (inked:=sources.inked_edges(records['anchor'])):
                raise ValueError('Preceding anchor must sit on a word boundary: ink runs across its '+' and '.join(inked)+' edge, so the box starts or ends inside a word.')
            if margin:
                for role in ('target','line'):records[role]=sources.pad(records[role],margin)
            for sample in records['samples']:
                key=(sample['source_id'],str(sample['page']),sample['sample_id'])
                if key in identities and identities[key]!=sample['bbox_original']:raise ValueError('A page-qualified sample ID refers to conflicting crops.')
                identities[key]=sample['bbox_original']
                verified=sources.crop(sample);all_samples.append(verified)
        groups=source_tools.coalesce_samples(all_samples,sources)
        group_by_alias={}
        for group in groups:
            unique={ (a['source_id'],str(a['page']),a['sample_id'],tuple(a['bbox_original'])):a for a in group['aliases'] }
            group['aliases']=list(unique.values())
            for key in unique:group_by_alias[key]=group
        manifest['sources']=list(sources.pages.values())
        review_by_region={}
        for t,records in zip(targets,prepared):
            source=sources.pages[source_tools.page_key(spec['source_id'],t['page'])]
            review_by_region[t['region_id']]={'region_id':t['region_id'],'source_id':spec['source_id'],'page':t['page'],
                'bbox_original':t['bbox_original'],'target_at_line_start':t.get('target_at_line_start') is True,
                'required_files':[source['file']]}
        for method,brief in BRIEFS.items():
            job='task-'+uuid.uuid4().hex[:12];folder=stage/'draft'/job;folder.mkdir(parents=True)
            (folder/'work').mkdir()
            assets={}
            def asset(record):
                # IDs name references, not duplicate image payloads. Preserve source/page distinction.
                key=(record['source_id'],str(record['page']),record['role'],tuple(record['bbox_original']),record['source_page_sha256'])
                if key not in assets:
                    asset_id='asset-'+str(len(assets)+1).zfill(3)
                    assets[key]=views.make_views(record,stage,folder,asset_id)
                return assets[key]
            rows=[]
            for index,(t,records) in enumerate(zip(targets,prepared),1):
                row={k:t[k] for k in ('region_id','page','bbox_original')}
                row['source_id']=spec['source_id'];row['target_asset']=asset(records['target'])['asset_id']
                if method=='A':
                    detail=asset(records['target'])
                    review_by_region[t['region_id']]['required_files'] += [(folder/v['file']).relative_to(stage).as_posix() for v in detail['views']]
                if method in ('B','C','D'):row['line_asset']=asset(records['line'])['asset_id']
                if method=='B':
                    row['target_at_line_start']=t.get('target_at_line_start',False)
                    row['anchor_asset']=asset(records['anchor'])['asset_id'] if records['anchor'] else None
                    row['anchor_bbox_original']=t.get('anchor_bbox_original')
                    location=views.mark_location(asset(records['line']),t['bbox_original'],t.get('anchor_bbox_original'),folder,index)
                    row['target_locator_view']=location['view_id']
                    review_by_region[t['region_id']]['required_files'].append((folder/location['file']).relative_to(stage).as_posix())
                    refs={}
                    for sample in records['samples']:
                        key=(sample['source_id'],str(sample['page']),sample['sample_id'],tuple(sample['bbox_original']))
                        image=asset(group_by_alias[key])
                        refs[key]=dict({k:sample[k] for k in ('source_id','page','sample_id','bbox_original')},asset_id=image['asset_id'])
                    row['same_hand_samples']=list(refs.values())
                if method=='D':row['context_asset']=asset(records['context'])['asset_id']
                rows.append(row)
            payload={'schema_version':'1.2','packet_id':manifest['packet_id'],'source_id':spec['source_id'],'method_id':method,
                'round':round_number,'targets':rows,'assets':list(assets.values()),
                'script':spec.get('script','unspecified'),'private_work_directory':'work'}
            if method=='D':payload['verified_context']=context
            common=(ROOT/'references/common-contract.md').read_text(encoding='utf-8')
            method_text=(ROOT/'references'/brief).read_text(encoding='utf-8')
            prompt=common+'\n'+method_text+'\n## Supplied inputs\n\nRead inputs.json and dispatch-receipt.json. Use only this task folder. Locator outlines are orientation aids, not ink evidence.\n'
            (folder/'prompt.md').write_text(prompt,encoding='utf-8')
            (folder/'inputs.json').write_text(json.dumps(payload,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
            manifest['packets'][method]={'prompt':'draft/'+job+'/prompt.md','inputs':'draft/'+job+'/inputs.json',
                'assets':list(assets.values()),'regions':[t['region_id'] for t in targets],
                'context_id':None,'execution_status':'not_started'}
        manifest['review_regions']=list(review_by_region.values())
        manifest['warnings']=warnings
        manifest['inventory']={p.relative_to(stage).as_posix():digest(p) for p in sorted(stage.rglob('*')) if p.is_file()}
        (stage/'coordinator-manifest.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
        review=load_module('packet_review')
        (stage/'preflight-template.json').write_text(json.dumps(review.template(stage,manifest),indent=2)+'\n',encoding='utf-8')
        review.start_log(stage,manifest)
        stage.rename(out)
    finally:
        if stage.exists():shutil.rmtree(stage)
    return manifest


def build_summary(out, manifest):
    """Short build result for an agent's context. The manifest file on disk stays complete."""
    out=Path(out)
    return {'status':'built','out':str(out),'manifest':str(out/'coordinator-manifest.json'),
        'preflight_template':str(out/'preflight-template.json'),'packet_id':manifest['packet_id'],
        'packet_digest':load_module('packet_review').fingerprint(out,manifest),
        'counts':{'regions':len(manifest['review_regions']),'methods':len(manifest['packets']),
                  'assets':sum(len(p['assets']) for p in manifest['packets'].values()),'files':len(manifest['inventory'])},
        'warnings':manifest['warnings'],
        'next':'Inspect the views, fill preflight-template.json, then run record-preflight. Use --verbose for the full manifest.'}


def validate_inputs(manifest, report, method):
    strict=manifest.get('schema_version') in ('1.1','1.2')
    if manifest.get('schema_version')=='1.2' and report.get('packet_id')!=manifest.get('packet_id'):raise ValueError('Report packet_id does not match the current packet set.')
    claimed=report.get('source_id')
    if (strict and claimed!=manifest['source_id']) or (claimed is not None and claimed!=manifest['source_id']):
        raise ValueError('Report source_id does not match the packet source.')
    used=report.get('inputs_used',[])
    if not isinstance(used,list) or any(not isinstance(item,dict) for item in used):
        raise ValueError('inputs_used must be a list of asset/view references.')
    assets={a['asset_id']:a for a in manifest['packets'][method].get('assets',[]) if 'asset_id' in a}
    if strict and report.get('status') in ('completed','partial') and not used:
        raise ValueError('Completed reading needs page-qualified inputs_used.')
    for item in used:
        if strict:
            asset=assets.get(item.get('asset_id'))
            if not asset or item.get('source_id')!=asset['source_id'] or item.get('page')!=asset['page']:
                raise ValueError('Report input source/page/asset does not match its assigned packet.')
            if item.get('view_id') not in {v['view_id'] for v in asset['views']}:
                raise ValueError('Report view_id does not belong to the supplied asset; log private derivatives separately.')
        elif item.get('source_id') not in (None,manifest['source_id']):
            raise ValueError('Legacy report input claims a different source; use page-qualified schema for cross-source exemplars.')


def sequence_check(region, reports):
    spans={m:next((s for s in r.get('spans',[]) if s['region_id']==region),{}) for m,r in reports.items()}
    candidate=spans.get('C',{}).get('reading') if reports.get('C',{}).get('status') in ('completed','partial') else None
    if not candidate or not candidate.strip():return {'status':'no_sequence_candidate'}
    return {'status':'coordinator_letter_review_required','candidate':candidate,
        'raw_line_output':spans['C'].get('method_product',{}).get('raw_line_output'),
        'self_audit':spans['C'].get('method_product',{}).get('character_audit',[]),
        'local_feature_evidence':spans.get('A',{}).get('method_product',{}).get('feature_inventory',[]),
        'same_hand_evidence':spans.get('B',{}).get('method_product',{}).get('exemplar_matches',[]),
        'confidence_promotion_allowed_by_summary':False,
        'rule':'Align consequential characters, including ending and boundaries, against A/B and source detail. Missing evidence is not agreement. Any unresolved material conflict blocks visually_supported; fluency and model confidence cannot clear this gate.'}


def summarize(manifest, reports):
    """Count literal agreement, never infer confidence or actual independence."""
    if not isinstance(manifest,dict):raise ValueError('Manifest must be an object.')
    if not isinstance(reports,list):raise ValueError('Reports must be a list.')
    if manifest.get('schema_version') not in (None,'1.0','1.1','1.2'):
        raise ValueError('Unsupported packet schema version')
    expected = manifest['planned_methods']
    if set(expected) != set(BRIEFS):
        raise ValueError('Manifest must plan the four methods A/B/C/D.')
    by_method = {}
    warnings = []
    for report in reports:
        if not isinstance(report,dict):raise ValueError('Each report must be an object.')
        method = report['method_id']
        if method not in expected or method in by_method:
            raise ValueError('Unknown or duplicate method; later rounds replace, never add votes.')
        if report.get('execution_kind') not in EXECUTIONS[method]:
            raise ValueError('Execution kind does not match assigned method ' + method)
        if report.get('status') not in ('completed','partial','abstained','blocked'):
            raise ValueError('Invalid method status')
        if report.get('round') != manifest['round']:
            raise ValueError('Summarize one round at a time; preserve earlier round summaries separately.')
        validate_inputs(manifest,report,method)
        spans = report.get('spans', [])
        if not isinstance(spans,list) or any(not isinstance(span,dict) for span in spans):raise ValueError('spans must be a list of objects.')
        region_ids = [s['region_id'] for s in spans]
        if len(region_ids) != len(set(region_ids)) or set(region_ids) - set(manifest['packets'][method]['regions']):
            raise ValueError('Duplicate or unknown region in report ' + method)
        if report['status'] == 'completed' and set(region_ids) != set(manifest['packets'][method]['regions']):
            raise ValueError('Completed report omits target regions.')
        for span in spans:
            if not isinstance(span.get('method_product',{}),dict):raise ValueError('method_product must be an object.')
            if span.get('reading') is not None and not isinstance(span['reading'], str):
                raise ValueError('Reading must be a literal string or null.')
            if isinstance(span.get('reading'),str) and span['reading'].strip() and not span.get('method_product', {}).get(PRODUCTS[method]):
                raise ValueError('Missing method-specific evidence product for ' + method)
            if isinstance(span.get('reading'),str) and span['reading'].strip() and method=='B' and manifest.get('schema_version')=='1.2':
                location=span.get('method_product',{}).get('target_location',{})
                expected_region=next(r for r in manifest['review_regions'] if r['region_id']==span['region_id'])
                if not isinstance(location,dict) or any(location.get(k)!=expected_region[k] for k in ('source_id','page','bbox_original')) or not isinstance(location.get('preceding_anchor'),str) or not location['preceding_anchor'].strip():
                    raise ValueError('B needs target_location matching the requested source/page/bounds and an observed preceding_anchor or line-start statement.')
            if isinstance(span.get('reading'),str) and span['reading'].strip() and method == 'C' and manifest.get('schema_version') in ('1.1','1.2'):
                product=span.get('method_product',{})
                if not product.get('raw_line_output') or not product.get('character_audit'):
                    raise ValueError('C must preserve raw_line_output and perform a character_audit against supplied detail views.')
            if isinstance(span.get('reading'),str) and span['reading'].strip() and report['execution_kind'] == 'htr_engine':
                recognizer = span.get('method_product', {}).get('recognizer', {})
                if any(not isinstance(recognizer.get(k), str) or not recognizer[k].strip() for k in ('tool','model','raw_output')):
                    raise ValueError('A claimed HTR run needs tool, model and raw_output metadata.')
        if report.get('context_isolation') != 'fresh' or report.get('context_id') in (None,'','unknown'):
            raise panel_unavailable('method ' + method + ' did not run in a documented separate fresh context')
        by_method[method] = report
    seen = {}
    for method, report in by_method.items():
        seen.setdefault(report['context_id'], []).append(method)
    shared = [', '.join(sorted(m)) for m in seen.values() if len(m) > 1]
    if shared:
        raise panel_unavailable('methods ' + '; '.join(shared) + ' report the same context ID')
    models = sorted({r.get('model_identity','host-default-unspecified') for r in reports})
    if len(models) <= 1:
        warnings.append('Shared/unspecified model: shared error modes remain possible; permitted configuration')
    regions = sorted({x for packet in manifest['packets'].values() for x in packet['regions']})
    agreement = {}
    for region in regions:
        groups = {}
        nonliteral = []
        for method in expected:
            report = by_method.get(method, {})
            span = next((s for s in report.get('spans', []) if s['region_id'] == region), {})
            reading = span.get('reading')
            if report.get('status') in ('completed','partial') and reading and reading.strip():
                literal = unicodedata.normalize('NFC', reading.strip())
                groups.setdefault(literal, []).append(method)
            else:
                nonliteral.append(method)
        agreement[region] = {'candidate_groups': [{'literal': k, 'methods': v} for k,v in groups.items()],
            'methods_without_literal': nonliteral, 'planned_method_count': 4,
            'confidence': 'not_computed', 'sequence_check': sequence_check(region,by_method), 'rule': 'Coordinator must evaluate pixels, products and conflicts; agreement is not probability.'}
    return {'source_id': manifest['source_id'], 'round': manifest['round'], 'planned_methods': expected,
        'reported_methods': sorted(by_method), 'missing_methods': sorted(set(expected)-set(by_method)),
        'reported_statuses': {m:r['status'] for m,r in by_method.items()}, 'model_identities': models,
        'warnings': warnings, 'agreement': agreement, 'limits': 'Self-reported metadata and structural checks do not authenticate context isolation, engine execution or evidence quality.'}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest='command',required=True)
    pack = sub.add_parser('build'); pack.add_argument('spec'); pack.add_argument('--out',required=True)
    pack.add_argument('--verbose',action='store_true',help='Print the full manifest instead of the short summary')
    rec = sub.add_parser('summarize'); rec.add_argument('manifest'); rec.add_argument('reports',nargs='+')
    pre=sub.add_parser('record-preflight');pre.add_argument('manifest');pre.add_argument('review')
    launch=sub.add_parser('dispatch');launch.add_argument('manifest')
    args = parser.parse_args()
    try:
        if args.command == 'build':
            path = Path(args.spec)
            result = build(json.loads(path.read_text(encoding='utf-8')),path.parent,args.out)
            if not args.verbose:result=build_summary(args.out,result)
        elif args.command == 'record-preflight':
            result=load_module('packet_review').record_preflight(args.manifest,json.loads(Path(args.review).read_text(encoding='utf-8')))
        elif args.command == 'dispatch':
            result=load_module('packet_review').dispatch(args.manifest)
        else:
            result = summarize(json.loads(Path(args.manifest).read_text(encoding='utf-8')),
                [json.loads(Path(p).read_text(encoding='utf-8')) for p in args.reports])
        print(json.dumps(result,ensure_ascii=False,indent=2))
        return 0
    except (OSError,ValueError,KeyError,TypeError) as exc:
        print(json.dumps({'error':str(exc)}),file=sys.stderr)
        return 2


if __name__ == '__main__':
    sys.exit(main())
