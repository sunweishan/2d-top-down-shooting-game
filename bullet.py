"""
bullet.py - Bullet projectile kinematics, tracer rendering, and collision detection.
Handles continuous collision ray-checks against walls and combat targets to prevent tunneling.
"""

import math
import pygame


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
    """High-speed projectile dealing 1 damage per hit."""

    def __init__(self, x, y, angle_deg, owner='player', speed=850.0, damage=1, shooter=None):
        self.pos = [float(x), float(y)]
        self.prev_pos = [float(x), float(y)]
        self.angle_deg = angle_deg
        rad = math.radians(angle_deg)
        self.vel = [math.cos(rad) * speed, math.sin(rad) * speed]
        self.owner = owner  # 'player' or 'enemy'
        self.damage = damage
        self.shooter = shooter
        self.alive = True
        self.lifetime = 1.6  # Seconds before despawning

    def update(self, dt, map_manager, targets, effect_manager, audio_manager, listener_pos):
        """Updates position, performs collision sweeps, and triggers hits/sparks."""
        if not self.alive:
            return

        self.lifetime -= dt
        if self.lifetime <= 0:
            self.alive = False
            return

        self.prev_pos = [self.pos[0], self.pos[1]]
        self.pos[0] += self.vel[0] * dt
        self.pos[1] += self.vel[1] * dt

        # 1. Check collision against map obstacle walls
        wall_hit, wall_pt = self._check_wall_collision(map_manager)
        if wall_hit:
            self.alive = False
            self.pos = [wall_pt[0], wall_pt[1]]
            effect_manager.add_wall_hit(self.pos[0], self.pos[1], self.angle_deg)
            audio_manager.play_spatial('hit_wall', self.pos, listener_pos, base_volume=0.85)
            return

        # 2. Check collision against target characters
        for target in targets:
            if not target.alive:
                continue
            # Distance from target center to bullet segment
            target_hit, hit_pt = line_intersects_rect(
                (self.prev_pos[0], self.prev_pos[1]),
                (self.pos[0], self.pos[1]),
                target.get_hitbox()
            )
            if target_hit:
                self.alive = False
                self.pos = [hit_pt[0], hit_pt[1]]
                if self.shooter and hasattr(self.shooter, 'shots_hit'):
                    self.shooter.shots_hit += 1
                target.take_damage(self.damage, attacker_type=self.owner)
                effect_manager.add_blood_splatter(self.pos[0], self.pos[1], self.angle_deg)
                audio_manager.play_spatial('hit_body', self.pos, listener_pos, base_volume=0.9)
                return

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
        """Renders illuminated tracer line."""
        sx1 = int(self.prev_pos[0] - camera_offset[0])
        sy1 = int(self.prev_pos[1] - camera_offset[1])
        sx2 = int(self.pos[0] - camera_offset[0])
        sy2 = int(self.pos[1] - camera_offset[1])

        # Outer glowing tracer (orange/amber)
        tracer_color = (255, 180, 50) if self.owner == 'player' else (255, 90, 60)
        pygame.draw.line(surface, tracer_color, (sx1, sy1), (sx2, sy2), 3)
        # Inner white-hot core
        pygame.draw.line(surface, (255, 255, 220), (sx1, sy1), (sx2, sy2), 1)
