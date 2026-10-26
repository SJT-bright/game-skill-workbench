#!/usr/bin/env python3
"""Focused regressions for first-round art-audit false positives."""

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import audit_page_richness as audit  # noqa: E402


def sprite_node(name, frame_size, display_size, rect, *, tiled=False, angle=0):
    return {
        'name': name,
        'path': 'Canvas/MAIN/Stage/board/' + name,
        'angle': angle,
        'rect': rect,
        'comps': {
            'sprite': {
                'frame': name,
                'frame_size': frame_size,
                'display_size': display_size,
                'sliced': False,
                'tiled': tiled,
            }
        },
    }


class ArtAuditRegressionTests(unittest.TestCase):
    def test_map_counts_visible_locked_level_cards(self):
        nodes = [
            {
                'name': f'level_{i}',
                'path': f'Canvas/UI/Map/level_{i}',
                'comps': {'button': {'interactable': i == 1}},
            }
            for i in range(1, 11)
        ]
        self.assertEqual(audit.visible_level_button_count(nodes), 10)

    def test_rotated_sprite_uses_unrotated_axis_dimensions(self):
        arrow = sprite_node(
            'Exit', [345, 401], [51.6, 60], [0.2, 0.2, 0.08, 0.08], angle=90
        )
        self.assertEqual(audit.squash_problems([arrow], []), [])

    def test_tiled_trim_is_not_compared_as_one_stretched_picture(self):
        trim = sprite_node(
            'Block0', [64, 10], [490, 10], [0.1, 0.2, 0.65, 0.015], tiled=True
        )
        self.assertEqual(audit.squash_problems([trim], []), [])
        self.assertEqual(audit.low_res_problems([trim], []), [])

    def test_real_nontiled_stretch_and_low_resolution_still_fail(self):
        stretched = sprite_node(
            'sample_picture', [400, 100], [250, 25], [0.1, 0.2, 0.2, 0.1]
        )
        self.assertTrue(any('squashed_picture:' in item for item in audit.squash_problems([stretched], [])))
        soft = sprite_node(
            'badge', [30, 30], [20, 20], [0.2, 0.2, 0.1, 0.1]
        )
        self.assertTrue(any('low_res:' in item for item in audit.low_res_problems([soft], [])))

    def test_fullscreen_art_uses_live_css_size_not_design_units(self):
        # A phone screenshot is 393x852 CSS px even when Cocos reports a larger design-space display size.
        meadow = sprite_node('v4_bg_spring', [720, 1280], [878, 1561], [0, 0, 1, 1])
        meadow['comps']['sprite']['css_display_size'] = [393, 852]
        self.assertEqual(audit.low_res_problems([meadow], []), [])

        soft = sprite_node('v4_bg_spring', [500, 1000], [878, 1561], [0, 0, 1, 1])
        soft['comps']['sprite']['css_display_size'] = [393, 852]
        self.assertTrue(any('low_res:' in item for item in audit.low_res_problems([soft], [])))

    def test_dim_cocos_bgshade_is_not_art_but_opaque_fallback_still_fails(self):
        shade = sprite_node('bgshade', [2, 2], [750, 1626], [0, 0, 1, 1])
        shade['path'] = 'Canvas/UI/MenuLayer/bgshade'
        shade['opacity'] = 70 / 255
        shade['comps']['sprite']['frame'] = 'default_sprite_splash'
        self.assertEqual(audit.low_res_problems([shade], []), [])

        # Do not turn the asset name into a broad exemption: an opaque 2x2 fallback
        # is still a real low-resolution picture and must retain the ART-04 failure.
        shade['opacity'] = 1
        self.assertTrue(any('low_res:' in item for item in audit.low_res_problems([shade], [])))

    def test_flat_sky_is_not_placeholder_but_flat_ui_surface_is(self):
        backdrop = sprite_node('background', [1500, 3000], [750, 1500], [0, 0, 1, 1])
        backdrop['path'] = 'Canvas/UI/MenuLayer/bg/__art_image'
        backdrop['comps']['sprite']['frame'] = 'home_bg'
        sample = [0.75, 0, 0.25, 0.133]
        self.assertTrue(audit.background_only_block(sample, [backdrop]))

        placeholder = sprite_node('empty_card', [200, 100], [200, 100], sample)
        placeholder['path'] = 'Canvas/UI/MenuLayer/empty_card'
        self.assertFalse(audit.background_only_block(sample, [backdrop, placeholder]))

    def test_icon_caption_set_does_not_count_as_action_text_buttons(self):
        old = audit.BUTTON_SET
        audit.BUTTON_SET = ['btn_*', 'icon_*', 'ctrl_*']
        try:
            icon_button = {
                'name': 'btn_daily', 'path': 'Canvas/UI/MenuLayer/btn_daily',
                'rect': [0.8, 0.75, 0.16, 0.08], 'comps': {'button': {}},
            }
            icon_art = sprite_node('__art_image', [300, 140], [120, 60], icon_button['rect'])
            icon_art['path'] = icon_button['path'] + '/__art_image'
            icon_art['comps']['sprite']['frame'] = 'icon_daily'
            self.assertFalse(audit.texted_action_button(icon_button, [icon_button, icon_art]))

            action_button = dict(icon_button, name='btn_play', path='Canvas/UI/MenuLayer/btn_play')
            action_art = dict(icon_art, path=action_button['path'] + '/__art_image')
            action_art['comps']['sprite']['frame'] = 'btn_play'
            self.assertTrue(audit.texted_action_button(action_button, [action_button, action_art]))
        finally:
            audit.BUTTON_SET = old

    def test_only_offscreen_pose_of_known_transient_banner_is_skipped(self):
        banner = {
            'path': 'Canvas/UI/MainLayer/level_up/label/__art_image',
            'rect': [0.965, 0.46, 0.67, 0.06],
        }
        self.assertTrue(audit.transient_banner_offscreen(banner))
        banner['rect'] = [0.33, 0.46, 0.67, 0.06]
        self.assertFalse(audit.transient_banner_offscreen(banner))
        banner['path'] = 'Canvas/UI/Other/label/__art_image'
        banner['rect'] = [0.965, 0.46, 0.67, 0.06]
        self.assertFalse(audit.transient_banner_offscreen(banner))

    def test_dynamic_number_in_its_own_capsule_is_not_a_collision(self):
        plate = {
            'name': '__art_image',
            'path': 'Canvas/UI/MenuLayer/level_badge/__art_image',
            'rect': [0.58, 0.07, 0.112, 0.017],
            'comps': {'sprite': {'frame': 'capsule'}},
        }
        number = {
            'name': 'nums',
            'path': 'Canvas/UI/MenuLayer/level_badge/nums',
            'rect': [0.58, 0.07, 0.112, 0.017],
            'comps': {'label': {'string': '1/70'}},
        }
        self.assertFalse(any('overlap_text_picture:' in item
                             for item in audit.overlap_problems([plate, number], [], [])))

    def test_named_runtime_value_and_contrast_plates_are_intentional_backgrounds(self):
        number = {
            'name': 'nums',
            'path': 'Canvas/UI/LevelMapOverlay/map_power/nums',
            'rect': [0.12, 0.07, 0.04, 0.02],
            'comps': {'label': {'string': '5'}},
        }
        value_plate = {
            'name': '__art_value_plate',
            'path': 'Canvas/UI/LevelMapOverlay/map_power/__art_value_plate',
            'rect': [0.11, 0.06, 0.06, 0.04],
            'comps': {'sprite': {'frame': 'capsule'}},
        }
        banner_text = {
            'name': '__art_image',
            'path': 'Canvas/UI/MainLayer/level_up/label/__art_image',
            'rect': [0.23, 0.18, 0.54, 0.04],
            'comps': {'image_text': {'string': 'difficulty up'}},
        }
        contrast_plate = {
            'name': '__art_contrast_plate',
            'path': 'Canvas/UI/MainLayer/level_up/label/__art_contrast_plate',
            'rect': [0.21, 0.17, 0.56, 0.06],
            'comps': {'sprite': {'frame': 'capsule'}},
        }
        for nodes in ([number, value_plate], [banner_text, contrast_plate]):
            self.assertFalse(any('overlap_text_picture:' in item
                                 for item in audit.overlap_problems(nodes, [], [])))

    def test_real_icon_overlap_and_non_tutorial_clip_still_fail(self):
        number = {
            'name': 'nums',
            'path': 'Canvas/UI/MenuLayer/level_badge/nums',
            'rect': [0.58, 0.07, 0.112, 0.017],
            'comps': {'label': {'string': '1/70'}},
        }
        icon = sprite_node('icon_reward', [40, 40], [20, 20], [0.58, 0.07, 0.03, 0.017])
        icon['path'] = 'Canvas/UI/MenuLayer/level_badge/icon_reward'
        result = audit.overlap_problems([number, icon], [], [])
        self.assertTrue(any('overlap_text_picture:' in item for item in result))

        holder = sprite_node('holder', [200, 200], [100, 100], [0.3, 0.3, 0.1, 0.1])
        holder['path'] = 'Canvas/UI/popup/button'
        hand = sprite_node('coin_pile', [90, 90], [60, 60], [0.38, 0.32, 0.08, 0.08])
        hand['path'] = 'Canvas/UI/popup/button/coin_pile'
        clipped = audit.overlap_problems([holder, hand], [], [])
        self.assertTrue(any('clip_out:' in item for item in clipped))

    def test_tutorial_hand_touching_car_is_intentionally_not_clip_out(self):
        car = sprite_node('Car0', [70, 140], [70, 140], [0.326, 0.386, 0.093, 0.086])
        car['path'] = 'Canvas/MAIN/Stage/Level1/board/Car0'
        hand = sprite_node('tip', [88, 95], [50, 55], [0.379, 0.438, 0.067, 0.034])
        hand['path'] = 'Canvas/MAIN/Stage/Level1/board/Car0/tip'
        hand['comps']['sprite']['frame'] = 'item_hand'
        self.assertFalse(any('clip_out:' in item
                             for item in audit.overlap_problems([car, hand], [], [])))


if __name__ == '__main__':
    unittest.main()
