"""
sprites.py - High-fidelity procedural 2D top-down military soldier sprite generator.
Produces 2D sprite images for Player (Blue) and AI Enemies (Red), complete with
tactical gear, weapons, hands, helmets, drop shadows, and melee animations.
"""

import math
import pygame


SKIN_PALETTES = {
    'NAVY': {
        'id': 'NAVY',
        'name': "Tactical Navy",
        'desc': "Special ops midnight blue fatigues",
        'c_camo': (30, 60, 110),
        'c_vest': (18, 35, 65),
        'c_pouch': (45, 80, 140),
        'c_helmet': (35, 85, 160),
        'c_goggles': (0, 220, 255),
        'c_skin': (215, 175, 140),
        'c_glove': (25, 30, 40),
        'accent_color': (0, 180, 255),
    },
    'CAMO': {
        'id': 'CAMO',
        'name': "Tactical Camo",
        'desc': "Woodland ghillie & reinforced olive kevlar",
        'c_camo': (45, 75, 40),
        'c_vest': (25, 45, 22),
        'c_pouch': (70, 100, 50),
        'c_helmet': (50, 85, 45),
        'c_goggles': (140, 255, 60),
        'c_skin': (215, 175, 140),
        'c_glove': (30, 38, 28),
        'accent_color': (100, 220, 80),
    },
    'CYBER': {
        'id': 'CYBER',
        'name': "Cyber Cyan",
        'desc': "High-tech synth armor & luminescent visor",
        'c_camo': (15, 40, 60),
        'c_vest': (10, 24, 38),
        'c_pouch': (0, 180, 210),
        'c_helmet': (20, 60, 85),
        'c_goggles': (0, 255, 240),
        'c_skin': (220, 185, 150),
        'c_glove': (15, 20, 28),
        'accent_color': (0, 240, 255),
    },
    'FLAME': {
        'id': 'FLAME',
        'name': "Flame Red",
        'desc': "Arid combat fatigues & molten ember visor",
        'c_camo': (110, 60, 30),
        'c_vest': (65, 35, 18),
        'c_pouch': (160, 90, 40),
        'c_helmet': (140, 75, 35),
        'c_goggles': (255, 140, 20),
        'c_skin': (215, 175, 140),
        'c_glove': (40, 30, 25),
        'accent_color': (255, 120, 40),
    },
    'SILVER': {
        'id': 'SILVER',
        'name': "Aurora Silver",
        'desc': "Titanium alloy armor & violet prism optics",
        'c_camo': (115, 125, 140),
        'c_vest': (65, 72, 85),
        'c_pouch': (150, 160, 175),
        'c_helmet': (140, 150, 165),
        'c_goggles': (200, 130, 255),
        'c_skin': (220, 180, 150),
        'c_glove': (35, 38, 45),
        'accent_color': (200, 140, 255),
    },
}

ENEMY_PALETTE = {
    'c_camo': (120, 30, 30),
    'c_vest': (70, 15, 15),
    'c_pouch': (150, 45, 45),
    'c_helmet': (175, 40, 40),
    'c_goggles': (255, 60, 40),
    'c_skin': (210, 170, 135),
    'c_glove': (30, 25, 25),
}


