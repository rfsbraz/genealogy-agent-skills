"""Source/crop, duplicate-input and enforced preflight regression checks. No OCR trial."""
import copy
import hashlib
import json
from pathlib import Path
import tempfile
import unittest
import subprocess
import sys
from unittest.mock import patch
from PIL import Image,ImageDraw
from check_v141 import MODULE, reports


def fixture(folder):
    for n in (1,2):
        im=Image.new('RGB',(400,160),'white');draw=ImageDraw.Draw(im)
        for x in range(400):draw.line((x,0,x,159),fill=(x%256,(x*3)%256,120+n))
        draw.text((20,40),'antecedent   target',fill='black');im.save(folder/f'page{n}.png')
    return {'schema_version':'1.2','source_id':'S','round':1,'script':'Latin',
        'pages':[{'source_id':'S','page':n,'image':f'page{n}.png','sha256':hashlib.sha256((folder/f'page{n}.png').read_bytes()).hexdigest(),'source_locator':f'Synthetic source page {n}'} for n in (1,2)],
        'targets':[{'region_id':'R1','page':1,'bbox_original':[80,40,180,70],
            'line_bbox_original':[20,30,380,80],'context_bbox_original':[0,0,400,160],
            'anchor_bbox_original':[20,40,80,70],
            'same_hand_samples':[{'source_id':'S','page':1,'sample_id':'E1','bbox_original':[200,90,330,120]}]}]}


