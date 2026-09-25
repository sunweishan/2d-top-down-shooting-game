"""
bullet.py - Bullet projectile kinematics, tracer rendering, and collision detection.
Handles continuous collision ray-checks against walls and combat targets to prevent tunneling.
"""

import math
import pygame
from effects import SparkParticle


def line_intersects_rect(p1, p2, rect):
    """
    Checks if line segment p1->p2 intersects an axis-aligned bounding box rect (pygame.Rect).
    Returns (hit, hit_point) where hit is bool and hit_point is (x, y) or None.
    """
    rx, ry, rw, rh = rect.x, rect.y, rect.width, rect.height
    rect_lines = [
        ((rx, ry), (rx + rw, ry)),             # Top
        ((rx + rw, ry), (rx + rw, ry + rh)),   # Right
        ((rx + rw, ry + rh), (rx, ry + rh)),   # Bottom
        ((rx, ry + rh), (rx, ry))              # Left
    ]

    closest_hit = None
    min_dist_sq = float('inf')

    for lp1, lp2 in rect_lines:
        hit, pt = line_segment_intersection(p1, p2, lp1, lp2)
        if hit:
            d_sq = (pt[0] - p1[0]) ** 2 + (pt[1] - p1[1]) ** 2
            if d_sq < min_dist_sq:
                min_dist_sq = d_sq
                closest_hit = pt

    if closest_hit:
        return True, closest_hit
    # Also check if p1 or p2 starts inside the rect
    if rect.collidepoint(p1):
        return True, p1
    if rect.collidepoint(p2):
        return True, p2

    return False, None


def line_segment_intersection(p1, p2, p3, p4):
    """Calculates 2D line segment intersection between p1-p2 and p3-p4."""
    x1, y1 = p1
    x2, y2 = p2
    x3, y3 = p3
    x4, y4 = p4

    denom = (y4 - y3) * (x2 - x1) - (x4 - x3) * (y2 - y1)
    if abs(denom) < 1e-9:
        return False, None

    ua = ((x4 - x3) * (y1 - y3) - (y4 - y3) * (x1 - x3)) / denom
    ub = ((x2 - x1) * (y1 - y3) - (y2 - y1) * (x1 - x3)) / denom

    if 0.0 <= ua <= 1.0 and 0.0 <= ub <= 1.0:
        ix = x1 + ua * (x2 - x1)
        iy = y1 + ua * (y2 - y1)
        return True, (ix, iy)

    return False, None


