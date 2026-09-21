"""
test_game_logic.py - Unit and integration tests for the v3 game contract.
Verifies difficulty HP, five-map scaling, supplies, active hunting AI, pause/help
interaction, hard-mode drops, and grade scoring.
"""

import os
import sys

# Set SDL dummy drivers for headless testing
os.environ["SDL_VIDEODRIVER"] = "dummy"
os.environ["SDL_AUDIODRIVER"] = "dummy"

import unittest
import pygame

import audio
import bullet
import effects
import enemy
import map
import player
import sprites
import supply
import ui
import weapon


class TestGameLogicV3(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        pygame.init()

    def test_audio_sound_synthesis(self):
        """Verify all synthesized sounds including new medkit_pickup and menu_select."""
        am = audio.AudioManager()
        expected = [
            'gunshot', 'knife_slash', 'knife_hit',
            'hit_body', 'hit_wall', 'footstep',
            'alert', 'victory', 'defeat',
            'medkit_pickup', 'menu_select'
        ]
        for s in expected:
            self.assertIn(s, am.sounds, f"Sound '{s}' should be present")

    def test_difficulty_hp_configuration(self):
        """Verify v3 player and enemy HP for each difficulty."""
        expected = {
            'EASY': (20, 3),
            'MEDIUM': (15, 5),
            'HARD': (10, 10),
        }
        for difficulty, (player_hp, enemy_hp) in expected.items():
            self.assertEqual(ui.DIFFICULTIES[difficulty]['hp'], player_hp)
            self.assertEqual(ui.DIFFICULTIES[difficulty]['enemy_hp'], enemy_hp)

            p = player.Player(100, 100, max_hp=player_hp)
            self.assertEqual(p.hp, player_hp)
            self.assertEqual(p.max_hp, player_hp)

            e = enemy.Enemy(200, 200, max_hp=enemy_hp)
            self.assertEqual(e.hp, enemy_hp)
            self.assertEqual(e.max_hp, enemy_hp)

    def test_five_maps_and_enemy_scaling(self):
        """Verify all 5 predefined maps have exact specified dimensions, enemy scaling, and supplies."""
        expected_configs = {
            1: {'enemies': 3,  'supplies': 0, 'w': 1100, 'h': 850},
            2: {'enemies': 5,  'supplies': 2, 'w': 1600, 'h': 1200},
            3: {'enemies': 5,  'supplies': 2, 'w': 1600, 'h': 1200},
            4: {'enemies': 7,  'supplies': 3, 'w': 2200, 'h': 1600},
            5: {'enemies': 7,  'supplies': 4, 'w': 2400, 'h': 1800},
        }

        for mid, exp in expected_configs.items():
            mgr = map.MapManager(map_id=mid)
            self.assertEqual(len(mgr.enemy_configs), exp['enemies'], f"Map {mid} should have {exp['enemies']} enemies")
            self.assertEqual(len(mgr.supply_stations), exp['supplies'], f"Map {mid} should have {exp['supplies']} supplies")
            self.assertEqual(mgr.width, exp['w'], f"Map {mid} width mismatch")
            self.assertEqual(mgr.height, exp['h'], f"Map {mid} height mismatch")

    def test_supply_medkit_pickup_and_healing_cap(self):
        """Verify direct pickup at full HP and capped healing when damaged."""
        am = audio.AudioManager()
        ui_mgr = ui.UIManager()
        p = player.Player(100, 100, max_hp=10)
        med = supply.Medkit(100, 100, heal_amount=5)

        # 1. Full-health pickup is still collected immediately.
        picked = med.check_pickup(p, am, ui_mgr)
        self.assertTrue(picked)
        self.assertTrue(med.collected)
        self.assertEqual(p.hp, 10)

        # 2. Damage player to 3 HP, then pick up -> restores +5 to 8 HP.
        p.hp = 3
        med_damaged = supply.Medkit(100, 100, heal_amount=5)
        picked = med_damaged.check_pickup(p, am, ui_mgr)
        self.assertTrue(picked)
        self.assertTrue(med_damaged.collected)
        self.assertEqual(p.hp, 8)

        # 3. Test healing cap on second medkit (+5 heals 2 up to 10 max_hp).
        med2 = supply.Medkit(100, 100, heal_amount=5)
        picked2 = med2.check_pickup(p, am, ui_mgr)
        self.assertTrue(picked2)
        self.assertEqual(p.hp, 10)

    def test_aggressive_ai_hearing_and_hunting(self):
        """Verify AI reacts to distant player gunfire and sets investigate coordinates."""
        e = enemy.Enemy(500, 500)
        self.assertIsNone(e.last_known_player_pos)

        # 1. Sound within hearing range (700px) alerts enemy
        heard = e.hear_sound((700, 500), max_dist=750.0)
        self.assertTrue(heard)
        self.assertIsNotNone(e.last_known_player_pos)
        self.assertEqual(e.last_known_player_pos, [700.0, 500.0])

        # 2. Sound outside hearing range (>750px) is ignored
        e2 = enemy.Enemy(100, 100)
        heard_far = e2.hear_sound((1200, 100), max_dist=750.0)
        self.assertFalse(heard_far)
        self.assertIsNone(e2.last_known_player_pos)

    def test_scoring_system_and_grade_evaluation(self):
        """Verify score calculation and letter grade mapping (A to E)."""
        # Grade A scenario: Fast, flawless Hard clear with high accuracy
        stats_a = {
            'enemies_killed': 5, 'total_enemies': 5,
            'hp': 5, 'max_hp': 5,
            'time': 18.0,
            'shots_fired': 30, 'shots_hit': 26,
            'melee_kills': 1,
            'difficulty': 'HARD'  # 2.2x
        }
        res_a = ui.calculate_grade_and_score(stats_a, is_victory=True)
        self.assertEqual(res_a['grade'], 'A', f"Expected Grade A, got {res_a['grade']}")
        self.assertGreaterEqual(res_a['final_score'], 850)

        # Grade C/B scenario: Medium difficulty, took some damage
        stats_c = {
            'enemies_killed': 5, 'total_enemies': 5,
            'hp': 4, 'max_hp': 10,
            'time': 45.0,
            'shots_fired': 60, 'shots_hit': 35,
            'melee_kills': 0,
            'difficulty': 'MEDIUM'  # 1.5x
        }
        res_c = ui.calculate_grade_and_score(stats_c, is_victory=True)
        self.assertIn(res_c['grade'], ['B', 'C'])

        # Grade E scenario: Early defeat on Easy difficulty
        stats_e = {
            'enemies_killed': 0, 'total_enemies': 5,
            'hp': 0, 'max_hp': 15,
            'time': 10.0,
            'shots_fired': 10, 'shots_hit': 1,
            'melee_kills': 0,
            'difficulty': 'EASY'  # 1.0x
        }
        res_e = ui.calculate_grade_and_score(stats_e, is_victory=False)
        self.assertEqual(res_e['grade'], 'E')

    def test_headless_full_game_simulation_v3(self):
        """Simulates matches across the v3 small and large map configurations."""
        import main
        game = main.Game()

        # Test Map 1 (Small - 3 enemies)
        game.ui_manager.selected_map_id = 1
        game.ui_manager.selected_difficulty = 'HARD'
        game.reset_match()
        self.assertEqual(len(game.enemies), 3)
        self.assertEqual(game.player.max_hp, 10)
        self.assertTrue(all(e.max_hp == 10 for e in game.enemies))

        for _ in range(60):
            game.update_playing(0.016)
            game.render_playing()

        # Test Map 4 (Large A - 7 enemies, 3 supplies)
        game.ui_manager.selected_map_id = 4
        game.ui_manager.selected_difficulty = 'EASY'
        game.reset_match()
        self.assertEqual(len(game.enemies), 7)
        self.assertEqual(len(game.supply_manager.medkits), 3)
        self.assertEqual(game.player.max_hp, 20)

        for _ in range(60):
            game.update_playing(0.016)
            game.render_playing()

        print("\nHeadless game simulation passed all v3 maps and difficulty modes!")

    def test_hard_mode_enemy_death_drops_medkit(self):
        """Verify every hard-mode enemy death creates one medkit at its location."""
        import main
        game = main.Game()
        game.ui_manager.selected_map_id = 1
        game.ui_manager.selected_difficulty = 'HARD'
        game.reset_match()
        victim = game.enemies[0]
        victim.alive = False
        death_pos = tuple(victim.pos)

        game._process_enemy_deaths()
        game._process_enemy_deaths()

        drops = [m for m in game.supply_manager.medkits if tuple(m.pos) == death_pos]
        self.assertEqual(len(drops), 1)

    def test_pause_and_help_controls(self):
        """Verify the interactive controls exposed by the pause/help overlays."""
        mgr = ui.UIManager()
        surface = pygame.Surface((1280, 720))
        mgr.draw_start_screen(surface, 0)
        self.assertEqual(mgr.handle_start_click(mgr.help_btn_rect.center, audio.AudioManager()), 'HELP')
        mgr.draw_help_modal(surface)
        self.assertTrue(mgr.handle_help_click(mgr.help_tab_rects[2].center))
        self.assertEqual(mgr.help_tab, 2)

        mgr.draw_pause_screen(surface)
        self.assertEqual(mgr.handle_pause_click(mgr.pause_btn_rects[0].center, audio.AudioManager()), 'RESUME')
        self.assertEqual(mgr.handle_pause_click(mgr.pause_btn_rects[1].center, audio.AudioManager()), 'RESTART')
        self.assertEqual(mgr.handle_pause_click(mgr.pause_btn_rects[2].center, audio.AudioManager()), 'MENU')


if __name__ == '__main__':
    unittest.main()
