"""
main.py - Main entry point and game loop for 2D Top-Down Shooter.
Coordinates state transitions, difficulty & map selection, active hunting AI,
supply stations, camera tracking, and end-game score evaluation.
"""

import math
import sys
import pygame

from audio import AudioManager
from bullet import Bullet
from effects import EffectManager
from enemy import Enemy
from map import MapManager
from player import Player
from sprites import get_sprite_bank
from supply import SupplyManager
from ui import UIManager, DIFFICULTIES

SCREEN_WIDTH = 1280
SCREEN_HEIGHT = 720
FPS = 60


class Game:
    """Core Game engine coordinating states, input, simulation, and rendering."""

    def __init__(self):
        pygame.init()
        pygame.display.set_caption("2D Top-Down Shooter - Tactical Elimination Prototype")
        pygame.mouse.set_visible(False)

        self.screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
        self.clock = pygame.time.Clock()
        self.sprite_bank = get_sprite_bank()
        self.audio_manager = AudioManager()
        self.ui_manager = UIManager(SCREEN_WIDTH, SCREEN_HEIGHT)

        self.state = 'START'  # START, PLAYING, PAUSED, HELP, VICTORY, DEFEAT
        self.tick_count = 0
        self.stats = {}

        self.reset_match()

    def reset_match(self):
        """Initializes match entities based on selected difficulty and map."""
        diff_key = self.ui_manager.selected_difficulty
        map_id = self.ui_manager.selected_map_id
        player_hp = DIFFICULTIES.get(diff_key, DIFFICULTIES['MEDIUM'])['hp']

        # 1. Map & Arena Geometry
        self.map_manager = MapManager(map_id=map_id)
        self.effect_manager = EffectManager()
        self.bullets = []

        # 2. Player Unit (Spawns with configured difficulty HP/Lives)
        self.player = Player(
            x=self.map_manager.player_spawn[0],
            y=self.map_manager.player_spawn[1],
            max_hp=player_hp
        )

        # 3. Scaled AI Enemies with Predefined Tactical Waypoints
        enemy_hp = DIFFICULTIES.get(diff_key, DIFFICULTIES['MEDIUM'])['enemy_hp']
        self.enemies = [
            Enemy(
                x=cfg['pos'][0],
                y=cfg['pos'][1],
                waypoints=cfg['waypoints'],
                enemy_id=idx + 1,
                max_hp=enemy_hp
            )
            for idx, cfg in enumerate(self.map_manager.enemy_configs)
        ]

        # 4. Collectible Supply Stations (Medkits on Medium & Large maps)
        self.supply_manager = SupplyManager(self.map_manager.supply_stations, heal_amount=5)
        # The HUD reads these live managers to render the selected map's radar.
        self.ui_manager.map_manager_ref = self.map_manager
        self.ui_manager.supply_manager_ref = self.supply_manager
        # Death processing is centralized so kills from gunfire, bayonets, and
        # same-frame updates each produce exactly one effect/drop.
        self.processed_enemy_deaths = set()

        # 5. Camera Initial Position
        self.camera_x = max(0.0, min(self.map_manager.width - SCREEN_WIDTH, self.player.pos[0] - SCREEN_WIDTH // 2))
        self.camera_y = max(0.0, min(self.map_manager.height - SCREEN_HEIGHT, self.player.pos[1] - SCREEN_HEIGHT // 2))

        # 6. Match Metrics
        self.match_time = 0.0
        self.player_bullets_fired = 0
        self.stats = {
            'time': 0.0,
            'bullets': 0,
            'shots_fired': 0,
            'shots_hit': 0,
            'melee_kills': 0,
            'hp': player_hp,
            'max_hp': player_hp,
            'enemies_killed': 0,
            'total_enemies': len(self.enemies),
            'difficulty': diff_key,
            'map_id': map_id,
            'cause': 'KILLED IN ACTION'
        }

        self.ui_manager.reset_intro()

    def run(self):
        """Main game loop capped at 60 FPS."""
        running = True
        while running:
            dt = self.clock.tick(FPS) / 1000.0
            dt = min(dt, 0.05)
            self.tick_count += 1

            events = pygame.event.get()
            for event in events:
                if event.type == pygame.QUIT:
                    running = False
                elif event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_ESCAPE:
                        if self.state == 'PLAYING':
                            self.state = 'PAUSED'
                        elif self.state == 'PAUSED':
                            self.state = 'PLAYING'
                        elif self.state == 'HELP':
                            self.state = 'START'
                        elif self.state in ('VICTORY', 'DEFEAT'):
                            self.state = 'START'
                        else:
                            running = False
                    elif self.state == 'PAUSED':
                        if event.key == pygame.K_r:
                            self.reset_match()
                            self.state = 'PLAYING'
                        elif event.key == pygame.K_m:
                            self.state = 'START'
                    elif self.state == 'HELP':
                        if event.key in (pygame.K_LEFT, pygame.K_UP):
                            self.ui_manager.help_tab = (self.ui_manager.help_tab - 1) % 3
                        elif event.key in (pygame.K_RIGHT, pygame.K_DOWN):
                            self.ui_manager.help_tab = (self.ui_manager.help_tab + 1) % 3
                        elif event.key in (pygame.K_1, pygame.K_KP1, pygame.K_e):
                            self.ui_manager.help_tab = 0
                        elif event.key in (pygame.K_2, pygame.K_KP2, pygame.K_m):
                            self.ui_manager.help_tab = 1
                        elif event.key in (pygame.K_3, pygame.K_KP3, pygame.K_h):
                            self.ui_manager.help_tab = 2
                    elif self.state == 'START':
                        # Map selection shortcuts: 1 to 5
                        if event.key in (pygame.K_1, pygame.K_KP1):
                            self.ui_manager.selected_map_id = 1
                            self.audio_manager.play('menu_select', 0.8)
                        elif event.key in (pygame.K_2, pygame.K_KP2):
                            self.ui_manager.selected_map_id = 2
                            self.audio_manager.play('menu_select', 0.8)
                        elif event.key in (pygame.K_3, pygame.K_KP3):
                            self.ui_manager.selected_map_id = 3
                            self.audio_manager.play('menu_select', 0.8)
                        elif event.key in (pygame.K_4, pygame.K_KP4):
                            self.ui_manager.selected_map_id = 4
                            self.audio_manager.play('menu_select', 0.8)
                        elif event.key in (pygame.K_5, pygame.K_KP5):
                            self.ui_manager.selected_map_id = 5
                            self.audio_manager.play('menu_select', 0.8)
                        # Difficulty cycle: Left / Right arrows or e/m/h
                        elif event.key == pygame.K_LEFT:
                            dkeys = ['EASY', 'MEDIUM', 'HARD']
                            idx = dkeys.index(self.ui_manager.selected_difficulty)
                            self.ui_manager.selected_difficulty = dkeys[(idx - 1) % len(dkeys)]
                            self.audio_manager.play('menu_select', 0.8)
                        elif event.key == pygame.K_RIGHT:
                            dkeys = ['EASY', 'MEDIUM', 'HARD']
                            idx = dkeys.index(self.ui_manager.selected_difficulty)
                            self.ui_manager.selected_difficulty = dkeys[(idx + 1) % len(dkeys)]
                            self.audio_manager.play('menu_select', 0.8)
                        elif event.key == pygame.K_e:
                            self.ui_manager.selected_difficulty = 'EASY'
                            self.audio_manager.play('menu_select', 0.8)
                        elif event.key == pygame.K_m:
                            self.ui_manager.selected_difficulty = 'MEDIUM'
                            self.audio_manager.play('menu_select', 0.8)
                        elif event.key == pygame.K_h:
                            self.ui_manager.selected_difficulty = 'HARD'
                            self.audio_manager.play('menu_select', 0.8)
                        # Start Match
                        elif event.key in (pygame.K_RETURN, pygame.K_SPACE):
                            self.reset_match()
                            self.state = 'PLAYING'
                    elif self.state in ('VICTORY', 'DEFEAT'):
                        if event.key == pygame.K_r:
                            self.reset_match()
                            self.state = 'PLAYING'

                elif event.type == pygame.MOUSEBUTTONDOWN:
                    if event.button == 1:
                        if self.state == 'START':
                            action = self.ui_manager.handle_start_click(event.pos, self.audio_manager)
                            if action == 'DEPLOY':
                                self.reset_match()
                                self.state = 'PLAYING'
                            elif action == 'HELP':
                                self.state = 'HELP'
                        elif self.state == 'HELP':
                            if not self.ui_manager.handle_help_click(event.pos):
                                self.state = 'START'
                        elif self.state == 'PAUSED':
                            action = self.ui_manager.handle_pause_click(event.pos, self.audio_manager)
                            if action == 'RESUME':
                                self.state = 'PLAYING'
                            elif action == 'RESTART':
                                self.reset_match()
                                self.state = 'PLAYING'
                            elif action == 'MENU':
                                self.state = 'START'

            # State updates and rendering
            if self.state == 'START':
                self.ui_manager.draw_start_screen(self.screen, self.tick_count)
                self.ui_manager.draw_crosshair(self.screen, pygame.mouse.get_pos())
            elif self.state == 'PLAYING':
                self.update_playing(dt)
                self.render_playing()
            elif self.state == 'PAUSED':
                self.render_playing()
                self.ui_manager.draw_pause_screen(self.screen)
            elif self.state == 'HELP':
                self.ui_manager.draw_start_screen(self.screen, self.tick_count)
                self.ui_manager.draw_help_modal(self.screen)
                self.ui_manager.draw_crosshair(self.screen, pygame.mouse.get_pos())
            elif self.state == 'VICTORY':
                self.render_playing()
                self.ui_manager.draw_victory_screen(self.screen, self.tick_count, self.stats)
                self.ui_manager.draw_crosshair(self.screen, pygame.mouse.get_pos())
            elif self.state == 'DEFEAT':
                self.render_playing()
                self.ui_manager.draw_defeat_screen(self.screen, self.tick_count, self.stats)
                self.ui_manager.draw_crosshair(self.screen, pygame.mouse.get_pos())

            pygame.display.flip()

        pygame.quit()
        sys.exit()

    def update_playing(self, dt):
        """Updates entities, active hunting, supplies, and scoring checks."""
        self.match_time += dt
        self.ui_manager.update_intro(dt)

        keys = pygame.key.get_pressed()
        mouse_buttons = pygame.mouse.get_pressed()
        mouse_screen_pos = pygame.mouse.get_pos()

        mouse_world_pos = (
            mouse_screen_pos[0] + self.camera_x,
            mouse_screen_pos[1] + self.camera_y
        )

        # Player input & update
        old_bullet_count = len(self.bullets)
        self.player.handle_input(
            keys=keys,
            mouse_buttons=mouse_buttons,
            mouse_world_pos=mouse_world_pos,
            dt=dt,
            bullets=self.bullets,
            enemies=self.enemies,
            effect_manager=self.effect_manager,
            audio_manager=self.audio_manager
        )

        # Active Hunting Trigger: Gunfire attracts nearby enemies
        if len(self.bullets) > old_bullet_count:
            self.player_bullets_fired += (len(self.bullets) - old_bullet_count)
            for enemy in self.enemies:
                if enemy.alive:
                    enemy.hear_sound(self.player.pos, max_dist=750.0)

        self.player.update(dt, self.map_manager, self.audio_manager)

        # Supplies update (Medkits)
        self.supply_manager.update(dt, self.player, self.audio_manager, self.ui_manager)

        # Check Player Death (Defeat)
        if not self.player.alive and self.state == 'PLAYING':
            self.effect_manager.add_death_effect(
                self.player.pos[0], self.player.pos[1], 'blue', self.player.angle_deg
            )
            self.audio_manager.play('defeat', volume=1.0)
            self._finalize_stats(is_victory=False)
            self.state = 'DEFEAT'
            return

        # AI Enemies update
        for enemy in self.enemies:
            if not enemy.alive:
                continue
            enemy.update(
                dt=dt,
                player=self.player,
                map_manager=self.map_manager,
                bullets=self.bullets,
                effect_manager=self.effect_manager,
                audio_manager=self.audio_manager
            )

        # Bullets update
        alive_targets_for_player = [e for e in self.enemies if e.alive]
        alive_targets_for_enemy = [self.player] if self.player.alive else []

        for b in self.bullets:
            if not b.alive:
                continue
            targets = alive_targets_for_player if b.owner == 'player' else alive_targets_for_enemy
            b.update(
                dt=dt,
                map_manager=self.map_manager,
                targets=targets,
                effect_manager=self.effect_manager,
                audio_manager=self.audio_manager,
                listener_pos=self.player.pos
            )

        self.bullets = [b for b in self.bullets if b.alive]
        self._process_enemy_deaths()
        self.effect_manager.update(dt)

        # Smooth camera tracking
        target_cam_x = self.player.pos[0] - SCREEN_WIDTH // 2
        target_cam_y = self.player.pos[1] - SCREEN_HEIGHT // 2
        max_cam_x = self.map_manager.width - SCREEN_WIDTH
        max_cam_y = self.map_manager.height - SCREEN_HEIGHT

        self.camera_x += (target_cam_x - self.camera_x) * min(1.0, 10.0 * dt)
        self.camera_y += (target_cam_y - self.camera_y) * min(1.0, 10.0 * dt)
        self.camera_x = max(0.0, min(max_cam_x, self.camera_x))
        self.camera_y = max(0.0, min(max_cam_y, self.camera_y))

        # Check Win Condition: All enemies eliminated
        alive_enemies = sum(1 for e in self.enemies if e.alive)
        if alive_enemies == 0 and self.state == 'PLAYING':
            self.audio_manager.play('victory', volume=1.0)
            self._finalize_stats(is_victory=True)
            self.state = 'VICTORY'

    def _process_enemy_deaths(self):
        """Apply one-time death effects and Hard-mode medkit drops."""
        for enemy in self.enemies:
            if enemy.alive or enemy.id in self.processed_enemy_deaths:
                continue

            self.processed_enemy_deaths.add(enemy.id)
            self.effect_manager.add_death_effect(
                enemy.pos[0], enemy.pos[1], 'red', enemy.angle_deg
            )

            if self.ui_manager.selected_difficulty == 'HARD':
                self.supply_manager.add_medkit(enemy.pos[0], enemy.pos[1])
                self.ui_manager.show_notification("HARD DROP: MEDKIT DEPLOYED", duration=1.8)

    def _finalize_stats(self, is_victory=True):
        """Compiles match performance stats for scoring and grading."""
        self.stats = {
            'time': self.match_time,
            'bullets': self.player_bullets_fired,
            'shots_fired': self.player.shots_fired,
            'shots_hit': self.player.shots_hit,
            'melee_kills': self.player.melee_kills,
            'hp': self.player.hp,
            'max_hp': self.player.max_hp,
            'enemies_killed': sum(1 for e in self.enemies if not e.alive),
            'total_enemies': len(self.enemies),
            'difficulty': self.ui_manager.selected_difficulty,
            'map_id': self.ui_manager.selected_map_id,
            'cause': 'MISSION ACCOMPLISHED' if is_victory else 'K.I.A. - OPERATOR ELIMINATED'
        }

    def render_playing(self):
        """Renders world, entities, supplies, bullets, lighting halos, and HUD."""
        shake_ox, shake_oy = self.effect_manager.get_screen_shake_offset()
        cam_offset = (self.camera_x + shake_ox, self.camera_y + shake_oy)

        # 1. Floor & Walls
        self.map_manager.draw(self.screen, cam_offset)

        # 2. Ground Decals (bloodstains)
        self.effect_manager.draw_decals(self.screen, cam_offset)

        # 3. Supply Stations (Medkits)
        self.supply_manager.draw(self.screen, cam_offset)

        # 4. Fallen soldier corpses
        self.effect_manager.draw_corpses(self.screen, self.sprite_bank, cam_offset)

        # 5. Characters
        for enemy in self.enemies:
            enemy.draw(self.screen, self.sprite_bank, cam_offset)
        self.player.draw(self.screen, self.sprite_bank, cam_offset)

        # 6. Bullets
        for b in self.bullets:
            b.draw(self.screen, cam_offset)

        # 7. Particles & Muzzle flashes
        self.effect_manager.draw_particles(self.screen, cam_offset)

        # 8. Additive Lighting Halos
        self.effect_manager.render_lighting_halos(
            self.screen,
            self.player,
            self.enemies,
            self.bullets,
            cam_offset
        )

        # 9. HUD & Overlays
        self.ui_manager.draw_hud(self.screen, self.player, self.enemies, self.bullets)

        # 10. Intro sequence animation (if active)
        if self.ui_manager.is_intro_active():
            self.ui_manager.draw_intro_animation(self.screen)

        # 11. Crosshair
        self.ui_manager.draw_crosshair(self.screen, pygame.mouse.get_pos())


if __name__ == '__main__':
    game = Game()
    game.run()
