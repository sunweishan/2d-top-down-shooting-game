"""
effects.py - Lighting glow halos, particle systems, death animations, and visual polish.
Implements radial alpha halo blending around characters, wall sparks, blood splatters, and screen shake.
"""

import math
import random
import pygame


def _create_radial_glow_mask(radius, color, intensity=0.45, center_alpha=None):
    """Generates a smooth radial gradient halo surface for dynamic additive lighting."""
    if center_alpha is not None:
        intensity = center_alpha / 255.0
    size = radius * 2
    small_size = 64
    small_surf = pygame.Surface((small_size, small_size))
    small_surf.fill((0, 0, 0))
    s_radius = small_size / 2.0
    for y in range(small_size):
        for x in range(small_size):
            d = math.hypot(x - s_radius + 0.5, y - s_radius + 0.5)
            if d < s_radius:
                factor = ((1.0 - (d / s_radius)) ** 2.0) * intensity
                r = min(255, int(color[0] * factor))
                g = min(255, int(color[1] * factor))
                b = min(255, int(color[2] * factor))
                small_surf.set_at((x, y), (r, g, b))
    return pygame.transform.smoothscale(small_surf, (size, size))


class SparkParticle:
    """Concrete impact spark from bullet collisions."""

    def __init__(self, x, y, base_angle_deg):
        self.x = x
        self.y = y
        spread = (random.random() * 2.0 - 1.0) * 60.0
        angle_rad = math.radians(base_angle_deg + 180.0 + spread)
        speed = random.uniform(80.0, 260.0)
        self.vx = math.cos(angle_rad) * speed
        self.vy = math.sin(angle_rad) * speed
        self.lifetime = random.uniform(0.12, 0.28)
        self.max_lifetime = self.lifetime
        self.color = random.choice([
            (255, 240, 160),
            (255, 180, 50),
            (255, 120, 30)
        ])

    def update(self, dt):
        self.x += self.vx * dt
        self.y += self.vy * dt
        self.vx *= 0.92
        self.vy *= 0.92
        self.lifetime -= dt

    def draw(self, surface, camera_offset):
        if self.lifetime <= 0:
            return
        sx = int(self.x - camera_offset[0])
        sy = int(self.y - camera_offset[1])
        alpha = max(0, min(255, int(255 * (self.lifetime / self.max_lifetime))))
        radius = max(1, int(2 * (self.lifetime / self.max_lifetime)))
        pygame.draw.circle(surface, self.color, (sx, sy), radius)


class BloodParticle:
    """Blood droplets emitted when an entity is hit."""

    def __init__(self, x, y, hit_angle_deg, is_melee=False):
        self.x = x
        self.y = y
        spread = (random.random() * 2.0 - 1.0) * (80.0 if is_melee else 45.0)
        angle_rad = math.radians(hit_angle_deg + spread)
        speed = random.uniform(60.0, 220.0) if not is_melee else random.uniform(100.0, 320.0)
        self.vx = math.cos(angle_rad) * speed
        self.vy = math.sin(angle_rad) * speed
        self.lifetime = random.uniform(0.18, 0.4)
        self.max_lifetime = self.lifetime
        self.size = random.randint(2, 4)
        self.color = random.choice([
            (160, 15, 15),
            (190, 25, 25),
            (120, 10, 10)
        ])

    def update(self, dt):
        self.x += self.vx * dt
        self.y += self.vy * dt
        self.vx *= 0.88
        self.vy *= 0.88
        self.lifetime -= dt

    def draw(self, surface, camera_offset):
        if self.lifetime <= 0:
            return
        sx = int(self.x - camera_offset[0])
        sy = int(self.y - camera_offset[1])
        pygame.draw.circle(surface, self.color, (sx, sy), self.size)


