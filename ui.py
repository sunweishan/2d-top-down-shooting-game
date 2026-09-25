"""
ui.py - Tactical Heads-Up Display (HUD), start menu with difficulty & map selection,
loadout customizer, minimap, crosshair, notifications, and dynamic Grade A-E evaluation.
"""

import math
import pygame
from map import MAP_METADATA
from sprites import SKIN_PALETTES, draw_rotated_sprite, get_sprite_bank

DIFFICULTIES = {
    'EASY': {
        'label': "EASY",
        'hp': 20,
        'enemy_hp': 3,
        'mult': 1.0,
        'desc': "20 HP / Lives - Reduced pressure",
        'color': (0, 220, 140)
    },
    'MEDIUM': {
        'label': "MEDIUM",
        'hp': 15,
        'enemy_hp': 5,
        'mult': 1.5,
        'desc': "15 HP / Lives - Standard tactical",
        'color': (255, 190, 40)
    },
    'HARD': {
        'label': "HARD",
        'hp': 10,
        'enemy_hp': 10,
        'mult': 2.2,
        'desc': "10 HP / Lives - Extreme lethality",
        'color': (255, 60, 60)
    }
}

WEAPON_CATALOG = {
    'MACHINE_GUN': {
        'id': 'MACHINE_GUN',
        'name': "MACHINE GUN",
        'badge': "STANDARD AUTO",
        'type_label': "RAPID FIRE RIFLE",
        'trait': "Continuous Fire",
        'desc': "High rate-of-fire assault rifle with unlimited standard ammunition.",
        'special': "Rapid automatic fire • 1 DMG per hit • High bullet stream",
        'stats': "ROF: High | DMG: 1 | VEL: 900 m/s",
        'color': (0, 220, 160),
        'key': "[ 1 ]",
    },
    'SNIPER': {
        'id': 'SNIPER',
        'name': "SNIPER RIFLE",
        'badge': "WALL PENETRATION",
        'type_label': "ANTI-MATERIEL",
        'trait': "Pierces Walls",
        'desc': "High-caliber precision rifle engineered to punch straight through solid obstacles.",
        'special': "Wall-piercing rounds • 5 DMG per hit • Pinpoint laser precision",
        'stats': "ROF: Slow | DMG: 5 | VEL: 1400 m/s",
        'color': (0, 210, 255),
        'key': "[ 2 ]",
    },
    'ROCKET': {
        'id': 'ROCKET',
        'name': "ROCKET LAUNCHER",
        'badge': "WALL-BREACH / CLEARANCE",
        'type_label': "HE ORDNANCE",
        'trait': "Piercing Blast",
        'desc': "Shoulder-fired ordnance that breaches walls before clearing the impact room.",
        'special': "Wall-piercing rocket • Impact clears all hostiles in the room • 10 DMG",
        'stats': "ROF: Heavy | DMG: 10 + Clear | VEL: 650 m/s",
        'color': (255, 130, 40),
        'key': "[ 3 ]",
    },
}

GRADE_THRESHOLDS = {
    'EASY': [
        ('A', 750, True, (255, 215, 0), "EXEMPLARY COMBAT PERFORMANCE"),
        ('B', 550, True, (0, 230, 255), "TACTICAL OBJECTIVE SECURED"),
        ('C', 400, False, (120, 255, 120), "OPERATION COMPLETED"),
        ('D', 250, False, (255, 160, 40), "SUB-OPTIMAL ENGAGEMENT"),
        ('E', 0, False, (255, 50, 50), "MISSION COMPROMISED"),
    ],
    'MEDIUM': [
        ('A', 1200, True, (255, 215, 0), "EXEMPLARY COMBAT PERFORMANCE"),
        ('B', 900, True, (0, 230, 255), "TACTICAL OBJECTIVE SECURED"),
        ('C', 650, False, (120, 255, 120), "OPERATION COMPLETED"),
        ('D', 400, False, (255, 160, 40), "SUB-OPTIMAL ENGAGEMENT"),
        ('E', 0, False, (255, 50, 50), "MISSION COMPROMISED"),
    ],
    'HARD': [
        ('A', 1200, True, (255, 215, 0), "EXEMPLARY COMBAT PERFORMANCE"),
        ('B', 900, True, (0, 230, 255), "TACTICAL OBJECTIVE SECURED"),
        ('C', 650, False, (120, 255, 120), "OPERATION COMPLETED"),
        ('D', 400, False, (255, 160, 40), "SUB-OPTIMAL ENGAGEMENT"),
        ('E', 0, False, (255, 50, 50), "MISSION COMPROMISED"),
    ],
}


def calculate_grade_and_score(stats, is_victory=True):
    """
    Computes final performance score and assigns Grade A through E dynamically by difficulty.
    Metrics:
    - Kills / Total ratio
    - Remaining HP / Max HP ratio
    - Completion time
    - Shooting accuracy (shots_hit / shots_fired)
    - Melee kills bonus
    - Difficulty multiplier & difficulty-tuned thresholds
    """
    enemies_killed = stats.get('enemies_killed', 0)
    total_enemies = max(1, stats.get('total_enemies', 1))
    hp_left = max(0, stats.get('hp', 0))
    max_hp = max(1, stats.get('max_hp', 10))
    match_time = stats.get('time', 0.0)
    shots_fired = stats.get('shots_fired', 0)
    shots_hit = stats.get('shots_hit', 0)
    melee_kills = stats.get('melee_kills', 0)
    diff_key = stats.get('difficulty', 'MEDIUM')
    diff_mult = DIFFICULTIES.get(diff_key, DIFFICULTIES['MEDIUM'])['mult']

    # 1. Elimination Score (up to 450 pts)
    kill_ratio = enemies_killed / total_enemies
    kill_score = kill_ratio * 450.0

    # 2. Vitality / HP Ratio Score (up to 250 pts)
    hp_ratio = hp_left / max_hp
    hp_score = hp_ratio * 250.0

    # 3. Time Score (faster completion = higher score, up to 200 pts)
    if is_victory:
        time_score = max(20.0, 200.0 - match_time * 1.8)
    else:
        time_score = max(0.0, 80.0 - match_time * 0.8)

    # 4. Accuracy Score (up to 150 pts)
    accuracy = (shots_hit / max(1, shots_fired)) if shots_fired > 0 else 0.0
    accuracy = min(1.0, accuracy)
    acc_score = accuracy * 150.0

    # 5. Melee Bonus (50 pts per risky knife kill)
    melee_bonus = melee_kills * 50.0

    # Raw combined score
    raw_score = kill_score + hp_score + time_score + acc_score + melee_bonus

    # Apply Difficulty Multiplier
    final_score = int(raw_score * diff_mult)

    # Dynamic Grade Assignment based on difficulty-specific thresholds
    thresholds = GRADE_THRESHOLDS.get(diff_key, GRADE_THRESHOLDS['MEDIUM'])
    grade = 'E'
    grade_color = (255, 50, 50)
    verdict = "MISSION COMPROMISED"
    for g, min_pts, req_vic, gcol, gverdict in thresholds:
        if final_score >= min_pts and (not req_vic or is_victory):
            grade = g
            grade_color = gcol
            verdict = gverdict
            break

    return {
        'grade': grade,
        'grade_color': grade_color,
        'verdict': verdict,
        'final_score': final_score,
        'raw_score': int(raw_score),
        'diff_mult': diff_mult,
        'diff_key': diff_key,
        'accuracy_pct': int(accuracy * 100),
        'kill_score': int(kill_score),
        'hp_score': int(hp_score),
        'time_score': int(time_score),
        'acc_score': int(acc_score),
        'melee_bonus': int(melee_bonus),
    }