class Bullet:
    """High-speed projectile dealing damage, with support for wall piercing and rocket room clearance."""

    def __init__(self, x, y, angle_deg, owner='player', speed=850.0, damage=1, shooter=None,
                 wall_pierce=False, is_sniper=False, is_rocket=False):
        self.pos = [float(x), float(y)]
        self.prev_pos = [float(x), float(y)]
        self.angle_deg = angle_deg
        rad = math.radians(angle_deg)
        self.vel = [math.cos(rad) * speed, math.sin(rad) * speed]
        self.owner = owner  # 'player' or 'enemy'
        self.damage = damage
        self.shooter = shooter
        self.wall_pierce = wall_pierce
        self.is_sniper = is_sniper
        self.is_rocket = is_rocket
        self.alive = True
        self.lifetime = 2.2 if is_sniper else (2.0 if is_rocket else 1.6)
        self.smoke_timer = 0.0

    def update(self, dt, map_manager, targets, effect_manager, audio_manager, listener_pos):
        """Updates position, performs collision sweeps, and triggers hits/sparks."""
        if not self.alive:
            return

        self.lifetime -= dt
        if self.lifetime <= 0:
            self.alive = False
            if self.is_rocket:
                self._detonate_rocket(map_manager, targets, effect_manager, audio_manager, listener_pos)
            return

        self.prev_pos = [self.pos[0], self.pos[1]]
        self.pos[0] += self.vel[0] * dt
        self.pos[1] += self.vel[1] * dt

        # Rocket engine smoke/flame particle trail
        if self.is_rocket:
            self.smoke_timer += dt
            if self.smoke_timer >= 0.03:
                self.smoke_timer = 0.0
                rad = math.radians(self.angle_deg)
                back_x = self.pos[0] - math.cos(rad) * 10.0
                back_y = self.pos[1] - math.sin(rad) * 10.0
                effect_manager.sparks.append(SparkParticle(back_x, back_y, self.angle_deg - 180.0))

        # 1. Check collision against map obstacle walls. Only explicitly
        # wall-piercing player projectiles (sniper/rocket) may continue.
        wall_hit, wall_pt = self._check_wall_collision(map_manager)
        if wall_hit:
            breached_walls = []
            if self.is_rocket and self.owner == 'player' and hasattr(map_manager, 'breach_walls'):
                breached_walls = map_manager.breach_walls(self.prev_pos, self.pos)
                for _, breach_point in breached_walls:
                    if breach_point is not None:
                        effect_manager.add_wall_hit(breach_point[0], breach_point[1], self.angle_deg)

                if breached_walls:
                    # The rocket has entered the next space through the new
                    # opening. Detonate just inside it so every enemy in that
                    # room is cleared, even when the projectile misses them.
                    travel_distance = math.hypot(self.vel[0], self.vel[1])
                    if travel_distance > 0:
                        push_distance = 56.0
                        self.pos[0] += (self.vel[0] / travel_distance) * push_distance
                        self.pos[1] += (self.vel[1] / travel_distance) * push_distance
                    self.alive = False
                    self._detonate_rocket(map_manager, targets, effect_manager, audio_manager, listener_pos)
                    return

                # The perimeter is indestructible. A rocket hitting it stops
                # and detonates instead of bypassing the arena boundary.
                self.alive = False
                self.pos = [wall_pt[0], wall_pt[1]]
                self._detonate_rocket(map_manager, targets, effect_manager, audio_manager, listener_pos)
                return

            if self.wall_pierce:
                # Sniper and player-fired rockets penetrate walls. Rockets
                # also remove the crossed interior wall above.
                pass
            else:
                # Machine-gun and enemy rounds stop at the first wall, so they
                # cannot damage a target on the opposite side.
                self.alive = False
                self.pos = [wall_pt[0], wall_pt[1]]
                effect_manager.add_wall_hit(self.pos[0], self.pos[1], self.angle_deg)
                audio_manager.play_spatial('hit_wall', self.pos, listener_pos, base_volume=0.85)
                return

        # 2. Check collision against target characters
        for target in targets:
            if not target.alive:
                continue
            target_hit, hit_pt = line_intersects_rect(
                (self.prev_pos[0], self.prev_pos[1]),
                (self.pos[0], self.pos[1]),
                target.get_hitbox()
            )
            if target_hit:
                self.pos = [hit_pt[0], hit_pt[1]]
                if self.is_rocket:
                    self.alive = False
                    self._detonate_rocket(map_manager, targets, effect_manager, audio_manager, listener_pos)
                    return
                else:
                    self.alive = False
                    if self.shooter and hasattr(self.shooter, 'shots_hit'):
                        self.shooter.shots_hit += 1
                    target.take_damage(self.damage, attacker_type=self.owner)
                    effect_manager.add_blood_splatter(self.pos[0], self.pos[1], self.angle_deg, count=18 if self.is_sniper else 12)
                    audio_manager.play_spatial('hit_body', self.pos, listener_pos, base_volume=0.9)
                    return

    def _detonate_rocket(self, map_manager, targets, effect_manager, audio_manager, listener_pos):
        """Detonates rocket with massive explosion and eliminates all hostiles in the affected room/space."""
        audio_manager.play_spatial('explosion', self.pos, listener_pos, base_volume=1.0)
        effect_manager.add_explosion(self.pos[0], self.pos[1], radius=180)
        if hasattr(map_manager, 'clear_room_enemies'):
            map_manager.clear_room_enemies(self.pos, targets, effect_manager, shooter=self.shooter)

    def _check_wall_collision(self, map_manager):
        """Finds closest wall intersection along trajectory from prev_pos to pos."""
        p1 = (self.prev_pos[0], self.prev_pos[1])
        p2 = (self.pos[0], self.pos[1])

        closest_hit = None
        min_dist_sq = float('inf')

        for wall in map_manager.walls:
            hit, pt = line_intersects_rect(p1, p2, wall)
            if hit:
                d_sq = (pt[0] - p1[0]) ** 2 + (pt[1] - p1[1]) ** 2
                if d_sq < min_dist_sq:
                    min_dist_sq = d_sq
                    closest_hit = pt

        if closest_hit:
            return True, closest_hit
        return False, None

    def draw(self, surface, camera_offset=(0, 0)):
        """Renders illuminated projectile tracer or rocket sprite."""
        sx1 = int(self.prev_pos[0] - camera_offset[0])
        sy1 = int(self.prev_pos[1] - camera_offset[1])
        sx2 = int(self.pos[0] - camera_offset[0])
        sy2 = int(self.pos[1] - camera_offset[1])

        if self.is_rocket:
            # Render high-explosive rocket missile
            rad = math.radians(self.angle_deg)
            cos_a = math.cos(rad)
            sin_a = math.sin(rad)
            tip_x = sx2
            tip_y = sy2
            tail_x = int(sx2 - cos_a * 16.0)
            tail_y = int(sy2 - sin_a * 16.0)

            # Fiery rocket exhaust glow
            pygame.draw.line(surface, (255, 100, 20), (tail_x, tail_y), (int(tail_x - cos_a * 8), int(tail_y - sin_a * 8)), 4)
            pygame.draw.line(surface, (255, 240, 120), (tail_x, tail_y), (int(tail_x - cos_a * 4), int(tail_y - sin_a * 4)), 2)
            # Rocket body
            pygame.draw.line(surface, (45, 55, 45), (tail_x, tail_y), (tip_x, tip_y), 4)
            # Red warhead tip
            pygame.draw.circle(surface, (255, 50, 40), (tip_x, tip_y), 3)

        elif self.is_sniper:
            # High-velocity sniper piercing beam (electric cyan / neon blue)
            pygame.draw.line(surface, (0, 180, 255), (sx1, sy1), (sx2, sy2), 4)
            pygame.draw.line(surface, (180, 245, 255), (sx1, sy1), (sx2, sy2), 2)
            pygame.draw.circle(surface, (255, 255, 255), (sx2, sy2), 3)

        else:
            # Standard machine gun tracer
            tracer_color = (255, 180, 50) if self.owner == 'player' else (255, 90, 60)
            pygame.draw.line(surface, tracer_color, (sx1, sy1), (sx2, sy2), 3)
            pygame.draw.line(surface, (255, 255, 220), (sx1, sy1), (sx2, sy2), 1)
