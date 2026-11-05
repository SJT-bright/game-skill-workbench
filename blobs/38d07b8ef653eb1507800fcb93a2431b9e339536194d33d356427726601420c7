import unittest
from PIL import Image, ImageDraw
from cut_sheet_frame import extract, fixed_frame

class Cuts(unittest.TestCase):
    def test_uneven_rows_and_detached_mark(self):
        sheet = Image.new('RGBA', (100,100))
        pen = ImageDraw.Draw(sheet)
        pen.rectangle((10,5,90,55),fill='white')
        pen.rectangle((10,70,75,88),fill='yellow')
        pen.rectangle((82,70,90,75),fill='red')
        master, cell, bounds = extract(sheet,2,1,2,1)
        self.assertGreater(cell[1],55)
        self.assertEqual(master.getpixel((85-bounds[0],72-bounds[1])),(255,0,0,255))
        self.assertNotIn((255,255,255,255),set(master.getdata()))

    def test_crossing_seam_refused(self):
        sheet=Image.new('RGBA',(100,100))
        ImageDraw.Draw(sheet).rectangle((10,5,90,95),fill='white')
        with self.assertRaisesRegex(ValueError,'clear bands'):
            extract(sheet,2,1,2,1)

    def test_uncertain_seam_refused(self):
        sheet=Image.new('RGBA',(100,100));pen=ImageDraw.Draw(sheet)
        for top,bottom in [(4,35),(46,54),(65,95)]:
            pen.rectangle((8,top,92,bottom),fill='white')
        with self.assertRaisesRegex(ValueError,'2 plausible'):
            extract(sheet,2,1,2,1)

    def test_touching_outer_border_refused(self):
        sheet=Image.new('RGBA',(64,64))
        ImageDraw.Draw(sheet).rectangle((0,10,48,52),fill='white')
        with self.assertRaisesRegex(ValueError,'touches boundary'):
            extract(sheet,1,1,1,1)

    def test_fixed_rect_uses_ownership_not_total_ink(self):
        im = Image.new('RGBA', (60, 30))
        pen = ImageDraw.Draw(im)
        pen.rectangle((8, 10, 27, 19), fill='yellow')
        pen.rectangle((34, 10, 53, 19), fill='white')
        owner = (0, 0, 31, 30)
        # Equal amounts of missing and foreign ink would pass a total-area comparison.
        with self.assertRaisesRegex(ValueError, 'loses 50 subject pixels and includes 50 foreign pixels'):
            fixed_frame(im, owner, (13, 0, 39, 30))
        self.assertEqual(fixed_frame(im, owner, (3, 1, 32, 26)).size, (29, 25))
