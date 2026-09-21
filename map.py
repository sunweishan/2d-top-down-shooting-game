"""
map.py - Predefined Map environments, obstacle collisions, LOS raycasting, and cover rendering.
Supports 5 distinct maps with scaled enemy counts and supply stations.
"""

import math
import pygame
from bullet import line_intersects_rect


MAP_METADATA = {
    1: {
        'name': "MAP 1: CQB BUNKER",
        'size_label': "Small (1100x850)",
        'enemies_count': 3,
        'supplies_count': 0,
        'desc': "Tight labyrinth bunker. High hostility density. No medkits."
    },
    2: {
        'name': "MAP 2: INDUSTRIAL COMPOUND",
        'size_label': "Medium A (1600x1200)",
        'enemies_count': 5,
        'supplies_count': 2,
        'desc': "Four fortified sector rooms and central tactical courtyard."
    },
    3: {
        'name': "MAP 3: URBAN RUINS",
        'size_label': "Medium B (1600x1200)",
        'enemies_count': 5,
        'supplies_count': 2,
        'desc': "Long flanking streets, crumbling facades, and intersection cover."
    },
    4: {
        'name': "MAP 4: MILITARY AIRBASE",
        'size_label': "Large A (2200x1600)",
        'enemies_count': 7,
        'supplies_count': 3,
        'desc': "Expansive tarmac, aircraft hangars, and perimeter checkpoints."
    },
    5: {
        'name': "MAP 5: RESEARCH LABS",
        'size_label': "Large B (2400x1800)",
        'enemies_count': 7,
        'supplies_count': 4,
        'desc': "Sprawling underground bio-research corridors and reactor wings."
    },
}