class BloodDecal:
    """Persistent ground blood splatter left by hits and casualties."""

    def __init__(self, x, y, radius=12):
        self.x = x
        self.y = y
        self.radius = radius
        self.alpha = 200
        self.lifetime = 25.0  # Lingers for 25 seconds
        self.color = (130 + random.randint(-15, 15), 15, 15)

    def update(self, dt):
        self.lifetime -= dt
        if self.lifetime < 5.0:
            self.alpha = max(0, int(200 * (self.lifetime / 5.0)))

    def draw(self, surface, camera_offset):
        if self.alpha <= 0:
            return
        sx = int(self.x - camera_offset[0])
        sy = int(self.y - camera_offset[1])
        decal_surf = pygame.Surface((self.radius * 2, self.radius * 2), pygame.SRCALPHA)
        pygame.draw.ellipse(
            decal_surf,
            (self.color[0], self.color[1], self.color[2], self.alpha),
            (0, 0, self.radius * 2, int(self.radius * 1.5))
        )
        surface.blit(decal_surf, (sx - self.radius, sy - int(self.radius * 0.75)))


class MuzzleFlash:
    """Instant bright flash at gun tip."""

    def __init__(self, x, y, angle_deg):
        self.x = x
        self.y = y
        self.angle_deg = angle_deg
        self.duration = 0.05
        self.timer = self.duration

    def update(self, dt):
        self.timer -= dt

    def draw(self, surface, camera_offset):
        if self.timer <= 0:
            return
        sx = int(self.x - camera_offset[0])
        sy = int(self.y - camera_offset[1])
        rad = math.radians(self.angle_deg)
        f_len = 12.0
        f_width = 5.0
        p1 = (sx + math.cos(rad) * f_len, sy + math.sin(rad) * f_len)
        p2 = (sx - math.sin(rad) * f_width, sy + math.cos(rad) * f_width)
        p3 = (sx + math.sin(rad) * f_width, sy - math.cos(rad) * f_width)
        pygame.draw.polygon(surface, (255, 245, 180), [p1, p2, p3])
        pygame.draw.circle(surface, (255, 255, 255), (sx, sy), 3)


class MeleeSlashVisual:
    """Curved animated slash arc / bayonet thrust streak."""

    def __init__(self, x, y, angle_deg, reach=65.0, is_player=True):
        self.x = x
        self.y = y
        self.angle_deg = angle_deg
        self.reach = reach
        self.is_player = is_player
        self.duration = 0.18
        self.timer = self.duration

    def update(self, dt):
        self.timer -= dt

    def draw(self, surface, camera_offset):
        if self.timer <= 0:
            return
        progress = 1.0 - (self.timer / self.duration)
        alpha = int(255 * (1.0 - progress))
        arc_color = (180, 230, 255, alpha) if self.is_player else (255, 120, 100, alpha)

        sx = int(self.x - camera_offset[0])
        sy = int(self.y - camera_offset[1])

        # Draw expanding blade swing polygon
        start_rad = math.radians(self.angle_deg - 40.0 + progress * 20.0)
        end_rad = math.radians(self.angle_deg + 40.0)
        r_inner = self.reach * 0.4
        r_outer = self.reach * (0.8 + 0.2 * progress)

        points = []
        steps = 6
        for i in range(steps + 1):
            cur_rad = start_rad + (end_rad - start_rad) * (i / steps)
            points.append((
                sx + math.cos(cur_rad) * r_outer,
                sy + math.sin(cur_rad) * r_outer
            ))
        for i in range(steps, -1, -1):
            cur_rad = start_rad + (end_rad - start_rad) * (i / steps)
            points.append((
                sx + math.cos(cur_rad) * r_inner,
                sy + math.sin(cur_rad) * r_inner
            ))

        if len(points) >= 3:
            slash_surf = pygame.Surface(surface.get_size(), pygame.SRCALPHA)
            pygame.draw.polygon(slash_surf, arc_color, points)
            surface.blit(slash_surf, (0, 0), special_flags=pygame.BLEND_ADD)


