"""
supply.py - Collectible supply stations and field medkits.
Restores player HP up to the selected difficulty cap with visual bobbing, green halo glow, and pickup chime.
"""

import math
import pygame


def _create_medkit_glow(radius=40):
    """Generates a soft green radial glow for medkits."""
    size = radius * 2
    small_size = 32
    small_surf = pygame.Surface((small_size, small_size))
    small_surf.fill((0, 0, 0))
    s_radius = small_size / 2.0
    for y in range(small_size):
        for x in range(small_size):
            d = math.hypot(x - s_radius + 0.5, y - s_radius + 0.5)
            if d < s_radius:
                factor = ((1.0 - (d / s_radius)) ** 2.0) * 0.4
                r = int(20 * factor)
                g = int(255 * factor)
                b = int(120 * factor)
                small_surf.set_at((x, y), (r, g, b))
    return pygame.transform.smoothscale(small_surf, (size, size))


class Medkit:
    """Field medical kit restoring player HP/Lives up to maximum capacity."""

    def __init__(self, x, y, heal_amount=5):
        self.pos = [float(x), float(y)]
        self.heal_amount = heal_amount
        self.radius = 20.0
        self.collected = False
        self.bob_time = 0.0
        self.glow_radius = 45
        self.glow_mask = _create_medkit_glow(self.glow_radius)

    def update(self, dt):
        self.bob_time += dt

    def check_pickup(self, player, audio_manager, ui_manager):
        """Checks collision with player and applies healing unconditionally."""
        if self.collected or not player.alive:
            return False

        # Distance check — pickup is unconditional regardless of current HP
        dist = math.hypot(player.pos[0] - self.pos[0], player.pos[1] - self.pos[1])
        if dist <= self.radius + 16.0:
            restored = player.heal(self.heal_amount)
            self.collected = True
            audio_manager.play('medkit_pickup', volume=0.9)
            ui_manager.show_notification(f"SUPPLY ACQUIRED: +{restored} HP RESTORED")
            return True
        return False

    def draw(self, surface, camera_offset):
        if self.collected:
            return

        # Bobbing offset
        bob_y = math.sin(self.bob_time * 3.5) * 3.5
        sx = int(self.pos[0] - camera_offset[0])
        sy = int(self.pos[1] + bob_y - camera_offset[1])

        # 1. Soft green glow halo
        gx = sx - self.glow_radius
        gy = sy - self.glow_radius
        surface.blit(self.glow_mask, (gx, gy), special_flags=pygame.BLEND_ADD)

        # 2. Shadow underneath
        shadow_rect = pygame.Rect(sx - 12, int(self.pos[1] - camera_offset[1] + 8), 24, 8)
        shadow_surf = pygame.Surface((24, 8), pygame.SRCALPHA)
        pygame.draw.ellipse(shadow_surf, (0, 0, 0, 110), (0, 0, 24, 8))
        surface.blit(shadow_surf, shadow_rect.topleft)

        # 3. Medical field case (White container with dark green border)
        case_rect = pygame.Rect(sx - 12, sy - 9, 24, 18)
        pygame.draw.rect(surface, (240, 245, 250), case_rect, border_radius=3)
        pygame.draw.rect(surface, (30, 120, 60), case_rect, 2, border_radius=3)

        # 4. Vibrant Red/Green Cross symbol on lid
        # Horizontal bar
        pygame.draw.rect(surface, (0, 200, 90), (sx - 6, sy - 2, 12, 4))
        # Vertical bar
        pygame.draw.rect(surface, (0, 200, 90), (sx - 2, sy - 6, 4, 12))


class SupplyManager:
    """Manages medkit supply stations across the map."""

    def __init__(self, stations=None, heal_amount=5):
        self.medkits = []
        self.heal_amount = heal_amount
        if stations:
            for x, y in stations:
                self.medkits.append(Medkit(x, y, heal_amount))

    def add_medkit(self, x, y):
        """Dynamically spawns a new Medkit (e.g., Hard mode enemy death drop)."""
        self.medkits.append(Medkit(x, y, self.heal_amount))

    def update(self, dt, player, audio_manager, ui_manager):
        for mk in self.medkits:
            if not mk.collected:
                mk.update(dt)
                mk.check_pickup(player, audio_manager, ui_manager)

    def draw(self, surface, camera_offset):
        for mk in self.medkits:
            mk.draw(surface, camera_offset)
