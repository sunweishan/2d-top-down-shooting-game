"""
sprites.py - High-fidelity procedural 2D top-down military soldier sprite generator.
Produces 2D sprite images for Player (Blue) and AI Enemies (Red), complete with
tactical gear, weapons, hands, helmets, drop shadows, and melee animations.
"""

import math
import pygame


def _create_base_soldier_surface(team='blue', state='idle', anim_frame=0.0):
    """
    Renders a detailed top-down soldier onto a 32-bit RGBA Surface.
    Soldier faces RIGHT (0 degrees / positive X axis) by default.
    
    Dimensions: 64x64 surface with origin centered at (32, 32).
    """
    surf = pygame.Surface((64, 64), pygame.SRCALPHA)

    # Color palettes
    if team == 'blue':
        c_camo = (30, 60, 110)        # Navy blue uniform
        c_vest = (18, 35, 65)         # Dark navy kevlar vest
        c_pouch = (45, 80, 140)       # Vest magazine pouches
        c_helmet = (35, 85, 160)      # Blue tactical helmet
        c_goggles = (0, 220, 255)     # Glowing cyan visor / night-vision
        c_skin = (215, 175, 140)      # Hand/skin tone
        c_glove = (25, 30, 40)        # Tactical gloves
    else:  # 'red'
        c_camo = (120, 30, 30)        # Crimson combat uniform
        c_vest = (70, 15, 15)         # Heavy dark red vest
        c_pouch = (150, 45, 45)       # Red vest webbing
        c_helmet = (175, 40, 40)      # Crimson helmet
        c_goggles = (255, 60, 40)     # Menacing red visor
        c_skin = (210, 170, 135)
        c_glove = (30, 25, 25)

    c_steel = (180, 185, 195)
    c_gun = (25, 25, 30)
    c_gun_metal = (55, 60, 65)

    cx, cy = 32, 32

    # 1. Drop shadow (subtle depth underneath entity)
    shadow_surf = pygame.Surface((64, 64), pygame.SRCALPHA)
    pygame.draw.ellipse(shadow_surf, (0, 0, 0, 90), (14, 20, 36, 26))
    surf.blit(shadow_surf, (0, 0))

    # 2. Boots / Feet (Animated during walking)
    walk_offset = math.sin(anim_frame * 12.0) * 4.0 if state == 'walk' else 0.0
    # Left foot (upper in top-down)
    pygame.draw.ellipse(surf, (20, 20, 25), (cx - 6 - walk_offset, cy - 18, 12, 7))
    # Right foot (lower in top-down)
    pygame.draw.ellipse(surf, (20, 20, 25), (cx - 6 + walk_offset, cy + 11, 12, 7))

    # 3. Torso & Uniform Base
    # Shoulders ellipse
    pygame.draw.ellipse(surf, c_camo, (cx - 15, cy - 14, 26, 28))
    # Tactical Vest (MOLLE armor)
    pygame.draw.ellipse(surf, c_vest, (cx - 13, cy - 12, 22, 24))
    # Vest Pouches
    pygame.draw.rect(surf, c_pouch, (cx - 4, cy - 10, 5, 6), border_radius=2)
    pygame.draw.rect(surf, c_pouch, (cx - 4, cy + 4, 5, 6), border_radius=2)

    # 4. Arms and Hands
    if state == 'melee':
        # Melee jab: Right arm thrusts forward holding combat bayonet
        jab_dist = 12.0
        # Arms extended forward
        pygame.draw.line(surf, c_camo, (cx, cy - 9), (cx + 16 + jab_dist, cy - 3), 5)
        pygame.draw.line(surf, c_camo, (cx, cy + 9), (cx + 16 + jab_dist, cy + 3), 5)

        # Hands
        pygame.draw.circle(surf, c_glove, (int(cx + 15 + jab_dist), int(cy - 2)), 4)
        pygame.draw.circle(surf, c_glove, (int(cx + 15 + jab_dist), int(cy + 2)), 4)

        # Bayonet Blade (Razor steel dagger extending ahead)
        knife_tip = (cx + 28 + jab_dist, cy)
        blade_pts = [
            (cx + 16 + jab_dist, cy - 3),
            (knife_tip[0], knife_tip[1]),
            (cx + 16 + jab_dist, cy + 3),
        ]
        pygame.draw.polygon(surf, c_steel, blade_pts)
        pygame.draw.line(surf, (255, 255, 255), (cx + 16 + jab_dist, cy), knife_tip, 1)  # Blade edge gleam
    else:
        # Standard tactical stance: Holding Machine Gun with both hands
        # Left arm (supports barrel)
        pygame.draw.line(surf, c_camo, (cx - 4, cy - 10), (cx + 12, cy - 6), 5)
        # Right arm (grips trigger)
        pygame.draw.line(surf, c_camo, (cx - 6, cy + 10), (cx + 6, cy + 4), 5)

        # Machine Gun Body
        # Receiver / Stock
        pygame.draw.rect(surf, c_gun, (cx + 2, cy - 3, 16, 6), border_radius=1)
        # Gun Barrel
        pygame.draw.rect(surf, c_gun_metal, (cx + 18, cy - 2, 9, 4))
        # Magazine
        pygame.draw.rect(surf, (15, 15, 18), (cx + 6, cy + 2, 4, 5))
        # Attached Bayonet Lug (Silver blade tip mounted under barrel)
        pygame.draw.polygon(surf, c_steel, [
            (cx + 27, cy - 2),
            (cx + 33, cy),
            (cx + 27, cy + 1)
        ])

        # Hands gripping gun
        pygame.draw.circle(surf, c_glove, (cx + 6, cy + 3), 4)    # Trigger hand
        pygame.draw.circle(surf, c_glove, (cx + 14, cy - 4), 4)   # Barrel hand

    # 5. Head and Helmet
    # Head neck base
    pygame.draw.circle(surf, c_skin, (cx - 2, cy), 8)
    # Tactical Helmet (PASGT / FAST dome)
    pygame.draw.circle(surf, c_helmet, (cx - 2, cy), 9)
    pygame.draw.circle(surf, (255, 255, 255, 40), (cx - 4, cy - 3), 4)  # Highlight

    # Helmet Brim / Visor
    pygame.draw.arc(surf, (10, 10, 15), (cx - 10, cy - 9, 18, 18), -0.7, 0.7, 3)

    # Tactical Goggles / Glowing Visor
    pygame.draw.rect(surf, c_goggles, (cx + 5, cy - 4, 3, 8), border_radius=1)
    # Lens glow highlight
    pygame.draw.circle(surf, (255, 255, 255), (cx + 6, cy - 1), 1)

    return surf


