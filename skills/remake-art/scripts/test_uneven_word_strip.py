import unittest
from PIL import Image, ImageDraw
from cut_sheet_frame import extract

class UnevenWordStrip(unittest.TestCase):
    def sheet(self, spans):
        im=Image.new('RGBA',(80,200));pen=ImageDraw.Draw(im)
        for i,(a,b) in enumerate(spans):
            pen.rectangle((10,a,68,b),fill=(20+i*70,50,90,255))
        return im

    def test_actual_bands_keep_every_row_and_no_neighbor(self):
        im=self.sheet([(8,24),(35,61),(73,185)])
        for row,color in [(1,20),(2,90),(3,160)]:
            master,cell,bounds=extract(im,3,1,row,1,rows_from_bands=True)
            colors={p[0] for p in master.getdata() if p[3]>8}
            self.assertEqual(colors,{color})
            self.assertEqual(sum(p[3]>8 for p in master.getdata()),sum(p[3]>8 and p[0]==color for p in im.getdata()))

    def test_missing_separator_refused(self):
        with self.assertRaisesRegex(ValueError,'complete clear bands'):
            extract(self.sheet([(8,65),(68,185)]),2,1,1,1,True)

    def test_extra_row_refused(self):
        with self.assertRaisesRegex(ValueError,'complete clear bands'):
            extract(self.sheet([(8,24),(35,61),(73,185)]),2,1,1,1,True)

    def test_outer_edge_refused(self):
        with self.assertRaisesRegex(ValueError,'complete clear bands'):
            extract(self.sheet([(0,24),(35,185)]),2,1,1,1,True)

    def test_multicolumn_not_guessed(self):
        with self.assertRaisesRegex(ValueError,'single-column'):
            extract(self.sheet([(8,24),(35,185)]),2,2,1,1,True)
