import pygame as pg

vec = pg.math.Vector2

# posted by Game with attributes: lap (int), lap_time (float, seconds)
LAP_COMPLETED = pg.event.custom_type()


def build_minimap(tiled_map, size, layer_name="road",
                  road_color=(230, 230, 230, 220), bg_color=(0, 0, 0, 110)):
    # road tiles as pixel mask (1 px per tile), scaled to minimap size
    surf = pg.Surface((tiled_map.width, tiled_map.height), pg.SRCALPHA)
    surf.fill(bg_color)
    layer = tiled_map.get_layer_by_name(layer_name)
    for x, y, gid in layer.iter_data():
        if gid:
            surf.set_at((x, y), road_color)
    return pg.transform.scale(surf, size)


class HUD:
    # sizes are in game_screen pixels (drawn before upscaling)
    MARGIN = 3
    FONT_PATH = None  # path to a .ttf pixel font, None = pygame default
    FONT_SIZE = 14
    MINIMAP_SIZE = (36, 36)
    SPEED_BARS = 6
    BAR_W = 2
    BAR_GAP = 1
    BAR_MIN_H = 2
    BAR_STEP_H = 1
    MAX_SPEED = 240  # max speed approximation, TODO set elswhere
    LAP_TIME_DURATION = 5000  # ms the last lap time stays visible

    def __init__(self, game, tiled_map=None):
        self.game = game
        self.font = pg.font.Font(self.FONT_PATH, self.FONT_SIZE)
        self.minimap = build_minimap(tiled_map, self.MINIMAP_SIZE) if tiled_map else None
        self.last_lap_time = None
        self.lap_time_until = 0  # pg.time.get_ticks() timestamp

    def handle_event(self, event):
        if event.type == LAP_COMPLETED:
            self.last_lap_time = event.lap_time
            self.lap_time_until = pg.time.get_ticks() + self.LAP_TIME_DURATION

    @staticmethod
    def format_time(t):
        m, s = divmod(t, 60)
        return f"{int(m):02d}:{s:05.2f}"

    def draw_text(self, screen, text, pos, anchor="topright"):
        # no antialiasing to keep hard pixel edges
        shadow = self.font.render(text, False, (0, 0, 0))
        surf = self.font.render(text, False, (255, 255, 255))
        rect = surf.get_rect(**{anchor: pos})
        screen.blit(shadow, rect.move(1, 1))
        screen.blit(surf, rect)
        return rect

    def draw_lap_and_time(self, screen):
        g = self.game
        lap = min(g.current_lap, g.max_laps)
        self.draw_text(screen, f"LAP {lap}/{g.max_laps}",
                       (self.MARGIN, self.MARGIN), anchor="topleft")
        right = screen.get_width() - self.MARGIN
        r = self.draw_text(screen, f"TIME {self.format_time(g.race_time)}",
                           (right, self.MARGIN))

        # last lap time, shown briefly after finishing a lap
        if self.last_lap_time is not None and pg.time.get_ticks() < self.lap_time_until:
            self.draw_text(screen, f"LAP {self.format_time(self.last_lap_time)}",
                           (right, r.bottom))

    def draw_speedometer(self, screen):
        frac = min(self.game.player.vel.length() / self.MAX_SPEED, 1.0)
        lit = round(frac * self.SPEED_BARS)
        x = self.MARGIN
        bottom = screen.get_height() - self.MARGIN
        for i in range(self.SPEED_BARS):
            h = self.BAR_MIN_H + i * self.BAR_STEP_H
            rect = pg.Rect(x, bottom - h, self.BAR_W, h)
            if i < lit:
                t = i / max(self.SPEED_BARS - 1, 1)
                color = (int(80 + 175 * t), int(230 - 150 * t), 60)  # green -> red
            else:
                color = (60, 60, 60)
            pg.draw.rect(screen, (0, 0, 0), rect.inflate(2, 2))
            pg.draw.rect(screen, color, rect)
            x += self.BAR_W + self.BAR_GAP

    def draw_minimap(self, screen):
        if self.minimap is None:
            return
        mw, mh = self.MINIMAP_SIZE
        rect = self.minimap.get_rect(bottomright=(screen.get_width() - self.MARGIN,
                                                  screen.get_height() - self.MARGIN))
        screen.blit(self.minimap, rect)
        pg.draw.rect(screen, (255, 255, 255), rect.inflate(2, 2), 1)

        # player as single pixel + heading pixel (dot)
        p = self.game.player
        map_w = self.game.course.pixel_width
        map_h = self.game.course.pixel_height
        dot = vec(rect.x + (p.pos.x % map_w) / map_w * mw,
                rect.y + (p.pos.y % map_h) / map_h * mh)
        tip = dot + vec(2, 0).rotate_rad(p.angle)
        screen.set_at((int(tip.x), int(tip.y)), (255, 200, 60))
        pg.draw.rect(screen, (255, 60, 60), (int(dot.x) - 1, int(dot.y) - 1, 2, 2))

    def draw(self, screen):
        self.draw_lap_and_time(screen)
        self.draw_speedometer(screen)
        self.draw_minimap(screen)