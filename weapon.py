"""
weapon.py - Combat weapons system: Machine Gun (ranged) and Bayonet (melee).
Enforces cooldowns, instakill melee logic, muzzle flashes, and sound triggers.
"""

import math
import random
from bullet import Bullet


class MachineGun:
    """Ranged automatic weapon with unlimited ammo, moderate fire rate and 1 damage per hit."""

    def __init__(self, cooldown=0.13, spread_deg=2.5, projectile_speed=850.0):
        self.cooldown = cooldown
        self.spread_deg = spread_deg
        self.projectile_speed = projectile_speed
        self.timer = 0.0

    def update(self, dt):
        if self.timer > 0:
            self.timer -= dt

    def can_fire(self):
        return self.timer <= 0

    def fire(self, shooter, bullet_list, effect_manager, audio_manager, listener_pos, is_player=False):
        """Fires a bullet projectile from the weapon barrel tip."""
        if not self.can_fire():
            return False

        self.timer = self.cooldown

        # Calculate gun barrel muzzle tip position
        rad = math.radians(shooter.angle_deg)
        barrel_offset_forward = 32.0
        barrel_offset_side = 4.0  # Gun is held slightly on the right side
        tip_x = (
            shooter.pos[0]
            + math.cos(rad) * barrel_offset_forward
            - math.sin(rad) * barrel_offset_side
        )
        tip_y = (
            shooter.pos[1]
            + math.sin(rad) * barrel_offset_forward
            + math.cos(rad) * barrel_offset_side
        )

        # Apply slight spread
        spread = (random.random() * 2.0 - 1.0) * self.spread_deg
        bullet_angle = shooter.angle_deg + spread

        if hasattr(shooter, 'shots_fired'):
            shooter.shots_fired += 1

        # Spawn bullet
        b = Bullet(
            x=tip_x,
            y=tip_y,
            angle_deg=bullet_angle,
            owner=shooter.team,
            speed=self.projectile_speed,
            damage=1,
            shooter=shooter
        )
        bullet_list.append(b)

        # Muzzle flash effect
        effect_manager.add_muzzle_flash(tip_x, tip_y, shooter.angle_deg)

        # Audio trigger
        if is_player:
            audio_manager.play('gunshot', volume=0.85)
        else:
            audio_manager.play_spatial('gunshot', shooter.pos, listener_pos, base_volume=0.8)

        return True


class Bayonet:
    """Close-quarters combat melee attack. Instakill (10 damage / 1-hit kill on contact)."""

    def __init__(self, cooldown=0.55, strike_range=68.0, strike_arc_deg=85.0, damage=10):
        self.cooldown = cooldown
        self.range = strike_range
        self.arc_deg = strike_arc_deg
        self.damage = damage
        self.timer = 0.0

    def update(self, dt):
        if self.timer > 0:
            self.timer -= dt

    def can_strike(self):
        return self.timer <= 0

    def strike(self, attacker, targets, effect_manager, audio_manager, listener_pos, is_player=False):
        """Executes a close-range melee thrust/slash."""
        if not self.can_strike():
            return 0

        self.timer = self.cooldown
        attacker.start_melee_anim(duration=0.22)

        # Compute slash position centered in front of attacker
        rad = math.radians(attacker.angle_deg)
        slash_x = attacker.pos[0] + math.cos(rad) * (self.range * 0.6)
        slash_y = attacker.pos[1] + math.sin(rad) * (self.range * 0.6)

        # Visual slash arc effect
        effect_manager.add_melee_slash(
            attacker.pos[0],
            attacker.pos[1],
            attacker.angle_deg,
            self.range,
            is_player=is_player
        )

        # Slash whoosh sound
        if is_player:
            audio_manager.play('knife_slash', volume=1.0)
        else:
            audio_manager.play_spatial('knife_slash', attacker.pos, listener_pos, base_volume=0.95)

        hits = 0
        for target in targets:
            if not target.alive:
                continue

            dx = target.pos[0] - attacker.pos[0]
            dy = target.pos[1] - attacker.pos[1]
            dist = math.hypot(dx, dy)

            # Check distance to target center (accounting for entity radius ~20)
            if dist <= self.range + 20.0:
                target_angle = math.degrees(math.atan2(dy, dx))
                angle_diff = (target_angle - attacker.angle_deg + 180) % 360 - 180

                if abs(angle_diff) <= self.arc_deg * 0.5:
                    # Instakill strike! Deals 10 damage
                    target.take_damage(self.damage, attacker_type=attacker.team, is_melee=True)
                    if not target.alive and hasattr(attacker, 'melee_kills'):
                        attacker.melee_kills += 1
                    effect_manager.add_blood_splatter(target.pos[0], target.pos[1], attacker.angle_deg, count=25)
                    effect_manager.add_screen_shake(amplitude=6.0, duration=0.2)

                    # Knife impact sound
                    if is_player:
                        audio_manager.play('knife_hit', volume=1.0)
                    else:
                        audio_manager.play_spatial('knife_hit', target.pos, listener_pos, base_volume=1.0)

                    hits += 1

        return hits
