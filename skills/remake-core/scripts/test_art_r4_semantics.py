"""Synthetic regressions for art measurements; never a game acceptance receipt."""
import tempfile
import unittest
from pathlib import Path
from PIL import Image, ImageDraw
import audit_page_richness as A
from test_art_analysis_cache import AnalysisCache


def node(path, rect, **comps):
    return {'path':path,'name':path.rsplit('/',1)[-1],'rect':rect,'comps':comps,'opacity':1,'order':1}


class Semantics(unittest.TestCase):
    def test_external_icon_caption_is_not_spliced_but_overlay_is(self):
        b=node('Canvas/Icon',[.1,.3,.2,.1],button={'interactable':True},sprite={'frame':'img_gift'})
        t=node('Canvas/Icon/Caption',[.11,.396,.18,.03],sprite={'frame':'txt_gift'})
        self.assertTrue(any(x.startswith('spliced_button:') for x in A.one_piece_problems([b,t],[b])),
                        'unknown art is fail-closed even for an outside word')
        with tempfile.TemporaryDirectory() as tmp:
            icon=Path(tmp)/'icon.png';word=Path(tmp)/'word.png'
            for path in (icon,word):
                im=Image.new('RGBA',(40,40),(0,0,0,0));ImageDraw.Draw(im).ellipse((5,5,35,35),fill='white');im.save(path)
            old_art,old_word=A.SPRITE_ART_SOURCES,A.GENERATED_TEXT_SOURCES
            A.SPRITE_ART_SOURCES={'img_gift':{'path':icon,'rect':None},'txt_gift':{'path':word,'rect':None}}
            A.GENERATED_TEXT_SOURCES={'txt_gift':{'path':word,'rect':None}}
            try:
                self.assertEqual(A.one_piece_problems([b,t],[b]),[])
                t['rect'][1]=.33
                self.assertTrue(any(x.startswith('spliced_button:') for x in A.one_piece_problems([b,t],[b])))
                t['rect'][1]=.396
                Image.new('RGBA',(40,40),'white').save(icon)
                self.assertTrue(any(x.startswith('spliced_button:') for x in A.one_piece_problems([b,t],[b])),
                                'a filled tile is not proven standalone art')
            finally:A.SPRITE_ART_SOURCES,A.GENERATED_TEXT_SOURCES=old_art,old_word

    def test_clickable_claim_link_is_not_another_buttons_caption(self):
        b=node('Canvas/BtnDouble',[.2,.4,.6,.08],button={'interactable':True},sprite={'frame':'btn_double'})
        claim=node('Canvas/LinkClaim',[.3,.51,.4,.05],button={'interactable':True})
        t=node('Canvas/LinkClaim/Art',[.31,.51,.38,.04],sprite={'frame':'txt_claim'})
        self.assertFalse(any(x.startswith('action_caption:') for x in A.overlap_problems([b,claim,t],[b,claim],[])))
        claim['comps'].pop('button')
        self.assertTrue(any(x.startswith('action_caption:') for x in A.overlap_problems([b,claim,t],[b],[])))

    def test_two_stepper_channels_and_disabled_missing_endpoint(self):
        ns=[node('Canvas/Music',[.4,.2,.2,.03],sprite={'frame':'txt_music'}),node('Canvas/Sound',[.4,.5,.2,.03],sprite={'frame':'txt_sound'})]
        for channel,y in [('music',.24),('sfx',.54)]:
            for sign,x in [('Minus',.2),('Plus',.7)]:
                ns.append(node('Canvas/Btn'+sign+channel,[x,y,.1,.04],button={'interactable':True,'enabled':True}))
        ns[-1]['comps']['button']['interactable']=False
        self.assertEqual(A.sound_stepper_channels(ns),{'music','sfx'},'grey endpoint is visible')
        ns += [node('Canvas/Close',[.8,.1,.1,.04],button={'interactable':True}),
               node('Canvas/MusicValue',[.4,.24,.2,.04],label={'string':'70%'}),
               node('Canvas/SoundValue',[.4,.54,.2,.04],label={'string':'90%'})]
        d={'nodes':ns,'kind':'popup','purpose':'settings_sound','_file':'/tmp/synthetic-only.json'}
        self.assertFalse(any(x.startswith('settings_sound:') for x in A.check(d,None)[0]))
        plus=ns[5]
        plus['comps']['button']['enabled']=False
        self.assertTrue(any(x.startswith('settings_sound:') for x in A.check(d,None)[0]))
        # Adding an unrelated close/help button cannot replace the missing audio endpoint.
        ns.append(node('Canvas/Help',[.8,.16,.1,.04],button={'interactable':True}))
        self.assertTrue(any(x.startswith('settings_sound:') for x in A.check(d,None)[0]))
        self.assertEqual(A.sound_stepper_channels(ns),{'music'})

    def test_resource_hud_needs_real_icon_and_number(self):
        t=node('Canvas/Home/coins/Word',[.1,.1,.2,.03],sprite={'frame':'txt_coins'})
        icon=node('Canvas/Home/coins/Value/Icon',[.1,.14,.03,.03],sprite={'frame':'img_coin'})
        val=node('Canvas/Home/coins/Value/Number/G0',[.2,.14,.03,.03],sprite={'frame':'digit_0'})
        self.assertTrue(A.resource_hud_word(t,[t,icon,val]))
        self.assertFalse(A.resource_hud_word(t,[t,icon]))
        self.assertFalse(A.resource_hud_word(t,[t,val]))
        t['comps']['sprite']['frame']='txt_coins_value'
        self.assertTrue(A.resource_hud_word(t,[t,icon,val]),'frame suffix does not remove actual HUD structure')
        t['comps']['sprite']['frame']='txt_coins_castle'
        self.assertFalse(A.resource_hud_word(t,[t,icon,val]),'a game title is not an amount label')
        t['comps']['sprite']['frame']='txt_coins_value'
        unrelated=dict(val,path='Canvas/Home/other/Value/Number/G0')
        self.assertFalse(A.resource_hud_word(t,[t,icon,unrelated]),'a number outside the icon row cannot complete it')
        undecodable=dict(val,comps={'sprite':{'frame':'unknown_glyph'}})
        self.assertFalse(A.resource_hud_word(t,[t,icon,undecodable]))

    def test_bright_face_mask_reads_screen_not_source_or_outline(self):
        with tempfile.TemporaryDirectory() as tmp:
            source=Path(tmp)/'text.png'
            im=Image.new('RGBA',(100,40),(0,0,0,0));d=ImageDraw.Draw(im)
            d.rectangle((15,5,85,35),fill=(100,45,130,255));d.rectangle((20,10,80,30),fill=(255,255,255,255));im.save(source)
            old=A.GENERATED_TEXT_SOURCES
            A.GENERATED_TEXT_SOURCES={'txt_example':{'path':source,'rect':None}}
            try:
                n=node('Canvas/Text',[0,0,1,1],sprite={'frame':'txt_example'})
                shown=Image.new('RGB',im.size,(248,244,250));shown.paste(im,mask=im.getchannel('A'))
                self.assertEqual(A.generated_face_ink_class(shown,n,Image),'neutral')
                shot=Path(tmp)/'shown.png';shown.save(shot)
                same_white=[node('Canvas/Text'+str(i),[0,0,1,1],sprite={'frame':'txt_example'}) for i in range(3)]
                issues=A.colour_problems({'_file':str(Path(tmp)/'dump.json'),'screenshot':'shown.png'},same_white,Image)
                self.assertTrue(any(x.startswith('uniform_text_colour:') and 'white/neutral' in x for x in issues))
                ImageDraw.Draw(shown).rectangle((20,10,80,30),fill=(240,170,40))
                self.assertEqual(A.generated_face_ink_class(shown,n,Image),'hue30','must measure actual screenshot')
            finally:A.GENERATED_TEXT_SOURCES=old

    def test_large_illustration_is_not_a_popup_panel(self):
        panel=node('Canvas/Popup/Panel',[.1,.2,.8,.6],sprite={'frame':'panel','sliced':True})
        disc=node('Canvas/Popup/Panel/Body/WheelPrizes/WheelDisc',[.2,.35,.6,.3],sprite={'frame':'img_wheel_disc','sliced':False})
        d={'nodes':[panel], 'kind':'popup', 'purpose':'reward', '_file':'/tmp/synthetic-only.json'}
        self.assertTrue(any(x.startswith('plain_popup:') for x in A.check(d,None)[0]))
        d['nodes'].append(disc)
        self.assertFalse(any(x.startswith('plain_popup:') for x in A.check(d,None)[0]))

    def test_real_resource_hud_is_not_title_but_unaccompanied_word_still_is(self):
        hero=node('Canvas/Home/Hero',[.1,.1,.8,.3],sprite={'frame':'hero'})
        t=node('Canvas/Home/coins/Word',[.2,.12,.2,.03],sprite={'frame':'txt_coins'})
        icon=node('Canvas/Home/coins/Value/Icon',[.2,.16,.03,.03],sprite={'frame':'img_coin'})
        val=node('Canvas/Home/coins/Value/Number/G0',[.3,.16,.03,.03],sprite={'frame':'digit_0'})
        d={'nodes':[hero,t,icon,val], 'kind':'home','purpose':'home','_file':'/tmp/synthetic-only.json'}
        self.assertFalse(any(x.startswith('typed_title:') for x in A.check(d,None)[0]))
        d['nodes']=[hero,t]
        self.assertTrue(any(x.startswith('typed_title:') for x in A.check(d,None)[0]))


class FrameDependencies(AnalysisCache):
    def test_bare_cocos_frame_is_identifier_and_assets_still_invalidate(self):
        self.document['nodes']=[node('Canvas/Original',[.1,.1,.1,.1],sprite={'frame':'wo4.png'})]
        self.dump.write_text(__import__('json').dumps(self.document))
        asset=self.write('assets/atlas.png','first asset bytes')
        before=self.key();self.assertIsNotNone(before)
        asset.write_text('changed asset bytes');self.assertNotEqual(before,self.key())
        self.document['nodes'][0]['comps']['sprite']['frame']='wo5.png'
        self.assertNotEqual(before,self.key())

    def test_missing_real_reference_and_frame_path_remain_unclosed(self):
        self.document['attachment']='missing.png';self.assertIsNone(self.key())
        self.document.pop('attachment')
        self.document['nodes']=[node('Canvas/Original',[.1,.1,.1,.1],sprite={'frame':'missing/path.png'})]
        self.assertIsNone(self.key())


if __name__=='__main__':unittest.main()
