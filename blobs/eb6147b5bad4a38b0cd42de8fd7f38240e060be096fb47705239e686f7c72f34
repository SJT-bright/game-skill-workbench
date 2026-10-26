"""Evaluator/refusal unit checks only; acceptance still requires registered real-browser execution."""
from pathlib import Path
import copy, hashlib, json, tempfile, unittest
import audit_ui_contract as audit

class Refusal(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.project=Path(self.temp.name).resolve();self.picture=self.project/'same-run.png'
        self.picture.write_bytes(b'\x89PNG\r\n\x1a\n'+b'x'*6000)
        self.sha='a'*64
        self.contract={'schema':'ui_contract.v1','tolerance_px':1,'states':{'ready':{'modal':'result','slots':{
            'left':{'kind':'button','rect':{'x':10,'y':20,'width':100,'height':50}},
            'right':{'kind':'button','rect':{'x':130,'y':20,'width':100,'height':50}}},
            'tools':{'return':{'frames':['icon_return'],'click_return_page':'map'}}}}}
        def node(x):
            r={'x':x,'y':20,'width':100,'height':50}
            return {'id':str(x),'kind':'button','slot':'left' if x==10 else 'right','visible':True,'effective_opacity':255,'parent':{'world_rect':r},'sprites':[{'frame':'plate','world_rect':dict(r),'loaded':True,'texture_loaded':True,'visible':True,'effective_opacity':255}],'captions':[{'text':'ACT','world_rect':{'x':x+20,'y':30,'width':60,'height':20},'font_size':12,'visible':True,'effective_opacity':255}]}
        self.raw={'schema':'ui_contract_runtime.v1','producer':'real_browser_ui_contract','execution':{'variant':'final','base_native_tree_sha256':self.sha,'native_tree_sha256':self.sha,'renderer_identity':{k:True for k in audit.IDENTITY},'viewport':{'x':0,'y':0,'width':250,'height':400},'events':[{'id':'actual_click'}],'errors':[],'states':[{'id':'ready','modal':'result','screenshot':{'path':str(self.picture),'sha256':audit.sha(self.picture)},'buttons':[node(10),node(130)],'tools':{'return':{'frame':'icon_return','loaded':True,'texture_loaded':True,'visible':True,'effective_opacity':255,'world_rect':{'x':10,'y':100,'width':44,'height':44},'click_return_page':'map'}}}]}}
    def tearDown(self): self.temp.cleanup()
    def codes(self, raw=None): return {e['code'] for e in audit.validate(raw if raw is not None else self.raw,self.contract,self.sha,'final',self.project)}
    def test_evaluator_valid_geometry_only(self): self.assertEqual(self.codes(),set())
    def test_parent_only_resize_actual_sprite_still_overlaps(self):
        self.raw['execution']['states'][0]['buttons'][0]['sprites'][0]['world_rect']['width']=180
        self.assertTrue({'cross_slot_overlap','parent_overflow','slot_overflow'}<=self.codes())
    def test_dynamic_saved_caption_is_content(self):
        left=self.raw['execution']['states'][0]['buttons'][0];left['kind']='status';left['sprites']=[]
        self.contract['states']['ready']['slots']['left']['kind']='status';self.contract['states']['ready']['slots']['left']['require_sprite']=False
        left['captions'][0]['world_rect']={'x':10,'y':30,'width':220,'height':20}
        self.assertTrue({'cross_slot_overlap','slot_overflow'}<=self.codes())
    def test_fallback_label_tool_rejected(self):
        tool=self.raw['execution']['states'][0]['tools']['return'];tool.update(frame='',loaded=False,texture_loaded=False)
        self.assertIn('missing_tool_sprite',self.codes())
    def test_empty_and_missing_states_rejected(self):
        self.raw['execution']['states']=[];self.assertIn('missing_state',self.codes())
    def test_empty_slots_rejected(self):
        self.raw['execution']['states'][0]['buttons']=[];self.assertIn('empty_capture',self.codes())
    def test_hidden_entity_and_content_rejected(self):
        left=self.raw['execution']['states'][0]['buttons'][0];left['visible']=False;left['sprites'][0]['effective_opacity']=0
        self.assertIn('hidden',self.codes())
    def test_empty_sprites_and_captions_rejected(self):
        left=self.raw['execution']['states'][0]['buttons'][0];left['sprites']=[];left['captions']=[]
        self.assertTrue({'missing_sprite','missing_caption','empty_capture'}<=self.codes())
    def test_root_rect_cannot_hide_viewport_overflow(self):
        self.raw['execution']['states'][0]['buttons'][0]['sprites'][0]['world_rect']['x']=-20
        self.assertIn('viewport_overflow',self.codes())
    def test_unloaded_texture_and_wrong_frame_rejected(self):
        tool=self.raw['execution']['states'][0]['tools']['return'];tool.update(frame='other',texture_loaded=False)
        self.assertIn('missing_tool_sprite',self.codes())
    def test_nan_rect_rejected(self):
        self.raw['execution']['states'][0]['buttons'][0]['captions'][0]['world_rect']['width']=float('nan')
        self.assertIn('rect',self.codes())
    def test_old_hash_claim_and_mock_renderer_rejected(self):
        self.raw['execution']['native_tree_sha256']='b'*64;self.raw['execution']['renderer_identity']['renderer_original']=False
        self.assertTrue({'binding','renderer'}<=self.codes())
    def test_report_pass_ignored(self):
        self.raw['passed']=True;self.raw['execution']['states']=[];self.assertIn('missing_state',self.codes())
    def test_tolerance_bounded(self):
        self.contract['tolerance_px']=99;self.assertIn('contract',self.codes())
    def test_infinite_opacity_rejected(self):
        self.raw['execution']['states'][0]['buttons'][0]['effective_opacity']=float('inf')
        self.assertIn('hidden',self.codes())
    def test_unmapped_entity_cannot_be_silently_ignored(self):
        extra=copy.deepcopy(self.raw['execution']['states'][0]['buttons'][0]);extra['slot']='unmapped'
        self.raw['execution']['states'][0]['buttons'].append(extra)
        self.assertIn('undeclared_slot',self.codes())
    def test_unknown_registry_never_executes_report_command(self):
        native=self.project/'native';native.mkdir();contract=self.project/'contract.json';contract.write_text(json.dumps(self.contract))
        self.raw['command']=['touch',str(self.project/'should-not-exist')]
        with self.assertRaises(KeyError):audit.execute(self.project,native,contract,'unregistered-not-command',self.project/'out',['final'])
        self.assertFalse((self.project/'should-not-exist').exists())
    def test_calibration_cannot_mask_hidden_or_incomplete_capture(self):
        self.assertTrue(audit.detected_expected([{'code':'cross_slot_overlap'}],['cross_slot_overlap']))
        for code in ['hidden','missing_state','empty_capture','rect','missing_slot','missing_sprite','missing_caption','events','kind','font_size']:
            self.assertFalse(audit.detected_expected([{'code':'cross_slot_overlap'},{'code':code}],['cross_slot_overlap']),code)
    def test_empty_dependency_registry_refused(self):
        native=self.project/'native';native.mkdir();contract=self.project/'contract.json';contract.write_text(json.dumps(self.contract))
        runner=self.project/'runner.py';runner.write_text("raise RuntimeError('must never execute')")
        registry=self.project/'registry.json';registry.write_text(json.dumps({'test':{'project':str(self.project),'path':str(runner),'sha256':audit.sha(runner),'dependencies':{}}}))
        old=audit.REGISTRY;audit.REGISTRY=registry
        try:
            with self.assertRaisesRegex(ValueError,'nonempty'):audit.execute(self.project,native,contract,'test',self.project/'out',['final'])
        finally:audit.REGISTRY=old
    def test_changed_registered_runner_refused_before_execution(self):
        native=self.project/'native';native.mkdir();contract=self.project/'contract.json';contract.write_text(json.dumps(self.contract))
        runner=self.project/'runner.py';runner.write_text("raise RuntimeError('must never execute')")
        registry=self.project/'registry.json';registry.write_text(json.dumps({'test':{'project':str(self.project),'path':str(runner),'sha256':'0'*64,'dependencies':{str(contract):audit.sha(contract)}}}))
        old=audit.REGISTRY;audit.REGISTRY=registry
        try:
            with self.assertRaises(ValueError):audit.execute(self.project,native,contract,'test',self.project/'out',['final'])
        finally:audit.REGISTRY=old

if __name__=='__main__':unittest.main()