def _create_base_soldier_surface(team='blue', state='idle', anim_frame=0.0, skin='NAVY', weapon='MACHINE_GUN'):
    """
    Renders a detailed top-down soldier onto a 32-bit RGBA Surface.
    Soldier faces RIGHT (0 degrees / positive X axis) by default.
    Dimensions: 64x64 surface with origin centered at (32, 32).
    """
    surf = pygame.Surface((64, 64), pygame.SRCALPHA)

    # Color palettes
    if team == 'blue' or team == 'player':
        pal = SKIN_PALETTES.get(skin, SKIN_PALETTES['NAVY'])
    else:  # 'red' or 'enemy'
        pal = ENEMY_PALETTE

    c_camo = pal['c_camo']
    c_vest = pal['c_vest']
    c_pouch = pal['c_pouch']
    c_helmet = pal['c_helmet']
    c_goggles = pal['c_goggles']
    c_skin = pal['c_skin']
    c_glove = pal['c_glove']

    c_steel = (180, 185, 195)
    c_gun = (25, 25, 30)
    c_gun_metal = (55, 60, 65)

    cx, cy = 32, 32

    # 1. Drop shadow
    shadow_surf = pygame.Surface((64, 64), pygame.SRCALPHA)
    pygame.draw.ellipse(shadow_surf, (0, 0, 0, 90), (14, 20, 36, 26))
    surf.blit(shadow_surf, (0, 0))

    # 2. Boots / Feet
    walk_offset = math.sin(anim_frame * 12.0) * 4.0 if state == 'walk' else 0.0
    pygame.draw.ellipse(surf, (20, 20, 25), (cx - 6 - walk_offset, cy - 18, 12, 7))
    pygame.draw.ellipse(surf, (20, 20, 25), (cx - 6 + walk_offset, cy + 11, 12, 7))

    # 3. Torso & Uniform Base
    pygame.draw.ellipse(surf, c_camo, (cx - 15, cy - 14, 26, 28))
    pygame.draw.ellipse(surf, c_vest, (cx - 13, cy - 12, 22, 24))
    pygame.draw.rect(surf, c_pouch, (cx - 4, cy - 10, 5, 6), border_radius=2)
    pygame.draw.rect(surf, c_pouch, (cx - 4, cy + 4, 5, 6), border_radius=2)

    # 4. Arms and Hands
    if state == 'melee':
        jab_dist = 12.0
        pygame.draw.line(surf, c_camo, (cx, cy - 9), (cx + 16 + jab_dist, cy - 3), 5)
        pygame.draw.line(surf, c_camo, (cx, cy + 9), (cx + 16 + jab_dist, cy + 3), 5)

        pygame.draw.circle(surf, c_glove, (int(cx + 15 + jab_dist), int(cy - 2)), 4)
        pygame.draw.circle(surf, c_glove, (int(cx + 15 + jab_dist), int(cy + 2)), 4)

        knife_tip = (cx + 28 + jab_dist, cy)
        blade_pts = [
            (cx + 16 + jab_dist, cy - 3),
            (knife_tip[0], knife_tip[1]),
            (cx + 16 + jab_dist, cy + 3),
        ]
        pygame.draw.polygon(surf, c_steel, blade_pts)
        pygame.draw.line(surf, (255, 255, 255), (cx + 16 + jab_dist, cy), knife_tip, 1)
    else:
        # Gun holding stance based on weapon
        if weapon == 'SNIPER':
            # Sniper Rifle: Longer sleek barrel, optical scope, forward grip
            pygame.draw.line(surf, c_camo, (cx - 4, cy - 10), (cx + 14, cy - 6), 5)
            pygame.draw.line(surf, c_camo, (cx - 6, cy + 10), (cx + 6, cy + 4), 5)

            # Sniper Body & Long Barrel
            pygame.draw.rect(surf, (20, 22, 26), (cx + 2, cy - 3, 15, 5), border_radius=1)
            pygame.draw.rect(surf, (45, 50, 58), (cx + 17, cy - 2, 17, 3))
            # Muzzle brake
            pygame.draw.rect(surf, (70, 75, 85), (cx + 33, cy - 3, 4, 5))
            # Scope on top
            pygame.draw.rect(surf, (30, 35, 42), (cx + 6, cy - 6, 11, 3), border_radius=1)
            pygame.draw.circle(surf, (0, 220, 255), (cx + 16, cy - 5), 1)

            pygame.draw.circle(surf, c_glove, (cx + 6, cy + 3), 4)
            pygame.draw.circle(surf, c_glove, (cx + 16, cy - 4), 4)

        elif weapon == 'ROCKET':
            # Rocket Launcher: Shoulder tube weapon
            pygame.draw.line(surf, c_camo, (cx - 4, cy - 10), (cx + 12, cy - 6), 5)
            pygame.draw.line(surf, c_camo, (cx - 6, cy + 10), (cx + 4, cy + 6), 5)

            # Heavy OD/Charcoal Launcher Tube
            pygame.draw.rect(surf, (35, 42, 38), (cx - 4, cy - 5, 34, 9), border_radius=2)
            pygame.draw.rect(surf, (60, 70, 65), (cx + 27, cy - 6, 4, 11))
            pygame.draw.rect(surf, (25, 28, 25), (cx - 6, cy - 6, 4, 11))
            # Rocket warhead tip peek
            pygame.draw.polygon(surf, (220, 60, 40), [
                (cx + 31, cy - 3),
                (cx + 35, cy),
                (cx + 31, cy + 3)
            ])

            pygame.draw.circle(surf, c_glove, (cx + 6, cy + 4), 4)
            pygame.draw.circle(surf, c_glove, (cx + 18, cy - 3), 4)

        else:
            # Standard Machine Gun
            pygame.draw.line(surf, c_camo, (cx - 4, cy - 10), (cx + 12, cy - 6), 5)
            pygame.draw.line(surf, c_camo, (cx - 6, cy + 10), (cx + 6, cy + 4), 5)

            pygame.draw.rect(surf, c_gun, (cx + 2, cy - 3, 16, 6), border_radius=1)
            pygame.draw.rect(surf, c_gun_metal, (cx + 18, cy - 2, 9, 4))
            pygame.draw.rect(surf, (15, 15, 18), (cx + 6, cy + 2, 4, 5))
            pygame.draw.polygon(surf, c_steel, [
                (cx + 27, cy - 2),
                (cx + 33, cy),
                (cx + 27, cy + 1)
            ])

            pygame.draw.circle(surf, c_glove, (cx + 6, cy + 3), 4)
            pygame.draw.circle(surf, c_glove, (cx + 14, cy - 4), 4)

    # 5. Head and Helmet
    pygame.draw.circle(surf, c_skin, (cx - 2, cy), 8)
    pygame.draw.circle(surf, c_helmet, (cx - 2, cy), 9)
    pygame.draw.circle(surf, (255, 255, 255, 40), (cx - 4, cy - 3), 4)

    # Helmet Brim / Visor
    pygame.draw.arc(surf, (10, 10, 15), (cx - 10, cy - 9, 18, 18), -0.7, 0.7, 3)

    # Tactical Goggles / Glowing Visor
    pygame.draw.rect(surf, c_goggles, (cx + 5, cy - 4, 3, 8), border_radius=1)
    pygame.draw.circle(surf, (255, 255, 255), (cx + 6, cy - 1), 1)

    return surf


