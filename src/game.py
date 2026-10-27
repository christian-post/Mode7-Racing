import pygame as pg
    
from math import pi
from os import path
import numpy as np

from src.scenes import SCENES

vec = pg.math.Vector2



class Game:
    # some settings, TODO put in .ini
    HORIZON = 0.2
    SKY_IMAGE_SCALE = 0.2
    SKY_SCROLL_RATE = 1.0
    MOUNTAIN_SCROLL_RATE = 0.6
    FPS = 60
    DISPLAY_W = 800
    DISPLAY_H = 600
    GAME_SCREEN_W = 200
    GAME_SCREEN_H = 150


    def __init__(self):
        pg.init()

        # debugging
        self.debug_font = pg.font.SysFont('consolas', 16)
        self.show_debug = False
        self.debug_values = {}

        # game variables
        self.clock = pg.time.Clock()
        self.display_screen = pg.display.set_mode((self.DISPLAY_W, self.DISPLAY_H))
        self.display_rect = self.display_screen.get_rect()
        self.game_screen = pg.Surface((self.GAME_SCREEN_W, self.GAME_SCREEN_H))
        self.game_screen_rect = self.game_screen.get_rect()
        # specify the directories for asset loading
        base_dir = path.dirname(__file__)
        assets_folder = path.join(base_dir, "..", "assets")
        self.assets_folder = assets_folder

        bg_image = pg.image.load(path.join(assets_folder, "tilesetOpenGameBackground.png")).convert()
        
        # Calculate horizon position (must match Mode7.update())
        horizon_y = int(self.game_screen.get_height() * self.HORIZON)

        img = pg.transform.smoothscale(bg_image, (int(bg_image.get_width() * self.SKY_IMAGE_SCALE), int(bg_image.get_height() * self.SKY_IMAGE_SCALE)))
        self.background = img.subsurface((0, img.get_height() - horizon_y,
                                        img.get_width(), horizon_y)).copy()
        # px per radian so the sky moves at the same rate as the ground (90 deg FOV)
        self.sky_speed = self.game_screen.get_width() / (pi / 2)

        # parallax maountains
        mountains_scale = 0.5  # mountain image scale
        mountains_image = pg.image.load(path.join(assets_folder, "mountains.png")).convert_alpha()
        self.mountains = pg.transform.smoothscale(
            mountains_image,
            (int(mountains_image.get_width() * mountains_scale),
             int(mountains_image.get_height() * mountains_scale)))
        self.mountains_y = horizon_y - self.mountains.get_height()

        self.fps = self.FPS  # make instance attribut in case this gets changed by settings etc
        self.all_sprites = pg.sprite.Group()
        self.billboards = pg.sprite.Group()
        self.running = True
        
        player_image_strip = pg.image.load(
                path.join(assets_folder, "kart2.png")).convert_alpha()
        self.player_images = [player_image_strip.subsurface((i * 30, 0, 30, 32)) 
                              for i in range(11)]
        
        self.cloud_image = pg.image.load(
                path.join(assets_folder, "cloud.png")).convert_alpha()
        self.dirt_image = pg.image.load(
                path.join(assets_folder, "dirt.png")).convert_alpha()
        self.traffic_light_images = pg.image.load(
                path.join(assets_folder, "lights.png")).convert_alpha()

        self.font = pg.font.Font(path.join(assets_folder, "PressStart2P.ttf"), 8)  # menu text

        # race objects, set by the Race scene (sprites access them through game)
        self.player = None
        self.course = None
        self.map = None
        self.started = False  # if the race has started (starts after green light)

        # scene stack: top scene gets events/updates,
        # transparent scenes also draw the scene below them
        self.scene_stack = []
        self.push_scene("TitleScreen")


    # --- scene management ---

    def push_scene(self, name, **kwargs):
        scene = SCENES[name](self, **kwargs)
        self.scene_stack.append(scene)
        scene.startup()


    def pop_scene(self):
        self.scene_stack.pop().cleanup()
        if not self.scene_stack:
            self.running = False


    def switch_scene(self, name, **kwargs):
        # replace the whole stack with a new scene
        while self.scene_stack:
            self.scene_stack.pop().cleanup()
        self.debug_values.clear()
        self.push_scene(name, **kwargs)


    def ground_speed_at(self, pos):
        return self.course.ground_speed_at(pos) if self.course else 1.0


    def check_in_killzone(self, pos):
        return self.course.in_killzone(pos) if self.course else False


    def events(self):
        for event in pg.event.get():
            if event.type == pg.QUIT:
                self.running = False

            if event.type == pg.KEYDOWN and event.key == pg.K_F1:
                self.show_debug = not self.show_debug

            # builtin and custom events go to the active scene
            if self.scene_stack:
                self.scene_stack[-1].get_event(event)


    def update(self, dt):
        if self.scene_stack:
            self.scene_stack[-1].update(dt)


    def draw_debug(self):
        line_y = 5
        for name, value in self.debug_values.items():
            if isinstance(value, float):
                value = f'{value:.4f}'
            text = self.debug_font.render(f'{name}: {value}', True,
                                        pg.Color('white'), pg.Color('black'))
            self.display_screen.blit(text, (5, line_y))
            line_y += text.get_height()
        

    def draw(self):
        # find the lowest visible scene, then draw upwards
        first_visible = len(self.scene_stack) - 1
        while first_visible > 0 and self.scene_stack[first_visible].transparent:
            first_visible -= 1
        for scene in self.scene_stack[first_visible:]:
            scene.draw(self.game_screen)

        # scale up the game screen to the display
        transformed_screen = pg.transform.scale(self.game_screen, self.display_rect.size)
        self.display_screen.blit(transformed_screen, (0, 0))

        if self.show_debug:
            self.draw_debug()

        pg.display.update()
        
        
    def run(self):
        self.running = True
        while self.running:
            delta_time = self.clock.tick(self.fps) / 1000
            pg.display.set_caption(f"FPS: {round(self.clock.get_fps(), 2)}")
            self.events()        
            self.update(delta_time)
            self.draw()
        
        pg.quit()
        
        
        