class MapManager:
    """Manages arena geometry, obstacles, raycasts, and rendering for selected map."""

    def __init__(self, map_id=2):
        self.map_id = map_id
        meta = MAP_METADATA.get(map_id, MAP_METADATA[2])
        self.name = meta['name']
        self.description = meta['desc']
        self.walls = []
        self.cover_types = []
        self.supply_stations = []
        self.enemy_configs = []
        self.player_spawn = [100.0, 100.0]

        if map_id == 1:
            self._build_map_1_small()
        elif map_id == 2:
            self._build_map_2_medium_a()
        elif map_id == 3:
            self._build_map_3_medium_b()
        elif map_id == 4:
            self._build_map_4_large_a()
        elif map_id == 5:
            self._build_map_5_large_b()
        else:
            self._build_map_2_medium_a()

        self._pre_render_floor()

    def _add_obstacle(self, x, y, w, h, cover_type='concrete'):
        rect = pygame.Rect(x, y, w, h)
        self.walls.append(rect)
        self.cover_types.append((rect, cover_type))

    def _add_perimeter(self):
        self._add_obstacle(0, 0, self.width, 32, 'concrete')
        self._add_obstacle(0, self.height - 32, self.width, 32, 'concrete')
        self._add_obstacle(0, 0, 32, self.height, 'concrete')
        self._add_obstacle(self.width - 32, 0, 32, self.height, 'concrete')

    # -------------------------------------------------------------
    # MAP 1: Small CQB Bunker (1100x850) - 3 Enemies, 0 Supplies
    # -------------------------------------------------------------
    def _build_map_1_small(self):
        self.width = 1100
        self.height = 850
        self._add_perimeter()
        self.player_spawn = [80.0, 425.0]

        # Labyrinth dividing blast walls
        self._add_obstacle(220, 120, 24, 260, 'concrete')
        self._add_obstacle(220, 470, 24, 260, 'concrete')
        self._add_obstacle(440, 32, 24, 300, 'concrete')
        self._add_obstacle(440, 480, 24, 340, 'concrete')
        self._add_obstacle(660, 140, 24, 280, 'concrete')
        self._add_obstacle(660, 500, 24, 220, 'concrete')
        self._add_obstacle(860, 32, 24, 320, 'concrete')
        self._add_obstacle(860, 460, 24, 350, 'concrete')

        # Horizontal cross-corridor walls
        self._add_obstacle(244, 280, 120, 24, 'concrete')
        self._add_obstacle(320, 540, 120, 24, 'concrete')
        self._add_obstacle(684, 260, 100, 24, 'concrete')
        self._add_obstacle(760, 560, 100, 24, 'concrete')

        # Cover crates
        self._add_obstacle(130, 260, 45, 45, 'crate')
        self._add_obstacle(130, 560, 45, 45, 'crate')
        self._add_obstacle(340, 400, 50, 45, 'crate')
        self._add_obstacle(540, 240, 45, 45, 'crate')
        self._add_obstacle(540, 580, 45, 45, 'crate')
        self._add_obstacle(760, 400, 50, 45, 'crate')
        self._add_obstacle(970, 260, 45, 45, 'crate')
        self._add_obstacle(970, 580, 45, 45, 'crate')

        # 3 Enemy Spawns with Active Roaming Waypoints
        self.enemy_configs = [
            {'pos': [340, 180], 'waypoints': [[340, 180], [340, 680], [130, 425], [340, 180]]},
            {'pos': [760, 340], 'waypoints': [[760, 180], [760, 680], [550, 420], [760, 340]]},
            {'pos': [980, 420], 'waypoints': [[980, 160], [980, 680], [760, 340], [980, 160]]},
        ]
        self.supply_stations = []


    # -------------------------------------------------------------
    # MAP 2: Medium A - Industrial Compound (1600x1200) - 5 Enemies, 2 Supplies
    # -------------------------------------------------------------
    def _build_map_2_medium_a(self):
        self.width = 1600
        self.height = 1200
        self._add_perimeter()
        self.player_spawn = [120.0, 600.0]

        # NW HQ
        self._add_obstacle(180, 180, 260, 24, 'concrete')
        self._add_obstacle(180, 180, 24, 220, 'concrete')
        self._add_obstacle(180, 380, 160, 24, 'concrete')
        self._add_obstacle(420, 260, 20, 144, 'concrete')
        self._add_obstacle(260, 270, 70, 45, 'metal')

        # NE Armory
        self._add_obstacle(1120, 180, 280, 24, 'concrete')
        self._add_obstacle(1376, 180, 24, 220, 'concrete')
        self._add_obstacle(1240, 380, 160, 24, 'concrete')
        self._add_obstacle(1120, 260, 24, 144, 'concrete')
        self._add_obstacle(1200, 240, 55, 55, 'crate')

        # Center Plaza
        self._add_obstacle(680, 480, 40, 240, 'concrete')
        self._add_obstacle(880, 480, 40, 240, 'concrete')
        self._add_obstacle(720, 580, 160, 40, 'concrete')
        self._add_obstacle(540, 570, 50, 60, 'crate')
        self._add_obstacle(1010, 570, 50, 60, 'crate')

        # SW Power Substation
        self._add_obstacle(180, 800, 240, 24, 'concrete')
        self._add_obstacle(180, 800, 24, 220, 'concrete')
        self._add_obstacle(280, 996, 140, 24, 'concrete')
        self._add_obstacle(396, 880, 24, 140, 'concrete')
        self._add_obstacle(250, 870, 80, 55, 'metal')

        # SE Depot
        self._add_obstacle(1140, 800, 260, 24, 'concrete')
        self._add_obstacle(1376, 800, 24, 220, 'concrete')
        self._add_obstacle(1140, 996, 170, 24, 'concrete')
        self._add_obstacle(1140, 870, 24, 150, 'concrete')
        self._add_obstacle(1220, 870, 65, 45, 'crate')

        # Mid-Flank Barriers
        self._add_obstacle(480, 320, 120, 30, 'concrete')
        self._add_obstacle(1000, 320, 120, 30, 'concrete')
        self._add_obstacle(480, 850, 120, 30, 'concrete')
        self._add_obstacle(1000, 850, 120, 30, 'concrete')

        # 5 Enemies
        self.enemy_configs = [
            {'pos': [320, 240], 'waypoints': [[320, 240], [480, 480], [320, 480], [320, 240]]},
            {'pos': [1260, 260], 'waypoints': [[1260, 260], [1050, 480], [1260, 480], [1260, 260]]},
            {'pos': [800, 520], 'waypoints': [[800, 440], [800, 740], [600, 600], [1000, 600]]},
            {'pos': [320, 940], 'waypoints': [[320, 940], [480, 720], [320, 720], [320, 940]]},
            {'pos': [1260, 940], 'waypoints': [[1260, 940], [1050, 720], [1260, 720], [1260, 940]]},
        ]

        # 2 Supply Medkits
        self.supply_stations = [
            [220.0, 340.0],   # Inside NW HQ
            [1300.0, 920.0],  # Inside SE Depot
        ]

    # -------------------------------------------------------------
    # MAP 3: Medium B - Urban Ruins (1600x1200) - 5 Enemies, 2 Supplies
    # -------------------------------------------------------------
    def _build_map_3_medium_b(self):
        self.width = 1600
        self.height = 1200
        self._add_perimeter()
        self.player_spawn = [140.0, 1050.0]

        # Street grid layout with ruin walls
        self._add_obstacle(180, 180, 360, 24, 'concrete')
        self._add_obstacle(180, 180, 24, 300, 'concrete')
        self._add_obstacle(360, 320, 180, 24, 'concrete')
        self._add_obstacle(360, 320, 24, 160, 'concrete')

        self._add_obstacle(1060, 180, 360, 24, 'concrete')
        self._add_obstacle(1396, 180, 24, 300, 'concrete')
        self._add_obstacle(1060, 320, 180, 24, 'concrete')
        self._add_obstacle(1216, 320, 24, 160, 'concrete')

        # Southern Building Shells
        self._add_obstacle(180, 720, 24, 260, 'concrete')
        self._add_obstacle(180, 720, 280, 24, 'concrete')
        self._add_obstacle(436, 720, 24, 260, 'concrete')

        self._add_obstacle(1140, 720, 280, 24, 'concrete')
        self._add_obstacle(1396, 720, 24, 260, 'concrete')
        self._add_obstacle(1140, 720, 24, 260, 'concrete')

        # Central Crossroads Avenue & Barricades
        self._add_obstacle(720, 200, 160, 24, 'concrete')
        self._add_obstacle(720, 976, 160, 24, 'concrete')
        self._add_obstacle(540, 560, 160, 30, 'concrete')
        self._add_obstacle(900, 560, 160, 30, 'concrete')
        self._add_obstacle(785, 460, 30, 240, 'concrete')

        # Scattered Urban Crates & Rubble
        self._add_obstacle(600, 360, 60, 50, 'crate')
        self._add_obstacle(940, 360, 60, 50, 'crate')
        self._add_obstacle(600, 780, 60, 50, 'crate')
        self._add_obstacle(940, 780, 60, 50, 'crate')
        self._add_obstacle(770, 780, 60, 45, 'metal')

        # 5 Enemies actively patrolling intersections
        self.enemy_configs = [
            {'pos': [340, 260], 'waypoints': [[340, 260], [620, 260], [620, 480], [340, 260]]},
            {'pos': [1260, 260], 'waypoints': [[1260, 260], [980, 260], [980, 480], [1260, 260]]},
            {'pos': [800, 380], 'waypoints': [[800, 380], [800, 740], [650, 600], [950, 600]]},
            {'pos': [320, 850], 'waypoints': [[320, 850], [620, 850], [620, 650], [320, 850]]},
            {'pos': [1260, 850], 'waypoints': [[1260, 850], [980, 850], [980, 650], [1260, 850]]},
        ]

        # 2 Supply Medkits
        self.supply_stations = [
            [260.0, 240.0],
            [1320.0, 800.0],
        ]

    # -------------------------------------------------------------
    # MAP 4: Large A - Military Airbase (2200x1600) - 7 Enemies, 3 Supplies
    # -------------------------------------------------------------
    def _build_map_4_large_a(self):
        self.width = 2200
        self.height = 1600
        self._add_perimeter()
        self.player_spawn = [160.0, 800.0]

        # West Aircraft Hangar 1
        self._add_obstacle(300, 240, 480, 30, 'concrete')
        self._add_obstacle(300, 240, 30, 360, 'concrete')
        self._add_obstacle(300, 570, 320, 30, 'concrete')
        self._add_obstacle(750, 240, 30, 220, 'concrete')
        self._add_obstacle(450, 360, 80, 60, 'crate')

        # West Aircraft Hangar 2
        self._add_obstacle(300, 1000, 480, 30, 'concrete')
        self._add_obstacle(300, 1000, 30, 360, 'concrete')
        self._add_obstacle(300, 1330, 320, 30, 'concrete')
        self._add_obstacle(750, 1140, 30, 220, 'concrete')
        self._add_obstacle(450, 1120, 80, 60, 'crate')

        # Central Flight Line Checkpoint & Containers
        self._add_obstacle(1000, 680, 200, 40, 'concrete')
        self._add_obstacle(1000, 880, 200, 40, 'concrete')
        self._add_obstacle(1080, 720, 40, 160, 'concrete')

        # Cargo Containers on Runway
        self._add_obstacle(880, 450, 140, 50, 'metal')
        self._add_obstacle(1280, 450, 140, 50, 'metal')
        self._add_obstacle(880, 1050, 140, 50, 'metal')
        self._add_obstacle(1280, 1050, 140, 50, 'metal')

        # East Flight Operations & Tower
        self._add_obstacle(1550, 450, 420, 30, 'concrete')
        self._add_obstacle(1550, 450, 30, 700, 'concrete')
        self._add_obstacle(1550, 1120, 420, 30, 'concrete')
        self._add_obstacle(1940, 450, 30, 260, 'concrete')
        self._add_obstacle(1940, 890, 30, 260, 'concrete')
        self._add_obstacle(1700, 750, 100, 60, 'metal')

        # 7 Enemies (Extensive flight-line patrol sweeps)
        self.enemy_configs = [
            {'pos': [600, 400], 'waypoints': [[600, 400], [1050, 550], [1500, 400], [1050, 550], [600, 400]]},
            {'pos': [900, 800], 'waypoints': [[900, 800], [900, 400], [1600, 800], [900, 1200], [900, 800]]},
            {'pos': [600, 1200], 'waypoints': [[600, 1200], [1050, 1050], [1500, 1200], [1050, 1050], [600, 1200]]},
            {'pos': [860, 620], 'waypoints': [[860, 620], [960, 520], [960, 980], [860, 1080], [860, 620]]},
            {'pos': [1420, 620], 'waypoints': [[1420, 620], [1360, 520], [1360, 980], [1420, 1080], [1420, 620]]},
            {'pos': [1780, 620], 'waypoints': [[1780, 620], [1880, 620], [1880, 980], [1780, 980], [1780, 620]]},
            {'pos': [1780, 980], 'waypoints': [[1780, 980], [1680, 980], [1680, 620], [1780, 620], [1780, 980]]},
        ]

        # 3 Supplies
        self.supply_stations = [
            [400.0, 320.0],    # Inside Hangar 1
            [400.0, 1240.0],   # Inside Hangar 2
            [1780.0, 800.0],   # Inside Flight Ops Tower
        ]

    # -------------------------------------------------------------
    # MAP 5: Large B - Deep Research Laboratory (2400x1800) - 7 Enemies, 4 Supplies
    # -------------------------------------------------------------
    def _build_map_5_large_b(self):
        self.width = 2400
        self.height = 1800
        self._add_perimeter()
        self.player_spawn = [160.0, 900.0]

        # Sector 1: Containment Wing (North-West)
        self._add_obstacle(260, 240, 450, 30, 'concrete')
        self._add_obstacle(260, 240, 30, 420, 'concrete')
        self._add_obstacle(260, 630, 320, 30, 'concrete')
        self._add_obstacle(680, 240, 30, 260, 'concrete')
        self._add_obstacle(440, 380, 90, 70, 'metal')

        # Sector 2: Reactor Core (North-East)
        self._add_obstacle(1650, 240, 480, 30, 'concrete')
        self._add_obstacle(2100, 240, 30, 420, 'concrete')
        self._add_obstacle(1780, 630, 350, 30, 'concrete')
        self._add_obstacle(1650, 240, 30, 260, 'concrete')
        self._add_obstacle(1820, 380, 120, 80, 'metal')

        # Sector 3: Bio-Archive (South-West)
        self._add_obstacle(260, 1150, 450, 30, 'concrete')
        self._add_obstacle(260, 1150, 30, 420, 'concrete')
        self._add_obstacle(260, 1540, 320, 30, 'concrete')
        self._add_obstacle(680, 1310, 30, 260, 'concrete')
        self._add_obstacle(440, 1300, 90, 70, 'crate')

        # Sector 4: Data Vault (South-East)
        self._add_obstacle(1650, 1150, 480, 30, 'concrete')
        self._add_obstacle(2100, 1150, 30, 420, 'concrete')
        self._add_obstacle(1780, 1540, 350, 30, 'concrete')
        self._add_obstacle(1650, 1310, 30, 260, 'concrete')
        self._add_obstacle(1840, 1300, 90, 70, 'metal')

        # Central Grand Hall & Lab Pods
        self._add_obstacle(1050, 450, 30, 300, 'concrete')
        self._add_obstacle(1320, 450, 30, 300, 'concrete')
        self._add_obstacle(1050, 1050, 30, 300, 'concrete')
        self._add_obstacle(1320, 1050, 30, 300, 'concrete')
        # Center hub
        self._add_obstacle(1080, 850, 240, 100, 'concrete')
        self._add_obstacle(900, 860, 60, 80, 'crate')
        self._add_obstacle(1440, 860, 60, 80, 'crate')

        # 7 Enemies (Deep sector patrols roaming the laboratory wings)
        self.enemy_configs = [
            {'pos': [600, 460], 'waypoints': [[600, 460], [1200, 500], [1800, 460], [1200, 750], [600, 460]]},
            {'pos': [1000, 900], 'waypoints': [[1000, 900], [800, 900], [1200, 600], [1600, 900], [1000, 1200]]},
            {'pos': [600, 1350], 'waypoints': [[600, 1350], [1200, 1300], [1800, 1350], [1200, 1050], [600, 1350]]},
            {'pos': [900, 500], 'waypoints': [[900, 500], [980, 500], [980, 760], [900, 760], [900, 500]]},
            {'pos': [1500, 500], 'waypoints': [[1500, 500], [1420, 500], [1420, 760], [1500, 760], [1500, 500]]},
            {'pos': [900, 1300], 'waypoints': [[900, 1300], [980, 1300], [980, 1040], [900, 1040], [900, 1300]]},
            {'pos': [1500, 1300], 'waypoints': [[1500, 1300], [1420, 1300], [1420, 1040], [1500, 1040], [1500, 1300]]},
        ]

        # 4 Supplies
        self.supply_stations = [
            [360.0, 340.0],
            [1950.0, 340.0],
            [360.0, 1420.0],
            [1950.0, 1420.0],
        ]

    def _pre_render_floor(self):
        """Pre-renders an industrial tactical floor grid."""
        self.floor_surface = pygame.Surface((self.width, self.height))
        self.floor_surface.fill((26, 30, 36))

        # Grid lines
        tile_size = 64
        for x in range(0, self.width, tile_size):
            pygame.draw.line(self.floor_surface, (32, 38, 46), (x, 0), (x, self.height), 1)
        for y in range(0, self.height, tile_size):
            pygame.draw.line(self.floor_surface, (32, 38, 46), (0, y), (self.width, y), 1)

        # Tactical markings
        cx, cy = self.width // 2, self.height // 2
        pygame.draw.circle(self.floor_surface, (42, 50, 60), (cx, cy), 180, 2)
        pygame.draw.circle(self.floor_surface, (42, 50, 60), (cx, cy), 90, 1)

    def resolve_movement(self, hitbox_rect, dx, dy):
        """Moves entity hitbox rect with separate X and Y axis sliding resolution."""
        hitbox_rect.x += dx
        for wall in self.walls:
            if hitbox_rect.colliderect(wall):
                if dx > 0:
                    hitbox_rect.right = wall.left
                elif dx < 0:
                    hitbox_rect.left = wall.right

        hitbox_rect.y += dy
        for wall in self.walls:
            if hitbox_rect.colliderect(wall):
                if dy > 0:
                    hitbox_rect.bottom = wall.top
                elif dy < 0:
                    hitbox_rect.top = wall.bottom

        return hitbox_rect.centerx, hitbox_rect.centery

    def has_line_of_sight(self, p1, p2):
        for wall in self.walls:
            hit, _ = line_intersects_rect(p1, p2, wall)
            if hit:
                return False
        return True

    def draw(self, surface, camera_offset=(0, 0)):
        cam_x, cam_y = camera_offset
        sw, sh = surface.get_size()
        src_rect = pygame.Rect(cam_x, cam_y, sw, sh)
        surface.blit(self.floor_surface, (0, 0), src_rect)

        for rect, cover_type in self.cover_types:
            draw_rect = pygame.Rect(
                rect.x - cam_x,
                rect.y - cam_y,
                rect.width,
                rect.height
            )
            if not draw_rect.colliderect(pygame.Rect(0, 0, sw, sh)):
                continue

            if cover_type == 'concrete':
                pygame.draw.rect(surface, (50, 56, 64), draw_rect)
                top_bevel = pygame.Rect(draw_rect.x + 2, draw_rect.y + 2, draw_rect.width - 4, draw_rect.height - 4)
                pygame.draw.rect(surface, (70, 78, 88), top_bevel)
                pygame.draw.rect(surface, (95, 105, 118), draw_rect, 2)
            elif cover_type == 'crate':
                pygame.draw.rect(surface, (85, 65, 45), draw_rect)
                inner = pygame.Rect(draw_rect.x + 3, draw_rect.y + 3, draw_rect.width - 6, draw_rect.height - 6)
                pygame.draw.rect(surface, (110, 85, 55), inner)
                pygame.draw.line(surface, (60, 45, 30), inner.topleft, inner.bottomright, 2)
                pygame.draw.line(surface, (60, 45, 30), inner.topright, inner.bottomleft, 2)
                pygame.draw.rect(surface, (45, 35, 25), draw_rect, 2)
            elif cover_type == 'metal':
                pygame.draw.rect(surface, (40, 48, 56), draw_rect)
                inner = pygame.Rect(draw_rect.x + 2, draw_rect.y + 2, draw_rect.width - 4, draw_rect.height - 4)
                pygame.draw.rect(surface, (60, 72, 85), inner)
                pygame.draw.rect(surface, (100, 118, 138), draw_rect, 2)
                pygame.draw.circle(surface, (0, 255, 180), (inner.x + 8, inner.y + 8), 3)
