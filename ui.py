"""
ui.py - Tactical Heads-Up Display (HUD), start menu with difficulty & map selection,
minimap, crosshair, notifications, and end-game Grade A-E evaluation.
"""

import math
import pygame
from map import MAP_METADATA

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


def calculate_grade_and_score(stats, is_victory=True):
    """
    Computes final performance score and assigns Grade A through E.
    Metrics:
    - Kills / Total ratio
    - Remaining HP / Max HP ratio
    - Completion time
    - Shooting accuracy (shots_hit / shots_fired)
    - Melee kills bonus
    - Difficulty multiplier
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

    # Grade Assignment based on combined performance score
    if final_score >= 1200 and is_victory:
        grade = 'A'
        grade_color = (255, 215, 0)      # Tactical Gold
        verdict = "EXEMPLARY COMBAT PERFORMANCE"
    elif final_score >= 900 and is_victory:
        grade = 'B'
        grade_color = (0, 230, 255)      # Cyber Cyan
        verdict = "TACTICAL OBJECTIVE SECURED"
    elif final_score >= 650:
        grade = 'C'
        grade_color = (120, 255, 120)    # Standard Green
        verdict = "OPERATION COMPLETED"
    elif final_score >= 400:
        grade = 'D'
        grade_color = (255, 160, 40)     # Warning Amber
        verdict = "SUB-OPTIMAL ENGAGEMENT"
    else:
        grade = 'E'
        grade_color = (255, 50, 50)      # Critical Red
        verdict = "MISSION COMPROMISED"

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

        # Help modal state
        self.help_tab = 0  # 0=EASY, 1=MEDIUM, 2=HARD
        self.help_tab_rects = []

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

    def draw_hud(self, surface, player, enemies, bullets):
        """Draws player health, enemies remaining, bayonet cooldown, notification, and minimap."""
        # 1. Dynamic Health Bar
        self._draw_health_bar(surface, player)

        # 2. Dynamic Enemy Tracker
        self._draw_enemy_tracker(surface, enemies)

        # 3. Weapon Status
        self._draw_weapon_status(surface, player)

        # 4. Tactical Minimap
        self._draw_minimap(surface, player, enemies)

        # 5. Supply Notification Toast
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

        panel_rect = pygame.Rect(x - 8, y - 6, 330, 58)
        pygame.draw.rect(surface, (14, 18, 24, 215), panel_rect, border_radius=6)
        pygame.draw.rect(surface, (45, 60, 80), panel_rect, 2, border_radius=6)

        mg_txt = self.font_sm.render("[L-CLICK] MACHINE GUN: READY (UNLIMITED)", True, (200, 220, 245))
        surface.blit(mg_txt, (x, y))

        if player.bayonet.can_strike():
            knife_col = (0, 255, 160)
            knife_str = "[SPACE / F] BAYONET: READY (INSTAKILL 1-HIT)"
        else:
            knife_col = (255, 140, 40)
            knife_str = f"[SPACE / F] BAYONET: RECOVERING ({player.bayonet.timer:.1f}s)"

        k_txt = self.font_sm.render(knife_str, True, knife_col)
        surface.blit(k_txt, (x, y + 26))

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

        deploy_txt = self.font_main.render("COMMENCE OPERATION [ENTER / SPACE]", True, (255, 255, 255))
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
        """Multi-page Help modal with EASY / MEDIUM / HARD tabs showing scoring breakdown."""
        # Dim overlay
        overlay = pygame.Surface((self.screen_w, self.screen_h), pygame.SRCALPHA)
        overlay.fill((5, 8, 14, 210))
        surface.blit(overlay, (0, 0))

        modal_w = 820
        modal_h = 510
        modal_x = self.screen_w // 2 - modal_w // 2
        modal_y = self.screen_h // 2 - modal_h // 2

        # Modal background
        pygame.draw.rect(surface, (14, 20, 30), (modal_x, modal_y, modal_w, modal_h), border_radius=10)
        pygame.draw.rect(surface, (0, 160, 255), (modal_x, modal_y, modal_w, modal_h), 2, border_radius=10)

        # Title bar
        title_surf = self.font_title.render("SCORING SYSTEM & DIFFICULTY GUIDE", True, (0, 220, 255))
        surface.blit(title_surf, (
            modal_x + modal_w // 2 - title_surf.get_width() // 2, modal_y + 14
        ))

        # Tab buttons: EASY / MEDIUM / HARD
        tab_labels = ['EASY', 'MEDIUM', 'HARD']
        tab_colors = [(0, 220, 140), (255, 190, 40), (255, 60, 60)]
        tab_w = 160
        tab_h = 34
        tab_y = modal_y + 62
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

        # Content area
        content_y = tab_y + tab_h + 14
        content_x = modal_x + 36
        right_col_x = content_x + 300
        diff_keys_list = ['EASY', 'MEDIUM', 'HARD']
        dk = diff_keys_list[self.help_tab]
        dinfo = DIFFICULTIES[dk]

        pygame.draw.line(surface, (40, 60, 85),
                         (modal_x + 20, content_y), (modal_x + modal_w - 20, content_y), 1)
        content_y += 10

        def row(label, value, lcol=(200, 220, 245), vcol=(0, 230, 180)):
            nonlocal content_y
            ls = self.font_main.render(label, True, lcol)
            vs = self.font_main.render(str(value), True, vcol)
            surface.blit(ls, (content_x, content_y))
            surface.blit(vs, (modal_x + modal_w - 36 - vs.get_width(), content_y))
            content_y += 26

        # Difficulty config section
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
                         (modal_x + 20, content_y), (modal_x + modal_w - 20, content_y), 1)
        content_y += 10

        # Scoring formula section
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
                         (modal_x + 20, content_y), (modal_x + modal_w - 20, content_y), 1)
        content_y += 10

        # Grade thresholds section
        grade_header = self.font_main.render("[ GRADE THRESHOLDS ]", True, (255, 220, 120))
        surface.blit(grade_header, (content_x, content_y))
        content_y += 24

        grades = [
            ("A", f">= 1200 pts  (Victory required)", (255, 215, 0)),
            ("B", f">= 900 pts   (Victory required)", (0, 230, 255)),
            ("C", f">= 650 pts", (120, 255, 120)),
            ("D", f">= 400 pts", (255, 160, 40)),
            ("E", f"< 400 pts", (255, 50, 50)),
        ]
        for g, desc, gcol in grades:
            gs = self.font_main.render(f"  Grade {g}:", True, gcol)
            ds = self.font_sm.render(desc, True, (180, 200, 220))
            surface.blit(gs, (content_x, content_y))
            surface.blit(ds, (content_x + 120, content_y + 3))
            content_y += 22

        # Close hint
        close_txt = self.font_sm.render("[ ESC ] or [ CLICK OUTSIDE ] to close", True, (100, 130, 160))
        surface.blit(close_txt, (
            modal_x + modal_w // 2 - close_txt.get_width() // 2,
            modal_y + modal_h - 26
        ))

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

    def handle_help_click(self, mouse_pos):
        """Handles tab clicks inside the help modal. Returns True if click consumed a tab."""
        for i, tr in enumerate(self.help_tab_rects):
            if tr.collidepoint(mouse_pos):
                self.help_tab = i
                return True
        return False

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