class SourceAndGateChecks(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.p=Path(self.temp.name);self.spec=fixture(self.p)
        self.gate=MODULE.load_module('packet_review')
    def tearDown(self):self.temp.cleanup()
    def build(self):
        self.m=MODULE.build(self.spec,self.p,self.p/'packet');self.manifest=self.p/'packet/coordinator-manifest.json'
        return self.m
    def payload(self,method):return json.loads((self.p/'packet'/self.m['packets'][method]['inputs']).read_text())
    def review(self):
        record=json.loads((self.p/'packet/preflight-template.json').read_text())
        record.update(reviewed_by='unit-test fixture',reviewed_at='2026-10-17T12:00:00+00:00')
        for region in record['regions']:
            region.update(inspected_files=region['required_files'],source_page_correct=True,
                target_complete=True,anchor_correct=True,views_usable=True,
                source_quality='adequate_for_attempt',notes='Synthetic software fixture; not a human image review.')
        return record
    def pass_review(self):return self.gate.record_preflight(self.manifest,self.review())

    def test_high_depth_page_is_rejected_without_silent_clipping(self):
        image=Image.new('I;16',(400,160),1000)
        image.paste(60000,(200,0,400,160));image.save(self.p/'page16.tiff')
        self.spec['pages'][0].update(image='page16.tiff',sha256=hashlib.sha256((self.p/'page16.tiff').read_bytes()).hexdigest())
        with self.assertRaisesRegex(ValueError,'Unsupported source image mode'):self.build()
        self.assertFalse((self.p/'packet').exists())

    def test_mixed_page_identity_types_are_rejected_consistently(self):
        self.spec['targets'][0]['page']='1'
        with self.assertRaisesRegex(ValueError,'same page identity type'):self.build()

    def test_source_replacement_during_copy_cannot_keep_old_hash(self):
        import shutil
        original=shutil.copyfile
        def replace_before_copy(source,destination,*args,**kwargs):
            if Path(source)==self.p/'page1.png':
                Image.new('RGB',(400,160),'black').save(source)
            return original(source,destination,*args,**kwargs)
        with patch('shutil.copyfile',side_effect=replace_before_copy):
            with self.assertRaisesRegex(ValueError,'hash mismatch'):self.build()
        self.assertFalse((self.p/'packet').exists())

    def test_cli_build_review_dispatch_workflow(self):
        spec_path=self.p/'spec.json';spec_path.write_text(json.dumps(self.spec))
        script=str(Path(MODULE.__file__))
        def run(*args):
            result=subprocess.run([sys.executable,script,*map(str,args)],capture_output=True,text=True)
            self.assertEqual(result.returncode,0,result.stderr+result.stdout)
            return json.loads(result.stdout)
        run('build',spec_path,'--out',self.p/'packet')
        self.manifest=self.p/'packet/coordinator-manifest.json'
        record=self.p/'review.json';record.write_text(json.dumps(self.review()))
        self.assertEqual(run('record-preflight',self.manifest,record)['status'],'passed')
        self.assertEqual(run('dispatch',self.manifest)['status'],'ready')

    def test_original_pages_are_required(self):
        del self.spec['pages']
        with self.assertRaisesRegex(ValueError,'requires pages'):self.build()
        self.assertFalse((self.p/'packet').exists())

    def test_pinned_page_hash_is_checked(self):
        self.spec['pages'][0]['sha256']='0'*64
        with self.assertRaisesRegex(ValueError,'hash mismatch'):self.build()
        self.assertFalse((self.p/'packet').exists())

    def test_shifted_same_size_crop_fails_pixel_comparison(self):
        with Image.open(self.p/'page1.png') as image:image.crop((81,40,181,70)).save(self.p/'wrong.png')
        self.spec['targets'][0]['target_image']='wrong.png'
        with self.assertRaisesRegex(ValueError,'pixels do not match'):self.build()

    def test_crop_from_wrong_page_is_rejected(self):
        with Image.open(self.p/'page2.png') as image:image.crop((80,40,180,70)).save(self.p/'wrong.png')
        self.spec['targets'][0]['target_image']='wrong.png'
        with self.assertRaisesRegex(ValueError,'pixels do not match'):self.build()

    def test_source_derived_pixels_and_hashes_match_actual_page(self):
        self.build();asset=self.payload('A')['assets'][0]
        folder=(self.p/'packet'/self.m['packets']['A']['prompt']).parent
        with Image.open(self.p/'page1.png') as page,Image.open(folder/asset['original_file']) as crop:
            self.assertEqual(page.crop((80,40,180,70)).convert('RGBA').tobytes(),crop.convert('RGBA').tobytes())
        self.assertEqual(asset['source_page_sha256'],self.spec['pages'][0]['sha256'])
        self.assertEqual(asset['crop_verification'],'derived_from_pinned_page')
        source=self.p/'packet'/self.m['sources'][0]['file']
        self.assertEqual(source.read_bytes(),(self.p/'page1.png').read_bytes())

    def test_crop_outside_page_is_rejected(self):
        self.spec['targets'][0]['context_bbox_original']=[0,0,401,160]
        with self.assertRaisesRegex(ValueError,'outside'):self.build()

    def test_preceding_anchor_is_required_and_cannot_follow_target(self):
        del self.spec['targets'][0]['anchor_bbox_original']
        with self.assertRaisesRegex(ValueError,'preceding-word'):self.build()
        self.spec['targets'][0]['anchor_bbox_original']=[180,40,210,70]
        with self.assertRaisesRegex(ValueError,'before the target'):self.build()

    def test_b_has_marked_position_and_neutral_preceding_word(self):
        self.build();b=self.payload('B');t=b['targets'][0]
        self.assertIsNotNone(t['anchor_asset'])
        line=next(a for a in b['assets'] if a['asset_id']==t['line_asset'])
        locator=next(v for v in line['views'] if v['view_id']==t['target_locator_view'])
        self.assertEqual(locator['target_bbox_in_line'],[60,10,160,40])
        self.assertEqual(locator['anchor_bbox_in_line'],[0,10,60,40])
        self.assertFalse(locator['transform']['letter_evidence'])

    def test_d_reuses_one_page_for_four_targets(self):
        for i in range(2,5):
            target=copy.deepcopy(self.spec['targets'][0]);target['region_id']=f'R{i}'
            target['bbox_original']=[80+i,40,180+i,70];self.spec['targets'].append(target)
        self.build();d=self.payload('D')
        self.assertEqual(len([a for a in d['assets'] if a['role']=='context']),1)
        self.assertEqual(len({t['context_asset'] for t in d['targets']}),1)

    def test_near_duplicate_samples_merge_without_losing_locations(self):
        samples=self.spec['targets'][0]['same_hand_samples']
        samples.append(dict(samples[0],sample_id='E2',bbox_original=[202,90,332,120]))
        self.build();b=self.payload('B');assets=[a for a in b['assets'] if a['role']=='exemplar']
        self.assertEqual(len(assets),1);self.assertEqual(len(assets[0]['aliases']),2)
        self.assertEqual(assets[0]['bbox_original'],[200,90,332,120])
        self.assertEqual([s['bbox_original'] for s in b['targets'][0]['same_hand_samples']],[[200,90,330,120],[202,90,332,120]])

    def test_identical_coordinates_on_different_pages_do_not_merge(self):
        sample=self.spec['targets'][0]['same_hand_samples'][0]
        self.spec['targets'][0]['same_hand_samples'].append(dict(sample,page=2))
        self.build();self.assertEqual(len([a for a in self.payload('B')['assets'] if a['role']=='exemplar']),2)

    def test_balanced_edge_tiles_avoid_near_complete_overlap(self):
        intervals=MODULE.load_module('image_views').intervals(1601)
        self.assertEqual(len(intervals),2)
        overlap=intervals[0][1]-intervals[1][0]
        self.assertLess(overlap/min(b-a for a,b in intervals),0.25)
        self.assertEqual(intervals[0][0],0);self.assertEqual(intervals[-1][1],1601)

    def test_no_contrast_variants_are_dispatched(self):
        self.build()
        for method in 'ABCD':
            for a in self.payload(method)['assets']:self.assertNotIn('contrast',{v['kind'] for v in a['views']})

    def test_dispatch_without_a_review_fails(self):
        self.build()
        with self.assertRaisesRegex(ValueError,'preflight first'):self.gate.dispatch(self.manifest)
        self.assertFalse((self.p/'packet/dispatch').exists())

    def test_missing_visual_check_is_not_a_pass(self):
        self.build();record=self.review();record['regions'][0]['inspected_files']=[]
        with self.assertRaisesRegex(ValueError,'Missing required'):self.gate.record_preflight(self.manifest,record)
        self.assertFalse((self.p/'packet/preflight.json').exists())

    def test_resolution_limit_records_a_block_and_stops_dispatch(self):
        self.build();record=self.review();record['regions'][0]['source_quality']='needs_better_source'
        result=self.gate.record_preflight(self.manifest,record);self.assertEqual(result['status'],'blocked')
        with self.assertRaisesRegex(ValueError,'Dispatch blocked'):self.gate.dispatch(self.manifest)

    def test_passed_review_releases_only_frozen_inputs_and_receipt(self):
        self.build();self.pass_review()
        folder=(self.p/'packet'/self.m['packets']['A']['prompt']).parent
        (folder/'peer-report.json').write_text('do not copy this')
        result=self.gate.dispatch(self.manifest);self.assertEqual(result['status'],'ready')
        self.assertEqual(len(result['tasks']),4)
        for task in result['tasks']:
            out=Path(task['prompt']).parent
            self.assertFalse((out/'peer-report.json').exists())
            self.assertFalse((out/'coordinator-manifest.json').exists())
            receipt=json.loads((out/'dispatch-receipt.json').read_text())
            self.assertEqual(receipt['method_id'],task['method_id'])
            self.assertEqual(receipt['packet_id'],self.m['packet_id'])

    def test_modifying_input_after_review_invalidates_dispatch(self):
        self.build();self.pass_review()
        path=self.p/'packet'/self.m['packets']['D']['inputs']
        path.write_text(path.read_text()+' ')
        with self.assertRaisesRegex(ValueError,'Packet changed'):self.gate.dispatch(self.manifest)

    def test_modifying_source_snapshot_invalidates_review(self):
        self.build();record=self.review()
        (self.p/'packet'/self.m['sources'][0]['file']).write_bytes(b'changed')
        with self.assertRaisesRegex(ValueError,'Packet changed'):self.gate.record_preflight(self.manifest,record)

    def test_stale_digest_and_duplicate_regions_fail(self):
        self.build();record=self.review();record['packet_digest']='bad'
        with self.assertRaisesRegex(ValueError,'Stale'):self.gate.record_preflight(self.manifest,record)
        record=self.review();record['regions'].append(copy.deepcopy(record['regions'][0]))
        with self.assertRaisesRegex(ValueError,'exactly once'):self.gate.record_preflight(self.manifest,record)

    def test_status_label_cannot_override_failed_checks(self):
        self.build();record=self.review();record['regions'][0]['target_complete']=False
        self.gate.record_preflight(self.manifest,record)
        receipt=self.p/'packet/preflight.json';saved=json.loads(receipt.read_text());saved['status']='passed';receipt.write_text(json.dumps(saved))
        with self.assertRaisesRegex(ValueError,'Dispatch blocked'):self.gate.dispatch(self.manifest)

    def test_preflight_cannot_be_overwritten(self):
        self.build();self.pass_review()
        with self.assertRaises(FileExistsError):self.pass_review()

    def test_wrong_target_location_from_b_is_rejected(self):
        self.build();row=reports()[1];row.update(packet_id=self.m['packet_id'],source_id='S')
        asset=self.m['packets']['B']['assets'][0]
        row['inputs_used']=[{**{k:asset[k] for k in ('asset_id','source_id','page')},'view_id':asset['views'][0]['view_id']}]
        row['spans'][0]['method_product']['target_location']={'source_id':'S','page':1,'bbox_original':[200,90,330,120],'preceding_anchor':'sample word'}
        with self.assertRaisesRegex(ValueError,'target_location'):MODULE.summarize(self.m,[row])

    def test_legacy_packets_cannot_pass_new_dispatch_gate(self):
        self.build();m=json.loads(self.manifest.read_text());m['schema_version']='1.1';self.manifest.write_text(json.dumps(m))
        with self.assertRaisesRegex(ValueError,'schema 1.2'):self.gate.record_preflight(self.manifest,self.review())


if __name__=='__main__':unittest.main()
