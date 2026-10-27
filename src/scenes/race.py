import traceback
from enum import Enum, auto

import pygame as pg

from src.scenes.scene import Scene
from src.render import Mode7
from src.course import Course
from src.sprites import Player, TrafficLight
from src.hud import HUD, LAP_COMPLETED
import src.utils as utils


class RacePhase(Enum):
    COUNTDOWN = auto()  # traffic light, no control
    RACING = auto()     # player has control
    FINISHED = auto()   # results over the running scene


class Race(Scene):
    MAX_LAPS = 3

    def __init__(self, game, course_name="track2", **kwargs):
        super().__init__(game)
        self.course_name = course_name
        self.phase = RacePhase.COUNTDOWN

        # read by HUD
        self.race_time = 0.0
        self.lap_start_time = 0.0
        self.current_lap = 1
        self.max_laps = self.MAX_LAPS
        self.current_checkpoint = 0

        self.course = None
        self.player = None
        self.map = None
        self.hud = None
        self.traffic_light = None
        self.checkpoints = []
        self.num_checkpoints = 0

    def startup(self):
        game = self.game
        # sprites, Mode7 and Course queries reach the race objects through game
        game.all_sprites = pg.sprite.Group()
        game.started = False
        game.course = None

        try:
            self.course = Course(game.assets_folder, self.course_name)
        except Exception:
            traceback.print_exc()
        game.course = self.course

        self.player = game.player = Player(game)
        self.traffic_light = TrafficLight(game, (100, 60))
        self.map = game.map = Mode7(game, self.course.image if self.course else None)

        if self.course:
            start_pos = self.course.get_start_position(8)
            if start_pos is not None:
                self.player.pos = start_pos
            self.checkpoints = self.course.game_object_data.get("checkpoints", [])
            self.num_checkpoints = max(
                (obj.properties.get("number", 0) for obj in self.checkpoints), default=0)

        # HUD reads lap/time/player/course from the race scene
        self.hud = HUD(self, self.course.tiled_map if self.course else None)

    def cleanup(self):
        self.game.all_sprites.empty()
        self.game.started = False

    def get_event(self, event):
        self.hud.handle_event(event)
        if event.type != pg.KEYDOWN:
            return
        if event.key == pg.K_ESCAPE:
            self.game.switch_scene("CourseSelect")
        elif event.key == pg.K_RETURN and self.phase == RacePhase.FINISHED:
            self.game.switch_scene("CourseSelect")

    def check_lap_progress(self):
        for checkpoint in self.checkpoints:
            if not utils.point_in_polygon(self.player.pos, checkpoint.points):
                continue
            if checkpoint.name == "finish" and self.current_checkpoint == self.num_checkpoints:
                # show the lap time in the HUD
                pg.event.post(pg.event.Event(LAP_COMPLETED,
                              lap=self.current_lap,
                              lap_time=self.race_time - self.lap_start_time))
                self.lap_start_time = self.race_time
                self.current_lap += 1
                self.current_checkpoint = 0
            elif checkpoint.name == "checkpoint":
                number = checkpoint.properties.get("number")
                if number == self.current_checkpoint + 1:
                    self.current_checkpoint = number

    def update(self, dt):
        game = self.game
        self.map.update(dt)

        if self.phase == RacePhase.COUNTDOWN:
            game.all_sprites.update(dt)
            if self.traffic_light.done:
                self.phase = RacePhase.RACING
                game.started = True

        elif self.phase == RacePhase.RACING:
            self.race_time += dt
            game.all_sprites.update(dt)
            self.check_lap_progress()
            if self.current_lap > self.max_laps:
                self.phase = RacePhase.FINISHED

        elif self.phase == RacePhase.FINISHED:
            # world keeps running, player is frozen
            for sprite in game.all_sprites:
                if sprite is not self.player:
                    sprite.update(dt)

        game.debug_values["phase"] = self.phase.name
        game.debug_values["pos"] = f"{self.player.pos.x:.3f}, {self.player.pos.y:.3f}"
        game.debug_values["last_road_pos"] = (
            f"{self.player.last_road_pos.x:.3f}, {self.player.last_road_pos.y:.3f}")
        game.debug_values["lap"] = f"{self.current_lap}/{self.max_laps}"
        game.debug_values["checkpoint"] = f"{self.current_checkpoint}"

    def blit_scrolling(self, screen, image, rate, y):
        # rate 1.0 = moves with the ground, < 1.0 = farther away
        image_width = image.get_width()
        offset = int(self.player.angle * self.game.sky_speed * rate) % image_width
        x = -offset
        while x < screen.get_width():  # tile if image is narrower than screen
            screen.blit(image, (x, y))
            x += image_width

    def draw(self, screen):
        game = self.game
        self.blit_scrolling(screen, game.background, game.SKY_SCROLL_RATE, 0)
        self.blit_scrolling(screen, game.mountains, game.MOUNTAIN_SCROLL_RATE, game.mountains_y)
        self.map.draw(screen)
        for sprite in game.all_sprites:
            sprite.draw(screen)
        self.hud.draw(screen)

        if self.phase == RacePhase.FINISHED:
            shade = pg.Surface(screen.get_size(), pg.SRCALPHA)
            shade.fill((0, 0, 0, 140))
            screen.blit(shade, (0, 0))
            center_x = screen.get_width() // 2
            self.draw_text(screen, "FINISH!", (center_x, 40), "yellow")
            self.draw_text(screen, f"Time: {HUD.format_time(self.race_time)}", (center_x, 65))
            self.draw_text(screen, "Enter: continue", (center_x, 110))