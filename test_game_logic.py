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

    def test_loadout_selection_applies_weapon_and_skin(self):
        """Verify the loadout screen selections reach the gameplay Player entity."""
        import main

        mgr = ui.UIManager()
        surface = pygame.Surface((1280, 720))
        mgr.draw_start_screen(surface, 0)
        self.assertEqual(mgr.handle_start_click(mgr.start_btn_rect.center, audio.AudioManager()), 'DEPLOY')

        mgr.draw_loadout_screen(surface, 0)
        self.assertEqual(
            mgr.handle_loadout_click(mgr.loadout_weapon_rects['SNIPER'].center, audio.AudioManager()),
            'SELECT_WEAPON'
        )
        self.assertEqual(
            mgr.handle_loadout_click(mgr.loadout_skin_rects['SILVER'].center, audio.AudioManager()),
            'SELECT_SKIN'
        )
        self.assertEqual(mgr.selected_weapon_type, 'SNIPER')
        self.assertEqual(mgr.selected_skin_id, 'SILVER')

        game = main.Game()
        game.ui_manager.selected_weapon_type = mgr.selected_weapon_type
        game.ui_manager.selected_skin_id = mgr.selected_skin_id
        game.reset_match()
        self.assertEqual(game.player.weapon_type, 'SNIPER')
        self.assertEqual(game.player.skin_id, 'SILVER')
        self.assertIsInstance(game.player.primary_weapon, weapon.SniperRifle)

    def test_primary_weapon_specials(self):
        """Verify sniper piercing/damage and rocket room-clearance projectile flags."""
        self.assertEqual(weapon.SniperRifle().damage, 5)
        self.assertEqual(weapon.SniperRifle().weapon_type, 'SNIPER')
        self.assertEqual(weapon.RocketLauncher().weapon_type, 'ROCKET')
        self.assertEqual(weapon.SniperRifle().ammo, 10)
        self.assertEqual(weapon.RocketLauncher().ammo, 3)

        sniper = bullet.Bullet(100, 100, 0, damage=5, wall_pierce=True, is_sniper=True)
        rocket = bullet.Bullet(100, 100, 0, damage=10, is_rocket=True)
        self.assertTrue(sniper.wall_pierce)
        self.assertTrue(sniper.is_sniper)
        self.assertTrue(rocket.is_rocket)

    def test_rocket_breaches_walls_but_standard_rounds_do_not(self):
        """Verify rockets can breach walls while regular rounds cannot kill through them."""
        map_mgr = map.MapManager(1)
        effects_mgr = effects.EffectManager()
        audio_mgr = audio.AudioManager()

        behind_wall = enemy.Enemy(300, 200, max_hp=10)
        regular_round = bullet.Bullet(100, 200, 0, speed=2500, damage=1)
        regular_round.update(0.1, map_mgr, [behind_wall], effects_mgr, audio_mgr, (100, 200))
        self.assertEqual(behind_wall.hp, 10)
        self.assertFalse(regular_round.alive)

        behind_wall = enemy.Enemy(300, 200, max_hp=10)
        same_room_enemy = enemy.Enemy(320, 220, max_hp=10)
        rocket_round = bullet.Bullet(
            100, 200, 0, speed=2500, damage=10,
            wall_pierce=True, is_rocket=True
        )
        rocket_round.update(
            0.1, map_mgr, [behind_wall, same_room_enemy],
            effects_mgr, audio_mgr, (100, 200)
        )
        self.assertFalse(behind_wall.alive)
        self.assertFalse(same_room_enemy.alive)
        self.assertFalse(any(w.left == 220 and w.top == 120 for w in map_mgr.walls))

        # A rocket entering the room clears an enemy even when the enemy is
        # off the projectile's center line.
        open_map = map.MapManager(1)
        off_line_enemy = enemy.Enemy(320, 220, max_hp=10)
        entering_rocket = bullet.Bullet(
            100, 200, 0, speed=2500, damage=10,
            wall_pierce=True, is_rocket=True
        )
        entering_rocket.update(
            0.1, open_map, [off_line_enemy],
            effects_mgr, audio_mgr, (100, 200)
        )
        self.assertFalse(off_line_enemy.alive)

        shooter = player.Player(100, 100, weapon_type='ROCKET')
        fired = []
        shooter.primary_weapon.timer = 0.0
        shooter.primary_weapon.fire(shooter, fired, effects_mgr, audio_mgr, shooter.pos, is_player=True)
        self.assertTrue(fired[0].wall_pierce)

        melee_attacker = player.Player(200, 200)
        melee_attacker.angle_deg = 0.0
        melee_target = enemy.Enemy(250, 200, max_hp=10)
        melee_attacker.bayonet.strike(
            melee_attacker, [melee_target], effects_mgr, audio_mgr,
            melee_attacker.pos, is_player=True, map_manager=map.MapManager(1)
        )
        self.assertEqual(melee_target.hp, 10)

    def test_limited_primary_weapon_ammo(self):
        """Verify sniper ammo stops at 10 shots and rockets stop at 3 shots."""
        effects_mgr = effects.EffectManager()
        audio_mgr = audio.AudioManager()

        sniper_player = player.Player(100, 100, weapon_type='SNIPER')
        sniper_bullets = []
        for _ in range(10):
            sniper_player.primary_weapon.timer = 0.0
            self.assertTrue(sniper_player.primary_weapon.fire(
                sniper_player, sniper_bullets, effects_mgr, audio_mgr, sniper_player.pos, is_player=True
            ))
        self.assertEqual(sniper_player.primary_weapon.ammo, 0)
        sniper_player.primary_weapon.timer = 0.0
        self.assertFalse(sniper_player.primary_weapon.can_fire())
        self.assertFalse(sniper_player.primary_weapon.fire(
            sniper_player, sniper_bullets, effects_mgr, audio_mgr, sniper_player.pos, is_player=True
        ))

        rocket_player = player.Player(100, 100, weapon_type='ROCKET')
        rocket_bullets = []
        for _ in range(3):
            rocket_player.primary_weapon.timer = 0.0
            self.assertTrue(rocket_player.primary_weapon.fire(
                rocket_player, rocket_bullets, effects_mgr, audio_mgr, rocket_player.pos, is_player=True
            ))
        self.assertEqual(rocket_player.primary_weapon.ammo, 0)
        rocket_player.primary_weapon.timer = 0.0
        self.assertFalse(rocket_player.primary_weapon.can_fire())

    def test_easy_grade_a_threshold_is_rebalanced(self):
        """Verify Easy uses the lower v3 Grade A threshold while Medium/Hard stay at 1200."""
        self.assertEqual(ui.GRADE_THRESHOLDS['EASY'][0][1], 750)
        self.assertEqual(ui.GRADE_THRESHOLDS['MEDIUM'][0][1], 1200)
        self.assertEqual(ui.GRADE_THRESHOLDS['HARD'][0][1], 1200)

    def test_help_modal_scroll_stays_inside_fixed_frame(self):
        """Verify wheel scrolling is clamped without changing the modal frame size."""
        mgr = ui.UIManager()
        surface = pygame.Surface((1280, 720))
        mgr.draw_help_modal(surface)
        frame = mgr.help_modal_rect.copy()
        mgr.handle_help_scroll(-100)
        self.assertGreaterEqual(mgr.help_scroll_y, 0.0)
        self.assertLessEqual(mgr.help_scroll_y, mgr.max_help_scroll)
        mgr.handle_help_scroll(100)
        self.assertEqual(mgr.help_scroll_y, 0.0)
        self.assertEqual(mgr.help_modal_rect.size, frame.size)
        self.assertEqual(mgr.help_modal_rect.size, (820, 510))


if __name__ == '__main__':
    unittest.main()