def _create_death_surface(team='blue'):
    """Renders a fallen soldier decal for death animations."""
    surf = pygame.Surface((64, 64), pygame.SRCALPHA)
    c_camo = (25, 45, 80) if team == 'blue' else (90, 25, 25)
    c_vest = (15, 25, 45) if team == 'blue' else (50, 15, 15)
    c_helmet = (30, 60, 110) if team == 'blue' else (120, 30, 30)

    # Blood pool underneath
    pygame.draw.ellipse(surf, (130, 15, 15, 180), (12, 16, 40, 32))
    pygame.draw.circle(surf, (110, 10, 10, 200), (32, 32), 12)

    # Crumpled body
    pygame.draw.ellipse(surf, c_camo, (18, 22, 28, 20))
    pygame.draw.ellipse(surf, c_vest, (20, 24, 20, 16))

    # Helmet knocked off slightly
    pygame.draw.circle(surf, c_helmet, (42, 26), 7)

    # Fallen weapon on ground
    pygame.draw.rect(surf, (25, 25, 25), (14, 38, 18, 4))
    pygame.draw.polygon(surf, (180, 185, 195), [(32, 38), (38, 40), (32, 42)])

    return surf


class SpriteBank:
    """Pre-renders and caches all animated soldier sprites to eliminate runtime overhead."""

    def __init__(self):
        self.sprites = {
            'player': {
                'idle': _create_base_soldier_surface('blue', 'idle'),
                'melee': _create_base_soldier_surface('blue', 'melee'),
                'walk_0': _create_base_soldier_surface('blue', 'walk', 0.0),
                'walk_1': _create_base_soldier_surface('blue', 'walk', 1.57),
                'dead': _create_death_surface('blue'),
            },
            'enemy': {
                'idle': _create_base_soldier_surface('red', 'idle'),
                'melee': _create_base_soldier_surface('red', 'melee'),
                'walk_0': _create_base_soldier_surface('red', 'walk', 0.0),
                'walk_1': _create_base_soldier_surface('red', 'walk', 1.57),
                'dead': _create_death_surface('red'),
            }
        }

    def get_sprite(self, team, state, anim_time=0.0):
        """Returns the appropriate sprite surface for team and state."""
        team_dict = self.sprites.get(team, self.sprites['enemy'])
        if state == 'walk':
            # 4Hz walking cadence between walk_0 and walk_1
            frame_key = 'walk_0' if int(anim_time * 6.0) % 2 == 0 else 'walk_1'
            return team_dict[frame_key]
        elif state == 'melee':
            return team_dict['melee']
        elif state == 'dead':
            return team_dict['dead']
        return team_dict['idle']


# Global singleton instance
_SPRITE_BANK = None


def get_sprite_bank():
    global _SPRITE_BANK
    if _SPRITE_BANK is None:
        _SPRITE_BANK = SpriteBank()
    return _SPRITE_BANK


def draw_rotated_sprite(surface, sprite, angle_deg, center_pos, camera_offset=(0, 0)):
    """
    Draws sprite rotated by angle_deg (in degrees) centered at world coordinates center_pos.
    camera_offset: (offset_x, offset_y)
    """
    # Pygame rotates counter-clockwise; standard angle is in degrees
    rotated = pygame.transform.rotate(sprite, -angle_deg)
    screen_x = center_pos[0] - camera_offset[0]
    screen_y = center_pos[1] - camera_offset[1]
    rect = rotated.get_rect(center=(int(screen_x), int(screen_y)))
    surface.blit(rotated, rect.topleft)