class UIManager:
    """Renders tactical HUD, start screen, intro transition, and game over screens."""

    def __init__(self, screen_w=1280, screen_h=720):
        self.screen_w = screen_w
        self.screen_h = screen_h
        pygame.font.init()
        self.font_title = pygame.font.Font(None, 44)
        self.font_main = pygame.font.Font(None, 22)
        self.font_sm = pygame.font.Font(None, 17)
        self.font_grade = pygame.font.Font(None, 80)
        self.intro_timer = 0.0
        self.INTRO_DURATION = 2.0

        # Menu selections
        self.selected_difficulty = 'MEDIUM'
        self.selected_map_id = 2

        # In-game notification banner
        self.notification_text = ""
        self.notification_timer = 0.0

        # Clickable rects for Start menu
        self.diff_rects = {}
        self.map_rects = {}
        self.start_btn_rect = pygame.Rect(0, 0, 0, 0)
        self.help_btn_rect = pygame.Rect(0, 0, 0, 0)

        # Customization selections
        self.selected_weapon_type = 'MACHINE_GUN'
        self.selected_skin_id = 'NAVY'
        self.loadout_weapon_rects = {}
        self.loadout_skin_rects = {}
        self.loadout_deploy_rect = pygame.Rect(0, 0, 0, 0)
        self.loadout_back_rect = pygame.Rect(0, 0, 0, 0)

        # Help modal state & scroll support
        self.help_tab = 0  # 0=EASY, 1=MEDIUM, 2=HARD
        self.help_tab_rects = []
        self.help_scroll_y = 0.0
        self.max_help_scroll = 180.0
        self.help_modal_rect = pygame.Rect(0, 0, 0, 0)

        # Pause button rects (set by draw_pause_screen)
        self.pause_btn_rects = []

        # Minimap references (set when entering PLAYING state)
        self.map_manager_ref = None
        self.supply_manager_ref = None

    def show_notification(self, text, duration=2.5):
        self.notification_text = text
        self.notification_timer = duration

    def reset_intro(self):
        self.intro_timer = self.INTRO_DURATION

    def update_intro(self, dt):
        if self.intro_timer > 0:
            self.intro_timer -= dt
        if self.notification_timer > 0:
            self.notification_timer -= dt
            if self.notification_timer <= 0:
                self.notification_text = ""

    def is_intro_active(self):
        return self.intro_timer > 0

    def draw_hud(self, surface, player, enemies, bullets, match_time=0.0, current_score=0):
        """Draws player health, enemies remaining, bayonet cooldown, notification, minimap, and bottom-right metrics."""
        # 1. Dynamic Health Bar
        self._draw_health_bar(surface, player)

        # 2. Dynamic Enemy Tracker
        self._draw_enemy_tracker(surface, enemies)

        # 3. Weapon Status
        self._draw_weapon_status(surface, player)

        # 4. Tactical Minimap
        self._draw_minimap(surface, player, enemies)

        # 5. Bottom-Right Combat Metrics (Timer, Score & Limited Ammo)
        self._draw_combat_metrics(surface, player, match_time, current_score)

        # 6. Supply Notification Toast
        if self.notification_timer > 0 and self.notification_text:
            self._draw_notification(surface)

    def _draw_notification(self, surface):
        surf = self.font_main.render(self.notification_text, True, (0, 255, 160))
        w = surf.get_width() + 32
        h = 36
        cx = self.screen_w // 2
        y = 70
        rect = pygame.Rect(cx - w // 2, y, w, h)
        panel = pygame.Surface((w, h), pygame.SRCALPHA)
        panel.fill((10, 30, 20, 220))
        surface.blit(panel, rect.topleft)
        pygame.draw.rect(surface, (0, 220, 120), rect, 2, border_radius=4)
        surface.blit(surf, (cx - surf.get_width() // 2, y + 8))

    def _draw_health_bar(self, surface, player):
        x, y = 24, 20
        total_bar_w = 260
        seg_gap = 3
        count = max(1, player.max_hp)
        seg_w = max(10, (total_bar_w - (count - 1) * seg_gap) // count)
        actual_bar_w = count * seg_w + (count - 1) * seg_gap
        panel_w = max(290, actual_bar_w + 30)

        panel_rect = pygame.Rect(x - 8, y - 6, panel_w, 54)
        pygame.draw.rect(surface, (14, 18, 24, 215), panel_rect, border_radius=6)
        pygame.draw.rect(surface, (45, 60, 80), panel_rect, 2, border_radius=6)

        txt = self.font_sm.render(f"OPERATOR VITALITY: {player.hp}/{player.max_hp} HP", True, (160, 210, 255))
        surface.blit(txt, (x, y))

        bar_x = x
        bar_y = y + 20
        seg_h = 16
        for i in range(player.max_hp):
            seg_rect = pygame.Rect(bar_x + i * (seg_w + seg_gap), bar_y, seg_w, seg_h)
            if i < player.hp:
                ratio = player.hp / player.max_hp
                if ratio > 0.5:
                    col = (0, 200, 150)
                elif ratio > 0.25:
                    col = (255, 185, 30)
                else:
                    col = (255, 45, 45)
                pygame.draw.rect(surface, col, seg_rect, border_radius=2)
                pygame.draw.rect(surface, (255, 255, 255, 90), (seg_rect.x, seg_rect.y, seg_w, 3))
            else:
                pygame.draw.rect(surface, (35, 42, 52), seg_rect, border_radius=2)
            pygame.draw.rect(surface, (15, 20, 28), seg_rect, 1, border_radius=2)

    def _draw_enemy_tracker(self, surface, enemies):
        alive_count = sum(1 for e in enemies if e.alive)
        total_count = len(enemies)
        y = 16

        pip_spacing = min(32, 240 // max(1, total_count))
        panel_w = max(220, total_count * pip_spacing + 40)
        panel_rect = pygame.Rect(self.screen_w // 2 - panel_w // 2, y, panel_w, 44)
        pygame.draw.rect(surface, (14, 18, 24, 215), panel_rect, border_radius=6)
        pygame.draw.rect(surface, (80, 30, 30), panel_rect, 2, border_radius=6)

        txt = self.font_sm.render(f"HOSTILES: {alive_count} / {total_count}", True, (255, 120, 120))
        surface.blit(txt, (self.screen_w // 2 - txt.get_width() // 2, y + 4))

        start_x = self.screen_w // 2 - (total_count * pip_spacing) // 2 + pip_spacing // 2
        for i in range(total_count):
            pip_x = start_x + i * pip_spacing
            pip_y = y + 28
            is_alive = i < alive_count
            col = (255, 50, 50) if is_alive else (60, 65, 75)
            pygame.draw.circle(surface, col, (pip_x, pip_y), 5)
            if is_alive:
                pygame.draw.circle(surface, (255, 180, 180), (pip_x, pip_y), 2)
            else:
                pygame.draw.line(surface, (180, 40, 40), (pip_x - 3, pip_y - 3), (pip_x + 3, pip_y + 3), 2)
                pygame.draw.line(surface, (180, 40, 40), (pip_x + 3, pip_y - 3), (pip_x - 3, pip_y + 3), 2)

    def _draw_weapon_status(self, surface, player):
        x = 24
        y = self.screen_h - 74

        panel_rect = pygame.Rect(x - 8, y - 6, 360, 58)
        pygame.draw.rect(surface, (14, 18, 24, 215), panel_rect, border_radius=6)
        pygame.draw.rect(surface, (45, 60, 80), panel_rect, 2, border_radius=6)

        wp = getattr(player, 'primary_weapon', player.machine_gun)
        wp_type = getattr(wp, 'weapon_type', 'MACHINE_GUN')
        wp_short_name = {'SNIPER': 'SNIPER', 'ROCKET': 'ROCKET'}.get(wp_type, 'MACHINE GUN')
        ammo = getattr(wp, 'ammo', None)
        ammo_label = "UNLIMITED" if ammo is None else f"{ammo}/{wp.max_ammo}"

        if ammo is not None and ammo <= 0:
            wp_col = (255, 70, 70)
            wp_txt_str = f"[L-CLICK] {wp_short_name}: EMPTY | AMMO {ammo_label}"
        elif wp.can_fire():
            if wp_type == 'SNIPER':
                wp_col = (0, 220, 255)
                wp_txt_str = f"[L-CLICK] {wp_short_name}: READY | {ammo_label} | PIERCE 5"
            elif wp_type == 'ROCKET':
                wp_col = (255, 140, 40)
                wp_txt_str = f"[L-CLICK] {wp_short_name}: READY | {ammo_label} | WALL-BREACH"
            else:
                wp_col = (200, 220, 245)
                wp_txt_str = f"[L-CLICK] {wp_short_name}: READY | AUTO"
        else:
            wp_col = (180, 195, 210)
            wp_txt_str = f"[L-CLICK] {wp_short_name}: CYCLING ({wp.timer:.1f}s) | {ammo_label}"

        mg_txt = self.font_sm.render(wp_txt_str, True, wp_col)
        surface.blit(mg_txt, (x, y))

        if player.bayonet.can_strike():
            knife_col = (0, 255, 160)
            knife_str = "[SPACE / F] BAYONET: READY (INSTAKILL 1-HIT)"
        else:
            knife_col = (255, 140, 40)
            knife_str = f"[SPACE / F] BAYONET: RECOVERING ({player.bayonet.timer:.1f}s)"

        k_txt = self.font_sm.render(knife_str, True, knife_col)
        surface.blit(k_txt, (x, y + 26))

    def _draw_combat_metrics(self, surface, player, match_time, current_score):
        """Displays timer, score, and limited-weapon ammo in the bottom-right."""
        panel_w = 210
        primary_weapon = getattr(player, 'primary_weapon', None)
        ammo = getattr(primary_weapon, 'ammo', None)
        max_ammo = getattr(primary_weapon, 'max_ammo', None)
        has_limited_ammo = ammo is not None and max_ammo is not None
        panel_h = 84 if has_limited_ammo else 58
        x = self.screen_w - panel_w - 20
        y = self.screen_h - (100 if has_limited_ammo else 74)

        panel_rect = pygame.Rect(x, y - 6, panel_w, panel_h)
        pygame.draw.rect(surface, (14, 18, 24, 215), panel_rect, border_radius=6)
        pygame.draw.rect(surface, (45, 60, 80), panel_rect, 2, border_radius=6)

        # Elapsed time MM:SS
        mins = int(match_time // 60)
        secs = int(match_time % 60)
        time_str = f"TIME: {mins:02d}:{secs:02d}"
        time_surf = self.font_main.render(time_str, True, (0, 220, 255))
        surface.blit(time_surf, (x + 16, y + 2))

        # Real-time score
        score_str = f"SCORE: {int(current_score)}"
        score_surf = self.font_main.render(score_str, True, (255, 215, 80))
        surface.blit(score_surf, (x + 16, y + 26))

        if has_limited_ammo:
            ammo_str = f"AMMO: {int(ammo)}/{int(max_ammo)}"
            ammo_surf = self.font_main.render(ammo_str, True, (255, 140, 60) if ammo <= 0 else (255, 190, 90))
            surface.blit(ammo_surf, (x + 16, y + 50))

    def _draw_minimap(self, surface, player, enemies):
        mm_w = 160
        mm_h = 120
        x = self.screen_w - mm_w - 20
        y = 20

        mm_rect = pygame.Rect(x, y, mm_w, mm_h)
        pygame.draw.rect(surface, (10, 14, 20, 220), mm_rect, border_radius=4)
        pygame.draw.rect(surface, (45, 65, 90), mm_rect, 2, border_radius=4)

        # Per-map scale computed from actual map dimensions
        if self.map_manager_ref is not None:
            map_w = self.map_manager_ref.width
            map_h = self.map_manager_ref.height
        else:
            map_w = 2000
            map_h = 1500
        scale_x = mm_w / map_w
        scale_y = mm_h / map_h

        # Draw map walls as tiny grey rectangles
        if self.map_manager_ref is not None:
            for wall in self.map_manager_ref.walls:
                wx = int(x + wall.x * scale_x)
                wy = int(y + wall.y * scale_y)
                ww = max(1, int(wall.width * scale_x))
                wh = max(1, int(wall.height * scale_y))
                wall_rect = pygame.Rect(wx, wy, ww, wh)
                clipped = wall_rect.clip(mm_rect)
                if clipped.width > 0 and clipped.height > 0:
                    pygame.draw.rect(surface, (70, 80, 95), clipped)

        # Draw active medkits as small green crosses
        if self.supply_manager_ref is not None:
            for mk in self.supply_manager_ref.medkits:
                if not mk.collected:
                    mkx = int(x + mk.pos[0] * scale_x)
                    mky = int(y + mk.pos[1] * scale_y)
                    if x <= mkx <= x + mm_w and y <= mky <= y + mm_h:
                        pygame.draw.line(surface, (0, 220, 100), (mkx - 3, mky), (mkx + 3, mky), 2)
                        pygame.draw.line(surface, (0, 220, 100), (mkx, mky - 3), (mkx, mky + 3), 2)

        # Draw enemy dots (red)
        for e in enemies:
            if e.alive:
                ex = int(x + e.pos[0] * scale_x)
                ey = int(y + e.pos[1] * scale_y)
                if x <= ex <= x + mm_w and y <= ey <= y + mm_h:
                    pygame.draw.circle(surface, (255, 60, 60), (ex, ey), 3)

        # Draw player dot (cyan) with direction arrow
        if player.alive:
            px = int(x + player.pos[0] * scale_x)
            py = int(y + player.pos[1] * scale_y)
            if x <= px <= x + mm_w and y <= py <= y + mm_h:
                pygame.draw.circle(surface, (0, 230, 255), (px, py), 4)
                rad = math.radians(player.angle_deg)
                pygame.draw.line(surface, (255, 255, 255), (px, py),
                                 (int(px + math.cos(rad) * 8), int(py + math.sin(rad) * 8)), 2)

        tag = self.font_sm.render("TACTICAL RADAR", True, (110, 145, 180))
        surface.blit(tag, (x + 8, y + mm_h - 16))

    def draw_crosshair(self, surface, mouse_pos):
        mx, my = mouse_pos
        col = (0, 230, 255)
        pygame.draw.circle(surface, col, (mx, my), 2)
        gap = 5
        length = 11
        pygame.draw.line(surface, col, (mx - gap - length, my), (mx - gap, my), 2)
        pygame.draw.line(surface, col, (mx + gap, my), (mx + gap + length, my), 2)
        pygame.draw.line(surface, col, (mx, my - gap - length), (mx, my - gap), 2)
        pygame.draw.line(surface, col, (mx, my + gap), (mx, my + gap + length), 2)
        pygame.draw.circle(surface, (0, 230, 255, 120), (mx, my), 13, 1)

    def draw_intro_animation(self, surface):
        if self.intro_timer <= 0:
            return

        progress = 1.0 - (self.intro_timer / self.INTRO_DURATION)
        alpha = int(255 * (1.0 - progress))

        overlay = pygame.Surface((self.screen_w, self.screen_h), pygame.SRCALPHA)
        overlay.fill((10, 14, 20, alpha))
        surface.blit(overlay, (0, 0))

        meta = MAP_METADATA.get(self.selected_map_id, MAP_METADATA[2])
        t1 = self.font_title.render("OPERATION: IRON BREACH", True, (0, 220, 255))
        t2 = self.font_main.render(f"THEATER: {meta['name']}  |  DIFFICULTY: {self.selected_difficulty}", True, (240, 245, 255))
        t3 = self.font_sm.render(f"MISSION: ELIMINATE ALL {meta['enemies_count']} HOSTILES", True, (255, 180, 50))

        cx = self.screen_w // 2
        cy = self.screen_h // 2

        surface.blit(t1, (cx - t1.get_width() // 2, cy - 50))
        surface.blit(t2, (cx - t2.get_width() // 2, cy + 8))
        surface.blit(t3, (cx - t3.get_width() // 2, cy + 45))

        sweep_y = int(self.screen_h * progress)
        pygame.draw.line(surface, (0, 255, 220), (0, sweep_y), (self.screen_w, sweep_y), 2)

    def draw_start_screen(self, surface, tick_count):
        """Full interactive start menu with Difficulty Selection and 5 Map choices."""
        surface.fill((14, 18, 25))

        # Backdrop grid
        for gx in range(0, self.screen_w, 64):
            pygame.draw.line(surface, (22, 28, 38), (gx, 0), (gx, self.screen_h), 1)
        for gy in range(0, self.screen_h, 64):
            pygame.draw.line(surface, (22, 28, 38), (0, gy), (self.screen_w, gy), 1)

        cx = self.screen_w // 2

        # Main Title
        title_text = self.font_title.render("2D TOP-DOWN SHOOTER", True, (0, 220, 255))
        subtitle = self.font_main.render("TACTICAL ELIMINATION OPERATION  -  MISSION CONFIGURATION", True, (160, 190, 220))
        surface.blit(title_text, (cx - title_text.get_width() // 2, 28))
        surface.blit(subtitle, (cx - subtitle.get_width() // 2, 72))

        # -------------------------------------------------------------
        # 1. Difficulty Selection Panel (Top)
        # -------------------------------------------------------------
        diff_y = 115
        diff_lbl = self.font_main.render("1. SELECT DIFFICULTY / LIVES (ARROW KEYS / CLICK)", True, (255, 220, 120))
        surface.blit(diff_lbl, (cx - 480, diff_y))

        diff_keys = ['EASY', 'MEDIUM', 'HARD']
        btn_w = 300
        btn_h = 58
        start_bx = cx - 480
        self.diff_rects = {}

        for idx, dk in enumerate(diff_keys):
            dinfo = DIFFICULTIES[dk]
            bx = start_bx + idx * 330
            by = diff_y + 30
            rect = pygame.Rect(bx, by, btn_w, btn_h)
            self.diff_rects[dk] = rect

            is_sel = (self.selected_difficulty == dk)
            bg_col = (25, 45, 60) if is_sel else (18, 24, 32)
            border_col = dinfo['color'] if is_sel else (45, 55, 70)
            border_w = 3 if is_sel else 1

            pygame.draw.rect(surface, bg_col, rect, border_radius=6)
            pygame.draw.rect(surface, border_col, rect, border_w, border_radius=6)

            tag = "[ SELECTED ] " if is_sel else ""
            t_label = self.font_main.render(
                f"{tag}{dinfo['label']} (P:{dinfo['hp']}HP / E:{dinfo['enemy_hp']}HP)",
                True, dinfo['color']
            )
            t_sub = self.font_sm.render(f"Score Mult: {dinfo['mult']}x | {dinfo['desc']}", True, (180, 195, 215))
            surface.blit(t_label, (bx + 14, by + 8))
            surface.blit(t_sub, (bx + 14, by + 32))

        # -------------------------------------------------------------
        # 2. Map Selection Panel (Middle)
        # -------------------------------------------------------------
        map_y = 230
        map_lbl = self.font_main.render("2. SELECT TACTICAL MAP & HOSTILE SCALE (1-5 / CLICK)", True, (255, 220, 120))
        surface.blit(map_lbl, (cx - 480, map_y))

        self.map_rects = {}
        for mid in range(1, 6):
            meta = MAP_METADATA[mid]
            card_x = cx - 480
            card_y = map_y + 30 + (mid - 1) * 58
            card_rect = pygame.Rect(card_x, card_y, 960, 50)
            self.map_rects[mid] = card_rect

            is_sel = (self.selected_map_id == mid)
            bg_col = (28, 48, 65) if is_sel else (18, 24, 32)
            border_col = (0, 220, 255) if is_sel else (45, 55, 70)
            border_w = 2 if is_sel else 1

            pygame.draw.rect(surface, bg_col, card_rect, border_radius=5)
            pygame.draw.rect(surface, border_col, card_rect, border_w, border_radius=5)

            prefix = ">> " if is_sel else f"[{mid}] "
            title_col = (255, 255, 255) if is_sel else (200, 215, 230)
            title = self.font_main.render(f"{prefix}{meta['name']} - {meta['size_label']}", True, title_col)
            surface.blit(title, (card_x + 14, card_y + 6))

            enemies_txt = self.font_sm.render(f"ENEMIES: {meta['enemies_count']}", True, (255, 80, 80))
            supplies_txt = self.font_sm.render(f"MEDKITS: {meta['supplies_count']}", True, (0, 220, 140))
            desc_txt = self.font_sm.render(meta['desc'], True, (160, 180, 200))

            surface.blit(enemies_txt, (card_x + 680, card_y + 8))
            surface.blit(supplies_txt, (card_x + 810, card_y + 8))
            surface.blit(desc_txt, (card_x + 14, card_y + 28))

        # -------------------------------------------------------------
        # 3. Deploy Button & Controls Briefing (Bottom)
        # -------------------------------------------------------------
        deploy_y = 600
        deploy_btn_w = 480
        deploy_btn_h = 50
        self.start_btn_rect = pygame.Rect(cx - deploy_btn_w // 2, deploy_y, deploy_btn_w, deploy_btn_h)

        is_pulse = (tick_count // 25) % 2 == 0
        btn_col = (0, 160, 110) if is_pulse else (0, 130, 90)
        pygame.draw.rect(surface, btn_col, self.start_btn_rect, border_radius=8)
        pygame.draw.rect(surface, (0, 255, 180), self.start_btn_rect, 2, border_radius=8)

        deploy_txt = self.font_main.render("CONTINUE TO LOADOUT [ENTER / SPACE]", True, (255, 255, 255))
        surface.blit(deploy_txt, (cx - deploy_txt.get_width() // 2, deploy_y + 14))

        # Controls hint bar
        hint = self.font_sm.render(
            "WASD: Move | MOUSE: Aim & Shoot (1 DMG) | SPACE/F: Bayonet Instakill | ESC: Pause",
            True, (140, 160, 185)
        )
        surface.blit(hint, (cx - hint.get_width() // 2, 665))

        # -------------------------------------------------------------
        # 4. Help Button (?) — Bottom-Right
        # -------------------------------------------------------------
        help_bw = 42
        help_bh = 42
        self.help_btn_rect = pygame.Rect(
            self.screen_w - help_bw - 20,
            self.screen_h - help_bh - 20,
            help_bw, help_bh
        )
        pygame.draw.rect(surface, (30, 50, 75), self.help_btn_rect, border_radius=8)
        pygame.draw.rect(surface, (0, 180, 255), self.help_btn_rect, 2, border_radius=8)
        q_txt = self.font_main.render("?", True, (0, 220, 255))
        surface.blit(q_txt, (
            self.help_btn_rect.centerx - q_txt.get_width() // 2,
            self.help_btn_rect.centery - q_txt.get_height() // 2
        ))
        hint2 = self.font_sm.render("HELP / SCORING", True, (80, 110, 140))
        surface.blit(hint2, (self.screen_w - hint2.get_width() - 20, self.screen_h - help_bh - 38))

    def draw_help_modal(self, surface):
        """
        Multi-page Help modal with EASY / MEDIUM / HARD tabs showing scoring breakdown.
        Content is clipped to a fixed viewport and smoothly scrollable via mouse wheel.
        """
        # Dim overlay
        overlay = pygame.Surface((self.screen_w, self.screen_h), pygame.SRCALPHA)
        overlay.fill((5, 8, 14, 210))
        surface.blit(overlay, (0, 0))

        modal_w = 820
        modal_h = 510
        modal_x = self.screen_w // 2 - modal_w // 2
        modal_y = self.screen_h // 2 - modal_h // 2
        self.help_modal_rect = pygame.Rect(modal_x, modal_y, modal_w, modal_h)

        # Modal background (Strictly maintains fixed 820x510 blue frame)
        pygame.draw.rect(surface, (14, 20, 30), (modal_x, modal_y, modal_w, modal_h), border_radius=10)
        pygame.draw.rect(surface, (0, 160, 255), (modal_x, modal_y, modal_w, modal_h), 2, border_radius=10)

        # Title bar
        title_surf = self.font_title.render("SCORING SYSTEM & DIFFICULTY GUIDE", True, (0, 220, 255))
        surface.blit(title_surf, (
            modal_x + modal_w // 2 - title_surf.get_width() // 2, modal_y + 14
        ))

        # Tab buttons: EASY / MEDIUM / HARD (Fixed at top)
        tab_labels = ['EASY', 'MEDIUM', 'HARD']
        tab_colors = [(0, 220, 140), (255, 190, 40), (255, 60, 60)]
        tab_w = 160
        tab_h = 34
        tab_y = modal_y + 60
        total_tab_w = len(tab_labels) * tab_w + (len(tab_labels) - 1) * 12
        tab_start_x = modal_x + modal_w // 2 - total_tab_w // 2
        self.help_tab_rects = []

        for i, (lbl, tcol) in enumerate(zip(tab_labels, tab_colors)):
            tx = tab_start_x + i * (tab_w + 12)
            tr = pygame.Rect(tx, tab_y, tab_w, tab_h)
            self.help_tab_rects.append(tr)
            is_active = (self.help_tab == i)
            bg = (25, 45, 70) if is_active else (18, 24, 34)
            border_col = tcol if is_active else (50, 65, 85)
            pygame.draw.rect(surface, bg, tr, border_radius=6)
            pygame.draw.rect(surface, border_col, tr, 2 if is_active else 1, border_radius=6)
            t = self.font_main.render(lbl, True, tcol if is_active else (130, 150, 170))
            surface.blit(t, (tr.centerx - t.get_width() // 2, tr.centery - t.get_height() // 2))

        # Scrollable Viewport Configuration
        view_x = modal_x + 16
        view_y = modal_y + 104
        view_w = modal_w - 32
        view_h = modal_h - 140  # 370px visible height inside fixed modal
        clip_rect = pygame.Rect(view_x, view_y, view_w, view_h)

        diff_keys_list = ['EASY', 'MEDIUM', 'HARD']
        dk = diff_keys_list[self.help_tab]
        dinfo = DIFFICULTIES[dk]

        # Enable clipping so content never overflows the blue box border
        old_clip = surface.get_clip()
        surface.set_clip(clip_rect)

        content_x = modal_x + 36
        content_y = view_y + 8 - int(self.help_scroll_y)

        def row(label, value, lcol=(200, 220, 245), vcol=(0, 230, 180)):
            nonlocal content_y
            ls = self.font_main.render(label, True, lcol)
            vs = self.font_main.render(str(value), True, vcol)
            surface.blit(ls, (content_x, content_y))
            surface.blit(vs, (modal_x + modal_w - 56 - vs.get_width(), content_y))
            content_y += 26

        # 1. Difficulty config section
        header = self.font_main.render(f"[ {dk} DIFFICULTY CONFIGURATION ]", True, dinfo['color'])
        surface.blit(header, (content_x, content_y))
        content_y += 28

        row("Player Starting HP:", f"{dinfo['hp']} HP")
        row("Enemy HP (each):", f"{dinfo['enemy_hp']} HP")
        row("Score Multiplier:", f"{dinfo['mult']}x")
        if dk == 'HARD':
            hard_note = self.font_sm.render(
                "  ★ Hard Mode: Enemies drop Medkits on death!", True, (255, 200, 60)
            )
            surface.blit(hard_note, (content_x, content_y))
            content_y += 20

        content_y += 4
        pygame.draw.line(surface, (40, 60, 85),
                         (modal_x + 20, content_y), (modal_x + modal_w - 36, content_y), 1)
        content_y += 10

        # 2. Scoring formula section
        score_header = self.font_main.render("[ SCORING FORMULA ]", True, (255, 220, 120))
        surface.blit(score_header, (content_x, content_y))
        content_y += 26

        formula_lines = [
            ("Kill Score (max 450 pts):", "kills/total * 450"),
            ("Vitality Score (max 250 pts):", "remaining_hp/max_hp * 250"),
            ("Time Bonus (max 200 pts, victory):", "200 - time * 1.8"),
            ("Accuracy Score (max 150 pts):", "hits/shots * 150"),
            ("Bayonet Bonus:", "+50 pts per melee kill"),
            ("Final Score:", f"raw_score * {dinfo['mult']}x  (diff mult)"),
        ]
        for lbl, val in formula_lines:
            ls = self.font_sm.render(lbl, True, (180, 200, 230))
            vs = self.font_sm.render(val, True, (0, 220, 160))
            surface.blit(ls, (content_x, content_y))
            surface.blit(vs, (content_x + 290, content_y))
            content_y += 20

        content_y += 6
        pygame.draw.line(surface, (40, 60, 85),
                         (modal_x + 20, content_y), (modal_x + modal_w - 36, content_y), 1)
        content_y += 10

        # 3. Dynamic Grade thresholds section tuned to the active difficulty
        grade_header = self.font_main.render(f"[ {dk} GRADE THRESHOLDS ]", True, (255, 220, 120))
        surface.blit(grade_header, (content_x, content_y))
        content_y += 24

        thresh = GRADE_THRESHOLDS.get(dk, GRADE_THRESHOLDS['MEDIUM'])
        d_cutoff = 400
        for gl, mp, _, _, _ in thresh:
            if gl == 'D':
                d_cutoff = mp
                break

        for g, min_pts, req_vic, gcol, _ in thresh:
            vic_str = "  (Victory required)" if req_vic else ""
            if min_pts > 0:
                desc = f">= {min_pts} pts{vic_str}"
            else:
                desc = f"< {d_cutoff} pts"
            gs = self.font_main.render(f"  Grade {g}:", True, gcol)
            ds = self.font_sm.render(desc, True, (180, 200, 220))
            surface.blit(gs, (content_x, content_y))
            surface.blit(ds, (content_x + 120, content_y + 3))
            content_y += 22

        content_y += 12

        # Measure total content height to compute maximum scroll range
        total_content_height = (content_y + int(self.help_scroll_y)) - view_y
        self.max_help_scroll = max(0.0, float(total_content_height - view_h + 10))

        # Restore original clipping
        surface.set_clip(old_clip)

        # Draw sleek scrollbar on the right side if content is longer than viewport
        if self.max_help_scroll > 0:
            track_x = modal_x + modal_w - 20
            track_y = view_y + 6
            track_h = view_h - 12
            pygame.draw.rect(surface, (20, 28, 40), (track_x, track_y, 6, track_h), border_radius=3)
            thumb_h = max(24, int(track_h * (view_h / max(view_h + 1, total_content_height))))
            scroll_ratio = self.help_scroll_y / self.max_help_scroll if self.max_help_scroll > 0 else 0.0
            thumb_y = track_y + int(scroll_ratio * (track_h - thumb_h))
            pygame.draw.rect(surface, (0, 180, 240), (track_x, thumb_y, 6, thumb_h), border_radius=3)

        # Fixed close and scroll hint at bottom
        close_txt = self.font_sm.render(
            "[ ESC ] or [ CLICK OUTSIDE ] to close   •   [ MOUSE WHEEL ] to scroll",
            True, (120, 150, 185)
        )
        surface.blit(close_txt, (
            modal_x + modal_w // 2 - close_txt.get_width() // 2,
            modal_y + modal_h - 26
        ))

    def handle_help_scroll(self, wheel_y):
        """Scrolls the help modal viewport via mouse wheel."""
        self.help_scroll_y = max(0.0, min(self.max_help_scroll, self.help_scroll_y - wheel_y * 32.0))

    def handle_help_click(self, mouse_pos):
        """Handles tab clicks and keeps clicks inside the fixed modal from closing it."""
        for i, tr in enumerate(self.help_tab_rects):
            if tr.collidepoint(mouse_pos):
                if self.help_tab != i:
                    self.help_tab = i
                    self.help_scroll_y = 0.0
                return True
        return self.help_modal_rect.collidepoint(mouse_pos)

    def draw_loadout_screen(self, surface, tick_count):
        """
        Interactive loadout & customization screen allowing players to select their
        primary weapon (Machine Gun, Sniper Rifle, Rocket Launcher) and character skin.
        """
        surface.fill((12, 16, 22))

        # Ambient grid
        for gx in range(0, self.screen_w, 64):
            pygame.draw.line(surface, (20, 26, 36), (gx, 0), (gx, self.screen_h), 1)
        for gy in range(0, self.screen_h, 64):
            pygame.draw.line(surface, (20, 26, 36), (0, gy), (self.screen_w, gy), 1)

        cx = self.screen_w // 2

        # Header Title
        title = self.font_title.render("MISSION LOADOUT & CUSTOMIZATION", True, (0, 220, 255))
        subtitle = self.font_main.render("SELECT PRIMARY WEAPON & OPERATOR COMBAT SUIT", True, (160, 190, 220))
        surface.blit(title, (cx - title.get_width() // 2, 22))
        surface.blit(subtitle, (cx - subtitle.get_width() // 2, 64))

        # -------------------------------------------------------------
        # Left Panel: Operator Live Inspection Booth
        # -------------------------------------------------------------
        left_w = 330
        left_h = 510
        left_x = 45
        left_y = 100
        left_rect = pygame.Rect(left_x, left_y, left_w, left_h)
        pygame.draw.rect(surface, (16, 22, 32), left_rect, border_radius=8)
        pygame.draw.rect(surface, (45, 65, 90), left_rect, 2, border_radius=8)

        op_header = self.font_main.render("[ OPERATOR INSPECTION ]", True, (0, 220, 255))
        surface.blit(op_header, (left_rect.centerx - op_header.get_width() // 2, left_y + 14))

        # Staging pedestal
        pedestal_cx = left_rect.centerx
        pedestal_cy = left_y + 175
        pygame.draw.ellipse(surface, (22, 32, 48), (pedestal_cx - 85, pedestal_cy - 45, 170, 90))
        pygame.draw.ellipse(surface, (0, 180, 240), (pedestal_cx - 85, pedestal_cy - 45, 170, 90), 2)
        # Scanner ring animation
        scan_angle = (tick_count * 2.5) % 360
        srad = math.radians(scan_angle)
        sx = pedestal_cx + math.cos(srad) * 65.0
        sy = pedestal_cy + math.sin(srad) * 32.0
        pygame.draw.circle(surface, (0, 255, 200), (int(sx), int(sy)), 4)

        # Draw live rotating soldier sprite
        bank = get_sprite_bank()
        facing_angle = (tick_count * 1.5) % 360
        sprite = bank.get_sprite('player', 'idle', tick_count * 0.05, skin=self.selected_skin_id, weapon=self.selected_weapon_type)
        big_sprite = pygame.transform.scale(sprite, (96, 96))
        rot_sprite = pygame.transform.rotate(big_sprite, -facing_angle)
        rect_rot = rot_sprite.get_rect(center=(pedestal_cx, pedestal_cy - 10))
        surface.blit(rot_sprite, rect_rot.topleft)

        # Current Loadout Specs inside left card
        curr_skin = SKIN_PALETTES.get(self.selected_skin_id, SKIN_PALETTES['NAVY'])
        curr_wp = WEAPON_CATALOG.get(self.selected_weapon_type, WEAPON_CATALOG['MACHINE_GUN'])

        box_y = left_y + 265
        pygame.draw.line(surface, (35, 50, 70), (left_x + 16, box_y), (left_x + left_w - 16, box_y), 1)

        # Suit summary
        s_lbl = self.font_sm.render("OPERATOR SUIT:", True, (140, 160, 190))
        s_val = self.font_main.render(curr_skin['name'], True, curr_skin['accent_color'])
        s_desc = self.font_sm.render(curr_skin['desc'], True, (170, 185, 205))
        surface.blit(s_lbl, (left_x + 20, box_y + 12))
        surface.blit(s_val, (left_x + 20, box_y + 28))
        surface.blit(s_desc, (left_x + 20, box_y + 50))

        # Weapon summary
        box_y2 = box_y + 85
        pygame.draw.line(surface, (35, 50, 70), (left_x + 16, box_y2), (left_x + left_w - 16, box_y2), 1)
        w_lbl = self.font_sm.render("PRIMARY WEAPON:", True, (140, 160, 190))
        w_val = self.font_main.render(curr_wp['name'], True, curr_wp['color'])
        w_sp = self.font_sm.render(f"Special: {curr_wp['trait']}", True, (255, 220, 100))
        w_st = self.font_sm.render(curr_wp['stats'], True, (160, 210, 240))
        surface.blit(w_lbl, (left_x + 20, box_y2 + 12))
        surface.blit(w_val, (left_x + 20, box_y2 + 28))
        surface.blit(w_sp, (left_x + 20, box_y2 + 50))
        surface.blit(w_st, (left_x + 20, box_y2 + 70))

        # Tactical note
        note = self.font_sm.render("Tactical Bayonet is equipped as standard melee.", True, (100, 130, 160))
        surface.blit(note, (left_rect.centerx - note.get_width() // 2, left_y + left_h - 26))

        # -------------------------------------------------------------
        # Right Section: Weapon Selection (Top) & Skin Selection (Bottom)
        # -------------------------------------------------------------
        right_x = 400

        # 1. Weapon Selection Cards
        wp_y = 100
        wp_lbl = self.font_main.render("1. SELECT PRIMARY WEAPON ([1] / [2] / [3] OR CLICK)", True, (255, 220, 120))
        surface.blit(wp_lbl, (right_x, wp_y))

        wp_card_w = 265
        wp_card_h = 160
        self.loadout_weapon_rects = {}
        for idx, (wid, winfo) in enumerate(WEAPON_CATALOG.items()):
            wx = right_x + idx * (wp_card_w + 20)
            wy = wp_y + 26
            wrect = pygame.Rect(wx, wy, wp_card_w, wp_card_h)
            self.loadout_weapon_rects[wid] = wrect

            is_sel = (self.selected_weapon_type == wid)
            bg = (24, 42, 60) if is_sel else (16, 22, 30)
            bcol = winfo['color'] if is_sel else (45, 55, 70)
            bw = 3 if is_sel else 1
            pygame.draw.rect(surface, bg, wrect, border_radius=8)
            pygame.draw.rect(surface, bcol, wrect, bw, border_radius=8)

            badge_surf = self.font_sm.render(winfo['key'], True, (255, 255, 255) if is_sel else (140, 160, 180))
            surface.blit(badge_surf, (wx + 14, wy + 10))

            if is_sel:
                sel_tag = self.font_sm.render("EQUIPPED", True, (0, 255, 180))
                surface.blit(sel_tag, (wx + wp_card_w - sel_tag.get_width() - 14, wy + 10))

            wname = self.font_main.render(winfo['name'], True, winfo['color'] if is_sel else (220, 230, 245))
            surface.blit(wname, (wx + 14, wy + 30))

            trait_tag = self.font_sm.render(f"★ {winfo['badge']}", True, (255, 215, 80) if is_sel else (180, 170, 120))
            surface.blit(trait_tag, (wx + 14, wy + 54))

            # Wrap special-ability copy to the card's inner width.
            max_text_w = wp_card_w - 28
            spec_lines = []
            current_line = ""
            for word in winfo['special'].split():
                candidate = f"{current_line} {word}".strip()
                if current_line and self.font_sm.size(candidate)[0] > max_text_w:
                    spec_lines.append(current_line)
                    current_line = word
                else:
                    current_line = candidate
            if current_line:
                spec_lines.append(current_line)

            for line_idx, line in enumerate(spec_lines[:3]):
                spec_txt = self.font_sm.render(line, True, (200, 220, 240))
                surface.blit(spec_txt, (wx + 14, wy + 80 + line_idx * 16))

            stats_txt = self.font_sm.render(winfo['stats'], True, (130, 160, 190))
            surface.blit(stats_txt, (wx + 14, wy + 132))

        # 2. Skin Selection Cards
        skin_y = 315
        skin_lbl = self.font_main.render("2. SELECT OPERATOR COMBAT SUIT / SKIN ([4]-[8] OR CLICK)", True, (255, 220, 120))
        surface.blit(skin_lbl, (right_x, skin_y))

        sk_card_w = 152
        sk_card_h = 160
        self.loadout_skin_rects = {}
        skin_keys = list(SKIN_PALETTES.keys())
        for idx, skid in enumerate(skin_keys):
            skinfo = SKIN_PALETTES[skid]
            sx = right_x + idx * (sk_card_w + 18)
            sy = skin_y + 26
            skrect = pygame.Rect(sx, sy, sk_card_w, sk_card_h)
            self.loadout_skin_rects[skid] = skrect

            is_sel = (self.selected_skin_id == skid)
            bg = (24, 40, 56) if is_sel else (16, 22, 30)
            bcol = skinfo['accent_color'] if is_sel else (45, 55, 70)
            bw = 3 if is_sel else 1
            pygame.draw.rect(surface, bg, skrect, border_radius=8)
            pygame.draw.rect(surface, bcol, skrect, bw, border_radius=8)

            key_tag = self.font_sm.render(f"[{idx + 4}]", True, (140, 160, 180))
            surface.blit(key_tag, (sx + 10, sy + 8))

            swatch_cx = sx + sk_card_w // 2
            swatch_cy = sy + 44
            pygame.draw.circle(surface, skinfo['c_camo'], (swatch_cx, swatch_cy), 20)
            pygame.draw.circle(surface, skinfo['c_helmet'], (swatch_cx, swatch_cy), 14)
            pygame.draw.circle(surface, skinfo['c_goggles'], (swatch_cx + 4, swatch_cy - 1), 5)
            pygame.draw.circle(surface, bcol, (swatch_cx, swatch_cy), 22, 2)

            sname = self.font_main.render(skinfo['name'], True, skinfo['accent_color'] if is_sel else (210, 225, 240))
            surface.blit(sname, (sx + sk_card_w // 2 - sname.get_width() // 2, sy + 76))

            sdesc = self.font_sm.render(skinfo['desc'][:22], True, (150, 170, 190))
            surface.blit(sdesc, (sx + sk_card_w // 2 - sdesc.get_width() // 2, sy + 102))

            if is_sel:
                eq_tag = self.font_sm.render("[ ACTIVE ]", True, (0, 255, 180))
                surface.blit(eq_tag, (sx + sk_card_w // 2 - eq_tag.get_width() // 2, sy + 132))

        # -------------------------------------------------------------
        # Bottom Actions: Back and Deploy
        # -------------------------------------------------------------
        bar_y = 635
        back_w = 260
        deploy_w = 550
        btn_h = 50

        self.loadout_back_rect = pygame.Rect(right_x, bar_y, back_w, btn_h)
        pygame.draw.rect(surface, (25, 30, 40), self.loadout_back_rect, border_radius=8)
        pygame.draw.rect(surface, (60, 75, 95), self.loadout_back_rect, 1, border_radius=8)
        back_txt = self.font_main.render("< MISSION SETUP [ESC]", True, (180, 200, 220))
        surface.blit(back_txt, (self.loadout_back_rect.centerx - back_txt.get_width() // 2, bar_y + 14))

        self.loadout_deploy_rect = pygame.Rect(right_x + back_w + 25, bar_y, deploy_w, btn_h)
        is_pulse = (tick_count // 25) % 2 == 0
        deploy_bg = (0, 160, 110) if is_pulse else (0, 130, 90)
        pygame.draw.rect(surface, deploy_bg, self.loadout_deploy_rect, border_radius=8)
        pygame.draw.rect(surface, (0, 255, 180), self.loadout_deploy_rect, 2, border_radius=8)
        deploy_txt = self.font_main.render("DEPLOY TO COMBAT [ENTER / SPACE]", True, (255, 255, 255))
        surface.blit(deploy_txt, (self.loadout_deploy_rect.centerx - deploy_txt.get_width() // 2, bar_y + 14))

    def handle_loadout_click(self, mouse_pos, audio_manager):
        """Processes clicks on weapon cards, skin cards, deploy button, and back button."""
        # Check weapon cards
        for wid, rect in self.loadout_weapon_rects.items():
            if rect.collidepoint(mouse_pos):
                if self.selected_weapon_type != wid:
                    self.selected_weapon_type = wid
                    audio_manager.play('menu_select', volume=0.85)
                return 'SELECT_WEAPON'

        # Check skin cards
        for skid, rect in self.loadout_skin_rects.items():
            if rect.collidepoint(mouse_pos):
                if self.selected_skin_id != skid:
                    self.selected_skin_id = skid
                    audio_manager.play('menu_select', volume=0.85)
                return 'SELECT_SKIN'

        # Check deploy
        if self.loadout_deploy_rect.collidepoint(mouse_pos):
            audio_manager.play('menu_select', volume=1.0)
            return 'DEPLOY'

        # Check back
        if self.loadout_back_rect.collidepoint(mouse_pos):
            audio_manager.play('menu_select', volume=0.8)
            return 'BACK'

        return None

    def draw_pause_screen(self, surface):
        """Semi-transparent pause overlay with Resume / Restart / Main Menu buttons."""
        overlay = pygame.Surface((self.screen_w, self.screen_h), pygame.SRCALPHA)
        overlay.fill((5, 10, 18, 190))
        surface.blit(overlay, (0, 0))

        cx = self.screen_w // 2
        cy = self.screen_h // 2

        # Panel
        panel_w = 440
        panel_h = 260
        panel_rect = pygame.Rect(cx - panel_w // 2, cy - panel_h // 2, panel_w, panel_h)
        pygame.draw.rect(surface, (16, 24, 36), panel_rect, border_radius=12)
        pygame.draw.rect(surface, (0, 180, 255), panel_rect, 2, border_radius=12)

        title = self.font_title.render("II  PAUSED", True, (0, 220, 255))
        surface.blit(title, (cx - title.get_width() // 2, panel_rect.top + 18))

        pygame.draw.line(surface, (40, 70, 110),
                         (cx - 160, panel_rect.top + 66), (cx + 160, panel_rect.top + 66), 1)

        # Menu items
        items = [
            ("RESUME  [ ESC ]", (0, 220, 140)),
            ("RESTART MISSION  [ R ]", (255, 190, 50)),
            ("MAIN MENU  [ M ]", (220, 100, 100)),
        ]
        self.pause_btn_rects = []
        for i, (label, col) in enumerate(items):
            btn_rect = pygame.Rect(cx - 180, panel_rect.top + 82 + i * 54, 360, 42)
            self.pause_btn_rects.append(btn_rect)
            pygame.draw.rect(surface, (22, 34, 48), btn_rect, border_radius=6)
            pygame.draw.rect(surface, col, btn_rect, 1, border_radius=6)
            t = self.font_main.render(label, True, col)
            surface.blit(t, (cx - t.get_width() // 2, btn_rect.centery - t.get_height() // 2))

    def handle_pause_click(self, mouse_pos, audio_manager):
        """Returns the pause action selected by the player, if any."""
        for index, rect in enumerate(self.pause_btn_rects):
            if rect.collidepoint(mouse_pos):
                audio_manager.play('menu_select', volume=0.8)
                return ('RESUME', 'RESTART', 'MENU')[index]
        return None

    def handle_start_click(self, mouse_pos, audio_manager):
        """Processes clicks on Start Screen difficulty buttons, map cards, start button and ? button."""
        # Check Difficulty buttons
        for dk, rect in self.diff_rects.items():
            if rect.collidepoint(mouse_pos):
                if self.selected_difficulty != dk:
                    self.selected_difficulty = dk
                    audio_manager.play('menu_select', volume=0.8)
                return 'CHANGE'

        # Check Map buttons
        for mid, rect in self.map_rects.items():
            if rect.collidepoint(mouse_pos):
                if self.selected_map_id != mid:
                    self.selected_map_id = mid
                    audio_manager.play('menu_select', volume=0.8)
                return 'CHANGE'

        # Check Deploy button
        if self.start_btn_rect.collidepoint(mouse_pos):
            audio_manager.play('menu_select', volume=1.0)
            return 'DEPLOY'

        # Check Help (?) button
        if self.help_btn_rect.collidepoint(mouse_pos):
            audio_manager.play('menu_select', volume=0.7)
            return 'HELP'

        return None

    def draw_victory_screen(self, surface, tick_count, stats):
        """Victory screen with letter grade and detailed score breakdown."""
        overlay = pygame.Surface((self.screen_w, self.screen_h), pygame.SRCALPHA)
        overlay.fill((8, 24, 18, 235))
        surface.blit(overlay, (0, 0))

        eval_data = calculate_grade_and_score(stats, is_victory=True)
        cx = self.screen_w // 2

        t1 = self.font_title.render("MISSION ACCOMPLISHED", True, (0, 255, 160))
        t2 = self.font_main.render(eval_data['verdict'], True, (220, 255, 235))
        surface.blit(t1, (cx - t1.get_width() // 2, 45))
        surface.blit(t2, (cx - t2.get_width() // 2, 95))

        self._draw_score_card(surface, stats, eval_data, is_victory=True)

        if (tick_count // 30) % 2 == 0:
            r_prompt = self.font_main.render(
                "PRESS [R] TO PLAY AGAIN   |   [ESC] TO RETURN TO MISSION SETUP",
                True, (255, 255, 255)
            )
            surface.blit(r_prompt, (cx - r_prompt.get_width() // 2, 640))

    def draw_defeat_screen(self, surface, tick_count, stats):
        """Defeat screen with letter grade and loss analysis."""
        overlay = pygame.Surface((self.screen_w, self.screen_h), pygame.SRCALPHA)
        overlay.fill((28, 8, 8, 238))
        surface.blit(overlay, (0, 0))

        eval_data = calculate_grade_and_score(stats, is_victory=False)
        cx = self.screen_w // 2

        t1 = self.font_title.render("KILLED IN ACTION (K.I.A.)", True, (255, 50, 50))
        t2 = self.font_main.render("OPERATOR ELIMINATED - " + eval_data['verdict'], True, (255, 180, 180))
        surface.blit(t1, (cx - t1.get_width() // 2, 45))
        surface.blit(t2, (cx - t2.get_width() // 2, 95))

        self._draw_score_card(surface, stats, eval_data, is_victory=False)

        if (tick_count // 30) % 2 == 0:
            r_prompt = self.font_main.render(
                "PRESS [R] TO RETRY MISSION   |   [ESC] TO RETURN TO MISSION SETUP",
                True, (255, 230, 80)
            )
            surface.blit(r_prompt, (cx - r_prompt.get_width() // 2, 640))

    def _draw_score_card(self, surface, stats, eval_data, is_victory=True):
        cx = self.screen_w // 2
        card_w = 720
        card_h = 480
        card_rect = pygame.Rect(cx - card_w // 2, 135, card_w, card_h)

        bg = (16, 30, 24) if is_victory else (32, 14, 14)
        border = (0, 200, 120) if is_victory else (180, 45, 45)
        pygame.draw.rect(surface, bg, card_rect, border_radius=8)
        pygame.draw.rect(surface, border, card_rect, 2, border_radius=8)

        # Large Grade Badge on Left
        grade_x = cx - 240
        grade_y = 240
        badge_rect = pygame.Rect(grade_x - 70, grade_y - 70, 140, 140)
        pygame.draw.rect(surface, (10, 18, 14), badge_rect, border_radius=12)
        pygame.draw.rect(surface, eval_data['grade_color'], badge_rect, 3, border_radius=12)

        g_tag = self.font_sm.render("OPERATIONAL GRADE", True, (160, 180, 200))
        surface.blit(g_tag, (grade_x - g_tag.get_width() // 2, grade_y - 58))

        g_text = self.font_grade.render(eval_data['grade'], True, eval_data['grade_color'])
        surface.blit(g_text, (grade_x - g_text.get_width() // 2, grade_y - 20))

        score_tag = self.font_sm.render(f"SCORE: {eval_data['final_score']} PTS", True, (255, 230, 100))
        surface.blit(score_tag, (grade_x - score_tag.get_width() // 2, grade_y + 45))

        # Metrics Breakdown on Right
        mx = cx - 110
        my = 160
        header = self.font_main.render("AFTER-ACTION REPORT & SCORING METRICS", True, (220, 235, 255))
        surface.blit(header, (mx, my))
        pygame.draw.line(surface, (60, 80, 100), (mx, my + 24), (mx + 420, my + 24), 1)

        lines = [
            (f"Hostiles Neutralized: {stats.get('enemies_killed', 0)} / {stats.get('total_enemies', 5)}", f"+{eval_data['kill_score']} pts"),
            (f"Operator Vitality: {stats.get('hp', 0)} / {stats.get('max_hp', 10)} HP", f"+{eval_data['hp_score']} pts"),
            (f"Operation Time: {stats.get('time', 0):.1f} seconds", f"+{eval_data['time_score']} pts"),
            (f"Shooting Accuracy: {eval_data['accuracy_pct']}% ({stats.get('shots_hit', 0)}/{stats.get('shots_fired', 0)} hits)", f"+{eval_data['acc_score']} pts"),
            (f"Bayonet Melee Kills: {stats.get('melee_kills', 0)}", f"+{eval_data['melee_bonus']} pts"),
            (f"Raw Combat Score: {eval_data['raw_score']} pts", ""),
            (f"Difficulty Multiplier: {eval_data['diff_key']} ({eval_data['diff_mult']}x)", f"FINAL: {eval_data['final_score']} PTS"),
        ]

        sy = my + 38
        for label, val in lines:
            col = (255, 220, 100) if "FINAL" in val else (200, 220, 240)
            lbl_surf = self.font_sm.render(label, True, col)
            val_surf = self.font_sm.render(val, True, (0, 255, 180) if "+" in val else col)
            surface.blit(lbl_surf, (mx, sy))
            if val:
                surface.blit(val_surf, (mx + 420 - val_surf.get_width(), sy))
            sy += 28
