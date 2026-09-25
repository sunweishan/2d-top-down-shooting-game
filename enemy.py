"""
enemy.py - Enemy AI Controller (5 Red Units).
Implements tactical waypoint patrol, line-of-sight raycasting, burst firing,
close-quarters bayonet instakill charge, and spatial audio triggers.
"""

import math
import random
import pygame
from sprites import draw_rotated_sprite
from weapon import MachineGun, Bayonet


class Enemy:
    """Tactical AI Agent (Team Red). Health configurable via max_hp (bullets OR 1 knife = death)."""

    def __init__(self, x, y, waypoints=None, enemy_id=1, max_hp=10):
        self.pos = [float(x), float(y)]
        self.id = enemy_id
        self.hp = max_hp
        self.max_hp = max_hp
        self.alive = True
        self.team = 'enemy'
        self.angle_deg = random.uniform(0, 360)

        # Speeds
        self.patrol_speed = 145.0
        self.chase_speed = 205.0
        self.hitbox_size = 30

        # Weapons
        self.machine_gun = MachineGun(cooldown=0.16, spread_deg=4.5, projectile_speed=820.0)
        self.bayonet = Bayonet(cooldown=0.6, strike_range=65.0, strike_arc_deg=80.0, damage=10)

        # AI Navigation & Active Hunting
        self.state = 'PATROL'  # PATROL, ALERT, CHASE, MELEE
        # A missing route still gets a small roaming loop so a standalone
        # enemy never idles permanently at its spawn point.
        self.waypoints = waypoints if waypoints else [
            [x - 110.0, y], [x, y - 110.0], [x + 110.0, y], [x, y + 110.0]
        ]
        self.current_wp_idx = 0
        self.last_known_player_pos = None
        self.alert_timer = 0.0
        self.has_los_to_player = False

        # Periodic Sector Sweep / Active Hunt Timer
        self.hunt_timer = random.uniform(3.0, 7.0)
        self.hunt_target = None

        # Burst fire AI controller
        self.burst_count = 0
        self.burst_limit = random.randint(3, 5)
        self.burst_pause = 0.0

        # Visuals & audio
        self.walk_time = 0.0
        self.melee_timer = 0.0
        self.footstep_dist = 0.0
        self.FOOTSTEP_STEP = 50.0

    def get_hitbox(self):
        return pygame.Rect(
            int(self.pos[0] - self.hitbox_size // 2),
            int(self.pos[1] - self.hitbox_size // 2),
            self.hitbox_size,
            self.hitbox_size
        )

    def start_melee_anim(self, duration=0.22):
        self.melee_timer = duration

    def update(self, dt, player, map_manager, bullets, effect_manager, audio_manager):
        """Main AI thinking, perception, movement, and combat logic."""
        if not self.alive:
            return

        self.machine_gun.update(dt)
        self.bayonet.update(dt)
        if self.melee_timer > 0:
            self.melee_timer -= dt
        if self.burst_pause > 0:
            self.burst_pause -= dt

        if not player.alive:
            self._patrol_logic(dt, map_manager, audio_manager, player.pos)
            return

        # 1. Perception & Line-of-Sight
        dx = player.pos[0] - self.pos[0]
        dy = player.pos[1] - self.pos[1]
        dist_to_player = math.hypot(dx, dy)
        angle_to_player = math.degrees(math.atan2(dy, dx))

        # Check line-of-sight through map obstacles
        los_clear = map_manager.has_line_of_sight(self.pos, player.pos)
        angle_diff = (angle_to_player - self.angle_deg + 180) % 360 - 180

        # Detection conditions:
        # - Direct vision cone: within 520px and within 110 degree cone with clear LOS
        # - Close proximity alert: within 130px with clear LOS
        can_see_player = los_clear and (
            (dist_to_player < 520.0 and abs(angle_diff) < 65.0)
            or dist_to_player < 130.0
        )

        if can_see_player:
            if not self.has_los_to_player:
                # Target newly acquired: play tactical alert chirp
                audio_manager.play_spatial('alert', self.pos, player.pos, base_volume=0.8)
            self.has_los_to_player = True
            self.last_known_player_pos = [player.pos[0], player.pos[1]]
            self.alert_timer = 4.0  # Remember player for 4 seconds after losing sight
        else:
            self.has_los_to_player = False
            if self.alert_timer > 0:
                self.alert_timer -= dt
                if self.alert_timer <= 0:
                    self.last_known_player_pos = None

        # 2. Combat Decision & State Execution
        if dist_to_player <= 65.0 and los_clear:
            # Melee strike range! Execute Bayonet charge
            self._turn_towards(angle_to_player, rate=360.0 * dt)
            self.bayonet.strike(
                attacker=self,
                targets=[player],
                effect_manager=effect_manager,
                audio_manager=audio_manager,
                listener_pos=player.pos,
                is_player=False,
                map_manager=map_manager
            )
        elif self.has_los_to_player:
            # Ranged combat with Machine Gun
            self._turn_towards(angle_to_player, rate=280.0 * dt)

            # Fire in tactical bursts
            if self.burst_pause <= 0 and abs(angle_diff) < 25.0:
                if self.machine_gun.fire(
                    shooter=self,
                    bullet_list=bullets,
                    effect_manager=effect_manager,
                    audio_manager=audio_manager,
                    listener_pos=player.pos,
                    is_player=False
                ):
                    self.burst_count += 1
                    if self.burst_count >= self.burst_limit:
                        self.burst_count = 0
                        self.burst_limit = random.randint(3, 6)
                        self.burst_pause = random.uniform(0.35, 0.75)

            # Tactical repositioning: keep combat distance (~200-350px)
            if dist_to_player > 240.0:
                self._move_towards(player.pos[0], player.pos[1], self.chase_speed, dt, map_manager, audio_manager, player.pos)
            elif dist_to_player < 140.0:
                # Back away slightly while firing
                self._move_towards(self.pos[0] - dx, self.pos[1] - dy, self.patrol_speed * 0.8, dt, map_manager, audio_manager, player.pos)
        elif self.last_known_player_pos is not None:
            # Active Chase / Investigate position
            self._move_towards(
                self.last_known_player_pos[0],
                self.last_known_player_pos[1],
                self.chase_speed,
                dt,
                map_manager,
                audio_manager,
                player.pos
            )
            dist_to_last = math.hypot(
                self.last_known_player_pos[0] - self.pos[0],
                self.last_known_player_pos[1] - self.pos[1]
            )
            if dist_to_last < 45.0:
                self.last_known_player_pos = None
        else:
            # Active Sector Sweep & Hunting: Periodically branch out to sweep player's sector
            self.hunt_timer -= dt
            if self.hunt_timer <= 0:
                self.hunt_timer = random.uniform(6.0, 11.0)
                # Sweep toward general vicinity of player
                ox = random.uniform(-140.0, 140.0)
                oy = random.uniform(-140.0, 140.0)
                self.last_known_player_pos = [player.pos[0] + ox, player.pos[1] + oy]
                self.alert_timer = 5.0
            else:
                # Continuous dynamic waypoint patrol
                self._patrol_logic(dt, map_manager, audio_manager, player.pos)

    def hear_sound(self, sound_pos, max_dist=750.0):
        """Alerts enemy to nearby gunfire or loud noise, drawing them toward the source."""
        if not self.alive or self.has_los_to_player:
            return False
        dist = math.hypot(sound_pos[0] - self.pos[0], sound_pos[1] - self.pos[1])
        if dist <= max_dist:
            self.last_known_player_pos = [float(sound_pos[0]), float(sound_pos[1])]
            self.alert_timer = 6.0
            return True
        return False

    def _patrol_logic(self, dt, map_manager, audio_manager, player_pos):
        if not self.waypoints:
            return
        target_wp = self.waypoints[self.current_wp_idx]
        dist = math.hypot(target_wp[0] - self.pos[0], target_wp[1] - self.pos[1])
        if dist < 32.0:
            self.current_wp_idx = (self.current_wp_idx + 1) % len(self.waypoints)
        else:
            self._move_towards(target_wp[0], target_wp[1], self.patrol_speed, dt, map_manager, audio_manager, player_pos)

    def _turn_towards(self, target_angle, rate):
        diff = (target_angle - self.angle_deg + 180) % 360 - 180
        if abs(diff) <= rate:
            self.angle_deg = target_angle
        else:
            self.angle_deg += math.copysign(rate, diff)

    def _move_towards(self, tx, ty, speed, dt, map_manager, audio_manager, listener_pos):
        dx = tx - self.pos[0]
        dy = ty - self.pos[1]
        dist = math.hypot(dx, dy)
        if dist <= 0.001:
            return

        target_angle = math.degrees(math.atan2(dy, dx))
        self._turn_towards(target_angle, rate=320.0 * dt)

        vx = (dx / dist) * speed
        vy = (dy / dist) * speed

        hitbox = self.get_hitbox()
        new_x, new_y = map_manager.resolve_movement(hitbox, vx * dt, vy * dt)
        step_dist = math.hypot(new_x - self.pos[0], new_y - self.pos[1])

        self.pos[0] = new_x
        self.pos[1] = new_y
        self.walk_time += dt

        # Spatial footstep sound
        self.footstep_dist += step_dist
        if self.footstep_dist >= self.FOOTSTEP_STEP:
            audio_manager.play_spatial('footstep', self.pos, listener_pos, base_volume=0.45)
            self.footstep_dist = 0.0

    def take_damage(self, damage, attacker_type=None, is_melee=False):
        """Inflicts configurable difficulty damage on the enemy AI."""
        if not self.alive:
            return

        self.hp = max(0, self.hp - damage)
        if self.hp <= 0:
            self.alive = False

    def draw(self, surface, sprite_bank, camera_offset=(0, 0)):
        if not self.alive:
            return

        state = 'melee' if self.melee_timer > 0 else ('walk' if self.has_los_to_player or self.last_known_player_pos else 'idle')
        sprite = sprite_bank.get_sprite('enemy', state, self.walk_time)
        draw_rotated_sprite(surface, sprite, self.angle_deg, self.pos, camera_offset)