class DeathAnimation:
    """Dramatic collapse and defeat sequence when a soldier dies."""

    def __init__(self, x, y, team, angle_deg):
        self.x = x
        self.y = y
        self.team = team
        self.angle_deg = angle_deg
        self.duration = 1.2
        self.timer = self.duration
        self.rot_speed = random.choice([-180.0, 180.0])
        self.cur_angle = angle_deg

    def update(self, dt):
        self.timer -= dt
        if self.timer > 0.6:
            self.cur_angle += self.rot_speed * dt

    def draw(self, surface, sprite_bank, camera_offset):
        progress = 1.0 - (self.timer / self.duration)
        dead_sprite = sprite_bank.get_sprite(self.team, 'dead')

        sx = int(self.x - camera_offset[0])
        sy = int(self.y - camera_offset[1])

        # Rotation and alpha fade
        rotated = pygame.transform.rotate(dead_sprite, -self.cur_angle)
        rect = rotated.get_rect(center=(sx, sy))
        surface.blit(rotated, rect.topleft)


class ScorchDecal:
    """Dark charred blast crater on the ground."""
    def __init__(self, x, y, radius=32):
        self.x = x
        self.y = y
        self.radius = radius
        self.lifetime = 45.0

    def update(self, dt):
        self.lifetime -= dt

    def draw(self, surface, camera_offset):
        if self.lifetime <= 0:
            return
        sx = int(self.x - camera_offset[0])
        sy = int(self.y - camera_offset[1])
        surf = pygame.Surface((self.radius * 2, self.radius * 2), pygame.SRCALPHA)
        pygame.draw.circle(surf, (15, 12, 10, 160), (self.radius, self.radius), self.radius)
        pygame.draw.circle(surf, (8, 6, 5, 200), (self.radius, self.radius), int(self.radius * 0.6))
        surface.blit(surf, (sx - self.radius, sy - self.radius))


class ExplosionVisual:
    """Expanding fiery fireball, shockwave ring, and smoke cloud."""
    def __init__(self, x, y, max_radius=160):
        self.x = x
        self.y = y
        self.max_radius = max_radius
        self.duration = 0.45
        self.timer = self.duration
        self.particles = []
        for _ in range(26):
            angle = random.uniform(0, 2 * math.pi)
            spd = random.uniform(80, max_radius * 2.2)
            self.particles.append({
                'x': x,
                'y': y,
                'vx': math.cos(angle) * spd,
                'vy': math.sin(angle) * spd,
                'size': random.uniform(3, 7),
                'color': random.choice([(255, 240, 100), (255, 160, 30), (255, 70, 20), (140, 140, 140)])
            })

    def update(self, dt):
        self.timer -= dt
        for p in self.particles:
            p['x'] += p['vx'] * dt
            p['y'] += p['vy'] * dt
            p['vx'] *= 0.88
            p['vy'] *= 0.88

    def draw(self, surface, camera_offset):
        if self.timer <= 0:
            return
        sx = int(self.x - camera_offset[0])
        sy = int(self.y - camera_offset[1])
        progress = 1.0 - (self.timer / self.duration)
        cur_radius = int(self.max_radius * math.sin(progress * math.pi * 0.5))

        for p in self.particles:
            px = int(p['x'] - camera_offset[0])
            py = int(p['y'] - camera_offset[1])
            alpha = max(0, min(255, int(255 * (self.timer / self.duration))))
            sz = max(1, int(p['size'] * (self.timer / self.duration)))
            pygame.draw.circle(surface, p['color'], (px, py), sz)

        if cur_radius > 4:
            ring_surf = pygame.Surface((cur_radius * 2 + 8, cur_radius * 2 + 8), pygame.SRCALPHA)
            alpha = max(0, min(255, int(220 * (1.0 - progress))))
            pygame.draw.circle(ring_surf, (255, 180, 50, alpha), (cur_radius + 4, cur_radius + 4), cur_radius, width=max(2, int(6 * (1.0 - progress))))
            if progress < 0.6:
                pygame.draw.circle(ring_surf, (255, 255, 230, int(alpha * 0.8)), (cur_radius + 4, cur_radius + 4), int(cur_radius * 0.75), width=2)
            surface.blit(ring_surf, (sx - cur_radius - 4, sy - cur_radius - 4))


