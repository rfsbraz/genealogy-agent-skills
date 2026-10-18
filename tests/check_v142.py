#!/usr/bin/env python3
"""Display/provenance failure regressions; no claim about recognition accuracy."""
import copy
import hashlib
import json
from pathlib import Path
import tempfile
import unittest
from PIL import Image, ImageDraw
from check_v141 import MODULE, inputs, reports


def payload(path, manifest, method):
    return json.loads((path/'packets'/manifest['packets'][method]['inputs']).read_text())


class DisplayPacketChecks(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.p=Path(self.temp.name)
        self.spec=inputs(self.p)

    def tearDown(self):
        self.temp.cleanup()

    def method_reports(self,manifest):
        rows=reports()
        for row in rows:
            row['source_id']=manifest['source_id'];row['packet_id']=manifest['packet_id']
            if row['method_id']=='B':
                region=manifest['review_regions'][0]
                row['spans'][0]['method_product']['target_location']={**{k:region[k] for k in ('source_id','page','bbox_original')},'preceding_anchor':'line start in fixture'}
            asset=manifest['packets'][row['method_id']]['assets'][0]
            row['inputs_used']=[{k:asset[k] for k in ('asset_id','source_id','page')}]
            row['inputs_used'][0]['view_id']=asset['views'][0]['view_id']
        return rows

    def build(self):
        return MODULE.build(self.spec,self.p,self.p/'packets')

    def test_small_target_has_premade_enlarged_view_and_private_workdir(self):
        m=self.build();a=payload(self.p,m,'A')['assets'][0]
        enlarged=[v for v in a['views'] if v['kind']=='enlarged']
        self.assertTrue(enlarged)
        self.assertEqual(enlarged[0]['dimensions'],[1200,240])
        self.assertEqual(enlarged[0]['transform']['scale'],[8,8])
        self.assertEqual(m['preflight']['status'],'not_reviewed')
        self.assertTrue((self.p/'packets'/m['packets']['A']['prompt']).parent.joinpath('work').is_dir())

    def test_original_bytes_and_transform_lineage_are_preserved(self):
        before=(self.p/'target.png').read_bytes();m=self.build();a=payload(self.p,m,'A')['assets'][0]
        folder=(self.p/'packets'/m['packets']['A']['prompt']).parent
        self.assertEqual((folder/a['original_file']).read_bytes(),before)
        self.assertEqual((self.p/'target.png').read_bytes(),before)
        self.assertEqual(a['original_sha256'],hashlib.sha256(before).hexdigest())
        for view in a['views']:
            self.assertEqual(hashlib.sha256((folder/view['file']).read_bytes()).hexdigest(),view['sha256'])
            self.assertEqual(view['source_bbox_original'],[0,0,150,30])

    def test_equal_coordinates_on_different_pages_remain_distinct(self):
        t=self.spec['targets'][0];sample=t['same_hand_samples'][0]
        second=copy.deepcopy(sample);second['page']=9
        t['same_hand_samples'].append(second)
        m=self.build();b=payload(self.p,m,'B');assets=[a for a in b['assets'] if a['role']=='exemplar']
        self.assertEqual([a['page'] for a in assets],[2,9])
        self.assertEqual(len({a['asset_id'] for a in assets}),2)
        self.assertEqual(len(b['targets'][0]['same_hand_samples']),2)

    def test_sample_missing_own_page_is_rejected_before_output(self):
        del self.spec['targets'][0]['same_hand_samples'][0]['page']
        with self.assertRaises((ValueError,KeyError)):self.build()
        self.assertFalse((self.p/'packets').exists())

    def test_legacy_sample_paths_fail_with_migration_message(self):
        self.spec['targets'][0]['same_hand_images']=['same.png']
        with self.assertRaisesRegex(ValueError,'page-qualified same_hand_samples'):self.build()

    def test_context_method_has_target_line_and_page_views(self):
        m=self.build();d=payload(self.p,m,'D')
        self.assertEqual({a['role'] for a in d['assets']},{'target','line','context'})
        for a in d['assets']:
            self.assertIn('original',{v['kind'] for v in a['views']})
            self.assertIn('overview' if a['role']=='context' else 'enlarged',{v['kind'] for v in a['views']})

    def test_wide_line_tiles_cover_source_with_overlap_and_coordinates(self):
        t=self.spec['targets'][0]
        for name in ('line','page'):Image.new('RGB',(2000,30),'white').save(self.p/(name+'.png'))
        t['line_bbox_original']=t['context_bbox_original']=[0,0,2000,30]
        self.spec['pages'][0]['sha256']=hashlib.sha256((self.p/'page.png').read_bytes()).hexdigest()
        m=self.build();line=next(a for a in payload(self.p,m,'C')['assets'] if a['role']=='line')
        views=[v for v in line['views'] if v['kind']=='enlarged']
        self.assertGreater(len(views),1)
        self.assertEqual(views[0]['source_bbox_original'][0],0)
        self.assertEqual(views[-1]['source_bbox_original'][2],2000)
        for i,v in enumerate(views):
            self.assertLessEqual(max(v['dimensions']),1600)
            if i:self.assertLess(v['source_bbox_original'][0],views[i-1]['source_bbox_original'][2])

    def test_contrast_views_are_rejected(self):
        self.spec['display']={'contrast':True}
        with self.assertRaisesRegex(ValueError,'Contrast views are disabled'):self.build()

    def test_mismatched_dimensions_and_outside_target_are_rejected(self):
        self.spec['targets'][0]['bbox_original']=[0,0,149,30]
        with self.assertRaisesRegex(ValueError,'dimensions differ'):self.build()
        self.spec=inputs(self.p);self.spec['targets'][0]['bbox_original']=[10,0,160,30]
        with self.assertRaisesRegex(ValueError,'contained'):self.build()

    def test_sequence_candidate_never_clears_letter_gate_by_agreement(self):
        m=self.build();r=self.method_reports(m);c=r[2]['spans'][0]['method_product']
        c.update(raw_line_output='fluent candidate',character_audit=[{'group':'ending','verdict':'uncertain'}])
        r[0]['spans'][0]['method_product']['feature_inventory']=[{'feature':'ending contradicts C'}]
        result=MODULE.summarize(m,r)['agreement']['R1']
        self.assertEqual(result['sequence_check']['status'],'coordinator_letter_review_required')
        self.assertFalse(result['sequence_check']['confidence_promotion_allowed_by_summary'])
        self.assertEqual(result['confidence'],'not_computed')
        self.assertIn('contradicts C',str(result['sequence_check']['local_feature_evidence']))

    def test_sequence_reading_requires_raw_output_and_character_audit(self):
        m=self.build();r=self.method_reports(m)
        with self.assertRaisesRegex(ValueError,'raw_line_output'):MODULE.summarize(m,r)
        r[2]['spans'][0]['method_product']['raw_line_output']='first read'
        with self.assertRaisesRegex(ValueError,'character_audit'):MODULE.summarize(m,r)

    def test_same_page_sample_id_cannot_refer_to_different_crops(self):
        t=self.spec['targets'][0];duplicate=copy.deepcopy(t['same_hand_samples'][0])
        duplicate['bbox_original']=[1,0,151,30];t['same_hand_samples'].append(duplicate)
        with self.assertRaisesRegex(ValueError,'conflicting crops'):self.build()

    def test_corrupt_image_stops_preparation(self):
        (self.p/'target.png').write_bytes(b'not an image')
        with self.assertRaises(OSError):self.build()
        self.assertFalse((self.p/'packets').exists())

    def test_no_exemplars_keeps_method_b_target_and_honest_abstention_path(self):
        self.spec['targets'][0]['same_hand_samples']=[];m=self.build();b=payload(self.p,m,'B')
        self.assertEqual(b['targets'][0]['same_hand_samples'],[])
        self.assertEqual([a['role'] for a in b['assets']],['target','line'])


    def test_transparent_black_ink_remains_visible_on_documented_white(self):
        image=Image.new('RGBA',(150,30),(0,0,0,0))
        ImageDraw.Draw(image).rectangle((10,10,30,20),fill=(0,0,0,255));image.save(self.p/'target.png')
        image.save(self.p/'page.png');image.save(self.p/'line.png')
        self.spec['pages'][0]['sha256']=hashlib.sha256((self.p/'page.png').read_bytes()).hexdigest()
        m=self.build();a=payload(self.p,m,'A')['assets'][0]
        v=next(v for v in a['views'] if v['kind']=='enlarged')
        folder=(self.p/'packets'/m['packets']['A']['prompt']).parent
        with Image.open(folder/v['file']) as rendered:
            self.assertEqual(rendered.getpixel((0,0)),(255,255,255))
            self.assertEqual(rendered.getpixel((100,100)),(0,0,0))
        self.assertEqual(v['transform']['display_background'],'#ffffff')

    def test_whitespace_does_not_count_as_literal_agreement(self):
        m=self.build();rows=self.method_reports(m)
        for row in rows:row['spans'][0]['reading']='  '
        out=MODULE.summarize(m,rows)['agreement']['R1']
        self.assertEqual(out['candidate_groups'],[])
        self.assertEqual(out['methods_without_literal'],list('ABCD'))
        self.assertEqual(out['sequence_check']['status'],'no_sequence_candidate')

    def test_report_from_another_source_or_page_is_rejected(self):
        m=self.build();rows=self.method_reports(m)
        rows[0]['source_id']='UNRELATED-SOURCE'
        with self.assertRaisesRegex(ValueError,'source_id'):MODULE.summarize(m,rows)
        rows=self.method_reports(m);rows[0]['inputs_used'][0]['page']=99
        with self.assertRaisesRegex(ValueError,'source/page/asset'):MODULE.summarize(m,rows)
        rows=self.method_reports(m);rows[0]['inputs_used'][0]['view_id']='another-view'
        with self.assertRaisesRegex(ValueError,'view_id'):MODULE.summarize(m,rows)

    def test_malformed_input_returns_json_error_in_cli(self):
        import subprocess,sys
        script=Path(MODULE.__file__);bad=self.p/'bad.json'
        bad.write_text(json.dumps({'source_id':'S','targets':[None]}))
        process=subprocess.run([sys.executable,str(script),'build',str(bad),'--out',str(self.p/'packets')],capture_output=True,text=True)
        self.assertEqual(process.returncode,2)
        self.assertIn('error',json.loads(process.stderr))
        self.assertNotIn('Traceback',process.stderr)

    def test_malformed_report_members_fail_cleanly(self):
        m=self.build();rows=self.method_reports(m)
        rows[0]['spans']=[None]
        with self.assertRaisesRegex(ValueError,'spans'):MODULE.summarize(m,rows)
        rows=self.method_reports(m);rows[0]['spans'][0]['method_product']='not an object'
        with self.assertRaisesRegex(ValueError,'method_product'):MODULE.summarize(m,rows)


if __name__=='__main__':unittest.main()