def _create_death_surface(team='blue', skin='NAVY'):
    """Renders a fallen soldier decal for death animations."""
    surf = pygame.Surface((64, 64), pygame.SRCALPHA)
    if team == 'blue' or team == 'player':
        pal = SKIN_PALETTES.get(skin, SKIN_PALETTES['NAVY'])
    else:
        pal = ENEMY_PALETTE

    c_camo = pal['c_camo']
    c_vest = pal['c_vest']
    c_helmet = pal['c_helmet']

    pygame.draw.ellipse(surf, (130, 15, 15, 180), (12, 16, 40, 32))
    pygame.draw.circle(surf, (110, 10, 10, 200), (32, 32), 12)

    pygame.draw.ellipse(surf, c_camo, (18, 22, 28, 20))
    pygame.draw.ellipse(surf, c_vest, (20, 24, 20, 16))

    pygame.draw.circle(surf, c_helmet, (42, 26), 7)

    pygame.draw.rect(surf, (25, 25, 25), (14, 38, 18, 4))
    pygame.draw.polygon(surf, (180, 185, 195), [(32, 38), (38, 40), (32, 42)])

    return surf


class SpriteBank:
    """Pre-renders and caches animated soldier sprites for all skins, teams, and weapons."""

    def __init__(self):
        self.cache = {}
        # Pre-populate enemy sprites
        self.sprites = {
            'player': {},
            'enemy': {
                'idle': _create_base_soldier_surface('red', 'idle'),
                'melee': _create_base_soldier_surface('red', 'melee'),
                'walk_0': _create_base_soldier_surface('red', 'walk', 0.0),
                'walk_1': _create_base_soldier_surface('red', 'walk', 1.57),
                'dead': _create_death_surface('red'),
            }
        }
        # Pre-render default player sprites for NAVY
        for sk in SKIN_PALETTES.keys():
            self._precache_skin(sk)

    def _precache_skin(self, skin_id):
        for wp in ['MACHINE_GUN', 'SNIPER', 'ROCKET']:
            k_idle = f"{skin_id}_{wp}_idle"
            k_w0 = f"{skin_id}_{wp}_walk_0"
            k_w1 = f"{skin_id}_{wp}_walk_1"
            k_melee = f"{skin_id}_{wp}_melee"
            self.cache[k_idle] = _create_base_soldier_surface('blue', 'idle', 0.0, skin=skin_id, weapon=wp)
            self.cache[k_w0] = _create_base_soldier_surface('blue', 'walk', 0.0, skin=skin_id, weapon=wp)
            self.cache[k_w1] = _create_base_soldier_surface('blue', 'walk', 1.57, skin=skin_id, weapon=wp)
            self.cache[k_melee] = _create_base_soldier_surface('blue', 'melee', 0.0, skin=skin_id, weapon=wp)
        self.cache[f"{skin_id}_dead"] = _create_death_surface('blue', skin=skin_id)

    def get_sprite(self, team, state, anim_time=0.0, skin='NAVY', weapon='MACHINE_GUN'):
        """Returns the appropriate sprite surface for team, state, skin, and weapon."""
        if team == 'enemy' or team == 'red':
            team_dict = self.sprites['enemy']
            if state == 'walk':
                frame_key = 'walk_0' if int(anim_time * 6.0) % 2 == 0 else 'walk_1'
                return team_dict[frame_key]
            elif state == 'melee':
                return team_dict['melee']
            elif state == 'dead':
                return team_dict['dead']
            return team_dict['idle']

        # Player skin lookup
        if state == 'dead':
            ck = f"{skin}_dead"
            if ck not in self.cache:
                self.cache[ck] = _create_death_surface('blue', skin=skin)
            return self.cache[ck]

        if state == 'walk':
            sub = 'walk_0' if int(anim_time * 6.0) % 2 == 0 else 'walk_1'
        elif state == 'melee':
            sub = 'melee'
        else:
            sub = 'idle'

        ckey = f"{skin}_{weapon}_{sub}"
        if ckey not in self.cache:
            af = 0.0 if sub != 'walk_1' else 1.57
            self.cache[ckey] = _create_base_soldier_surface('blue', state, af, skin=skin, weapon=weapon)
        return self.cache[ckey]


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