class EffectManager:
    """Coordinates lighting halos, particles, decals, screen shake, and death effects."""

    def __init__(self):
        self.sparks = []
        self.blood_particles = []
        self.blood_decals = []
        self.explosions = []
        self.muzzle_flashes = []
        self.slashes = []
        self.death_animations = []

        # Screen shake
        self.shake_amplitude = 0.0
        self.shake_timer = 0.0

        # Pre-rendered lighting glow masks for high performance
        self.player_glow_radius = 85
        self.player_glow = _create_radial_glow_mask(radius=self.player_glow_radius, color=(0, 150, 255), center_alpha=65)

        self.enemy_glow_radius = 75
        self.enemy_glow = _create_radial_glow_mask(radius=self.enemy_glow_radius, color=(255, 45, 30), center_alpha=55)

        self.flash_glow_radius = 50
        self.flash_glow = _create_radial_glow_mask(radius=self.flash_glow_radius, color=(255, 200, 60), center_alpha=95)

        self.bullet_glow_radius = 24
        self.bullet_glow = _create_radial_glow_mask(radius=self.bullet_glow_radius, color=(255, 170, 40), center_alpha=40)

    def add_screen_shake(self, amplitude=5.0, duration=0.2):
        self.shake_amplitude = max(self.shake_amplitude, amplitude)
        self.shake_timer = max(self.shake_timer, duration)

    def get_screen_shake_offset(self):
        if self.shake_timer > 0:
            ox = (random.random() * 2.0 - 1.0) * self.shake_amplitude
            oy = (random.random() * 2.0 - 1.0) * self.shake_amplitude
            return ox, oy
        return 0.0, 0.0

    def add_wall_hit(self, x, y, bullet_angle_deg):
        """Creates ricochet sparks on solid obstacle collision."""
        for _ in range(8):
            self.sparks.append(SparkParticle(x, y, bullet_angle_deg))

    def add_blood_splatter(self, x, y, hit_angle_deg, count=12, is_melee=False):
        """Creates blood particles and deposits ground decals."""
        for _ in range(count):
            self.blood_particles.append(BloodParticle(x, y, hit_angle_deg, is_melee=is_melee))
        # Add ground blood decal
        self.blood_decals.append(BloodDecal(x, y, radius=random.randint(10, 18)))

    def add_muzzle_flash(self, x, y, angle_deg):
        self.muzzle_flashes.append(MuzzleFlash(x, y, angle_deg))

    def add_melee_slash(self, x, y, angle_deg, reach=65.0, is_player=True):
        self.slashes.append(MeleeSlashVisual(x, y, angle_deg, reach, is_player))

    def add_explosion(self, x, y, radius=160):
        """Creates high-yield blast shockwave, fireball debris, screen shake, and scorch decal."""
        self.explosions.append(ExplosionVisual(x, y, max_radius=radius))
        self.blood_decals.append(ScorchDecal(x, y, radius=int(radius * 0.4)))
        self.add_screen_shake(amplitude=9.5, duration=0.38)

    def add_death_effect(self, x, y, team, angle_deg):
        self.death_animations.append(DeathAnimation(x, y, team, angle_deg))
        # Generous blood pool at death site
        for _ in range(3):
            ox = random.uniform(-10, 10)
            oy = random.uniform(-10, 10)
            self.blood_decals.append(BloodDecal(x + ox, y + oy, radius=random.randint(14, 22)))

    def update(self, dt):
        # Update shake
        if self.shake_timer > 0:
            self.shake_timer -= dt
            if self.shake_timer <= 0:
                self.shake_amplitude = 0.0

        # Update all particles
        for p in self.sparks:
            p.update(dt)
        self.sparks = [p for p in self.sparks if p.lifetime > 0]

        for p in self.blood_particles:
            p.update(dt)
        self.blood_particles = [p for p in self.blood_particles if p.lifetime > 0]

        for d in self.blood_decals:
            d.update(dt)
        self.blood_decals = [d for d in self.blood_decals if d.lifetime > 0]

        for exp in self.explosions:
            exp.update(dt)
        self.explosions = [exp for exp in self.explosions if exp.timer > 0]

        for f in self.muzzle_flashes:
            f.update(dt)
        self.muzzle_flashes = [f for f in self.muzzle_flashes if f.timer > 0]

        for s in self.slashes:
            s.update(dt)
        self.slashes = [s for s in self.slashes if s.timer > 0]

        for d in self.death_animations:
            d.update(dt)
        # Retain finished death animations as ground corpses (cap list to last 20)
        if len(self.death_animations) > 20:
            self.death_animations = self.death_animations[-20:]

    def draw_decals(self, surface, camera_offset):
        """Draws ground decals before drawing entities (so soldiers walk over bloodstains)."""
        for d in self.blood_decals:
            d.draw(surface, camera_offset)

    def draw_particles(self, surface, camera_offset):
        """Draws dynamic sparks, slashes, explosions, and blood in front of entities."""
        for p in self.sparks:
            p.draw(surface, camera_offset)
        for p in self.blood_particles:
            p.draw(surface, camera_offset)
        for exp in self.explosions:
            exp.draw(surface, camera_offset)
        for f in self.muzzle_flashes:
            f.draw(surface, camera_offset)
        for s in self.slashes:
            s.draw(surface, camera_offset)

    def draw_corpses(self, surface, sprite_bank, camera_offset):
        for d in self.death_animations:
            d.draw(surface, sprite_bank, camera_offset)

    def render_lighting_halos(self, surface, player, enemies, bullets, camera_offset):
        """
        Renders semi-transparent glowing halos around characters and projectiles
        using BLEND_ADD for vibrant dynamic lighting.
        """
        cam_x, cam_y = camera_offset
        sw, sh = surface.get_size()

        # 1. Player Glow Halo (Cyan-Blue)
        if player.alive:
            px = int(player.pos[0] - cam_x - self.player_glow_radius)
            py = int(player.pos[1] - cam_y - self.player_glow_radius)
            surface.blit(self.player_glow, (px, py), special_flags=pygame.BLEND_ADD)

        # 2. Enemy Glow Halos (Crimson-Red)
        for enemy in enemies:
            if enemy.alive:
                ex = int(enemy.pos[0] - cam_x - self.enemy_glow_radius)
                ey = int(enemy.pos[1] - cam_y - self.enemy_glow_radius)
                # Only blit if on screen
                if -120 <= ex <= sw + 120 and -120 <= ey <= sh + 120:
                    surface.blit(self.enemy_glow, (ex, ey), special_flags=pygame.BLEND_ADD)

        # 3. Bullet Glow Points
        for b in bullets:
            if b.alive:
                bx = int(b.pos[0] - cam_x - self.bullet_glow_radius)
                by = int(b.pos[1] - cam_y - self.bullet_glow_radius)
                surface.blit(self.bullet_glow, (bx, by), special_flags=pygame.BLEND_ADD)

        # 4. Muzzle Flash Glow
        for f in self.muzzle_flashes:
            if f.timer > 0:
                fx = int(f.x - cam_x - self.flash_glow_radius)
                fy = int(f.y - cam_y - self.flash_glow_radius)
                surface.blit(self.flash_glow, (fx, fy), special_flags=pygame.BLEND_ADD)
