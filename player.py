"""
player.py - Player character entity (Blue Unit).
Handles WASD movement, mouse aiming, machine gun shooting, bayonet melee attack,
health tracking (10 HP), and footstep audio triggers.
"""

import math
import pygame
from sprites import draw_rotated_sprite
from weapon import MachineGun, SniperRifle, RocketLauncher, Bayonet


class Player:
    """Player controlled soldier (Team Blue). Dies after HP pool is empty OR 1 knife attack."""

    def __init__(self, x, y, max_hp=10, weapon_type='MACHINE_GUN', skin_id='NAVY'):
        self.pos = [float(x), float(y)]
        self.speed = 260.0
        self.hp = max_hp
        self.max_hp = max_hp
        self.alive = True
        self.team = 'player'
        self.angle_deg = 0.0

        # Customization
        self.weapon_type = weapon_type
        self.skin_id = skin_id

        # Stats tracking for scoring
        self.shots_fired = 0
        self.shots_hit = 0
        self.melee_kills = 0

        # Weapons
        if weapon_type == 'SNIPER':
            self.primary_weapon = SniperRifle()
        elif weapon_type == 'ROCKET':
            self.primary_weapon = RocketLauncher()
        else:
            self.primary_weapon = MachineGun(cooldown=0.12, spread_deg=2.5, projectile_speed=900.0)
        self.machine_gun = self.primary_weapon  # Backwards compatibility alias
        self.bayonet = Bayonet(cooldown=0.55, strike_range=68.0, strike_arc_deg=85.0, damage=10)

        # Movement & state
        self.velocity = [0.0, 0.0]
        self.state = 'idle'
        self.walk_time = 0.0
        self.melee_timer = 0.0
        self.footstep_dist = 0.0
        self.FOOTSTEP_STEP = 42.0  # Pixels traversed per footstep sound

        # Hitbox size (32x32)
        self.hitbox_size = 30

    def get_hitbox(self):
        """Returns pygame.Rect bounding box centered at pos."""
        return pygame.Rect(
            int(self.pos[0] - self.hitbox_size // 2),
            int(self.pos[1] - self.hitbox_size // 2),
            self.hitbox_size,
            self.hitbox_size
        )

    def start_melee_anim(self, duration=0.22):
        self.melee_timer = duration

    def handle_input(self, keys, mouse_buttons, mouse_world_pos, dt, bullets, enemies,
                     effect_manager, audio_manager, map_manager=None):
        """Processes keyboard and mouse inputs for moving, aiming, and attacking."""
        if not self.alive:
            self.velocity = [0.0, 0.0]
            return

        # 1. Aim towards mouse cursor
        dx = mouse_world_pos[0] - self.pos[0]
        dy = mouse_world_pos[1] - self.pos[1]
        self.angle_deg = math.degrees(math.atan2(dy, dx))

        # 2. WASD Movement
        mx = 0.0
        my = 0.0
        if keys[pygame.K_w] or keys[pygame.K_UP]:
            my -= 1.0
        if keys[pygame.K_s] or keys[pygame.K_DOWN]:
            my += 1.0
        if keys[pygame.K_a] or keys[pygame.K_LEFT]:
            mx -= 1.0
        if keys[pygame.K_d] or keys[pygame.K_RIGHT]:
            mx += 1.0

        # Diagonal normalization
        dist = math.hypot(mx, my)
        if dist > 0.0:
            self.velocity[0] = (mx / dist) * self.speed
            self.velocity[1] = (my / dist) * self.speed
        else:
            self.velocity[0] = 0.0
            self.velocity[1] = 0.0

        # 3. Primary Weapon Fire (Left Mouse Button)
        if mouse_buttons[0]:
            self.primary_weapon.fire(
                shooter=self,
                bullet_list=bullets,
                effect_manager=effect_manager,
                audio_manager=audio_manager,
                listener_pos=self.pos,
                is_player=True
            )

        # 4. Bayonet Melee Attack (Space or F key)
        if keys[pygame.K_SPACE] or keys[pygame.K_f]:
            self.bayonet.strike(
                attacker=self,
                targets=enemies,
                effect_manager=effect_manager,
                audio_manager=audio_manager,
                listener_pos=self.pos,
                is_player=True,
                map_manager=map_manager
            )

    def update(self, dt, map_manager, audio_manager):
        """Updates position, wall collision sliding, cooldowns, and footstep audio."""
        if not self.alive:
            return

        # Update weapons
        self.primary_weapon.update(dt)
        self.bayonet.update(dt)

        # Update melee animation state
        if self.melee_timer > 0:
            self.melee_timer -= dt

        # Resolve position and obstacle sliding
        dx = self.velocity[0] * dt
        dy = self.velocity[1] * dt

        if abs(dx) > 0.001 or abs(dy) > 0.001:
            hitbox = self.get_hitbox()
            new_cx, new_cy = map_manager.resolve_movement(hitbox, dx, dy)

            # Actual moved distance
            moved_dist = math.hypot(new_cx - self.pos[0], new_cy - self.pos[1])
            self.pos[0] = new_cx
            self.pos[1] = new_cy

            self.walk_time += dt
            self.state = 'walk'

            # Footstep sound accumulation
            self.footstep_dist += moved_dist
            if self.footstep_dist >= self.FOOTSTEP_STEP:
                audio_manager.play('footstep', volume=0.6)
                self.footstep_dist = 0.0
        else:
            self.state = 'idle'
            self.footstep_dist = 0.0

    def take_damage(self, damage, attacker_type=None, is_melee=False):
        """Inflicts damage on the player until their selected HP pool is empty."""
        if not self.alive:
            return

        self.hp = max(0, self.hp - damage)
        if self.hp <= 0:
            self.alive = False

    def heal(self, amount):
        """Restores player HP/lives up to max_hp cap. Returns actual restored amount."""
        if not self.alive or self.hp >= self.max_hp:
            return 0
        old_hp = self.hp
        self.hp = min(self.max_hp, self.hp + amount)
        return self.hp - old_hp

    def draw(self, surface, sprite_bank, camera_offset=(0, 0)):
        """Renders player sprite rotated based on facing angle with selected skin and weapon."""
        if not self.alive:
            return

        state = 'melee' if self.melee_timer > 0 else self.state
        sprite = sprite_bank.get_sprite('player', state, self.walk_time, skin=self.skin_id, weapon=self.weapon_type)
        draw_rotated_sprite(surface, sprite, self.angle_deg, self.pos, camera_offset)
