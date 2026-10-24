import pygame as pg

try:
    from pytmx.util_pygame import load_pygame
except ModuleNotFoundError:
    print("Warning: Pytmx is not installed")
    
import traceback
from math import pi
from os import path
import numpy as np

from src.render import Mode7
from src.sprites import Player, TrafficLight
from src.hud import HUD, LAP_COMPLETED
import src.utils as utils

vec = pg.math.Vector2



def load_map(folder, name):
    """
    load a Tiled map in .tmx format and return a background image Surface, 
    map objects as a TiledObjectGroup and layer_data as a list of 2D arrays
    with tile indices
    """
    tiled_map = load_pygame(path.join(folder, f"{name}.tmx"))
    # create empty surface based on tile map dimensions
    bg_image = pg.Surface((tiled_map.width * tiled_map.tilewidth,
                          tiled_map.height * tiled_map.tileheight))
    # iterate through each tile layer and blit the corresponding tile
    layer_data = []
    for layer in tiled_map.layers:
        if hasattr(layer, "data"):
            layer_data.append(layer.data)
            for x, y, image in layer.tiles():
                if image:
                    bg_image.blit(image, (x * tiled_map.tilewidth, 
                                          y * tiled_map.tileheight))

    # load object layers
    object_data = {}
    for group in tiled_map.objectgroups:
        object_data[group.name] = []
        for obj in group:
            object_data[group.name].append(obj)

    return bg_image, layer_data, tiled_map, object_data


def build_speed_grid(tiled_map, road_layer="layer2", offroad=0.3):
    # speed factor of 1 where the road layer has a tile, offroad factor elsewhere
    grid = np.full((tiled_map.width, tiled_map.height), offroad, dtype=np.float32)
    layer = tiled_map.get_layer_by_name(road_layer)
    for x, y, gid in layer.iter_data():
        if gid:
            grid[x, y] = 1.0
    return grid


def build_killzone_grid(tiled_map, killzone_layer="killzone"):
    grid = np.full((tiled_map.width, tiled_map.height), False, dtype=bool)
    layer = tiled_map.get_layer_by_name(killzone_layer)
    for x, y, gid in layer.iter_data():
        if gid:
            grid[x, y] = True
    return grid



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
        self.bush_image = pg.image.load(
                path.join(assets_folder, "bush.png")).convert_alpha()  # TODO: unused
        
        self.player = Player(self)
        self.traffic_light = TrafficLight(self, (100, 60))

        self.speed_grid = None
        self.killzone_grid = None
        self.game_object_data = None  # raw Tiled game objects, TODO handle how they are loaded and unloaded differently
        tiled_map = None
        self.race_time = 0.0
        self.lap_start_time = 0.0

        # load the tilemap
        try:
            self.map_img, _, tiled_map, self.game_object_data = load_map(folder=assets_folder, name="track2")

            # debug-draw checkpoint polygons onto the map texture
            if self.show_debug:
                for obj in self.game_object_data["checkpoints"]:
                    color = "red" if obj.name == "finish" else "yellow"
                    pg.draw.polygon(self.map_img, color, obj.points, 8)

            self.speed_grid = build_speed_grid(tiled_map)
            self.killzone_grid = build_killzone_grid(tiled_map)
            self.map = Mode7(self, self.map_img)
        except Exception:
            traceback.print_exc()
            self.map = Mode7(self)


        self.hud = HUD(self, tiled_map)    
        self.started = False  # if the race has started (starts after green light)
        self.current_lap = 1
        self.max_laps = 3
        self.current_checkpoint = 0
        self.num_checkpoints = max([obj.properties.get("number", 0) for obj in self.game_object_data["checkpoints"]])


    def ground_speed_at(self, pos):
        # get speed depending on which tile you are on
        if self.speed_grid is None:
            return 1.0
        gw, gh = self.speed_grid.shape
        tx = int((pos.x % 1) * gw)
        ty = int((pos.y % 1) * gh)
        return self.speed_grid[tx, ty]


    def check_in_killzone(self, pos):
        # check if this position is within the killzone grid
        if self.killzone_grid is None:
            return False

        gw, gh = self.killzone_grid.shape      
        tx = int((pos.x % 1) * gw)
        ty = int((pos.y % 1) * gh)
        return self.killzone_grid[tx, ty]


    def blit_scrolling(self, image, rate, y):
        # rate 1.0 = moves with the ground, < 1.0 = farther away
        image_width = image.get_width()
        offset = int(self.player.angle * self.sky_speed * rate) % image_width
        x = -offset
        while x < self.game_screen_rect.w:  # tile if image is narrower than screen
            self.game_screen.blit(image, (x, y))
            x += image_width
        
    
    def events(self):
        # builtin events
        for event in pg.event.get():
            if event.type == pg.QUIT:
                self.running = False

            if event.type == pg.KEYDOWN and event.key == pg.K_F1:
                self.show_debug = not self.show_debug

            # custom events
            self.hud.handle_event(event)

    
    def update(self, dt):
        # construct the skybox
        self.blit_scrolling(self.background, self.SKY_SCROLL_RATE, 0)
        self.blit_scrolling(self.mountains, self.MOUNTAIN_SCROLL_RATE, self.mountains_y)
        self.map.update(dt)
        self.all_sprites.update(dt)

        # check for lap progression
        map_w, map_h = self.map_img.get_size()
        pixel_pos = vec((self.player.pos.x % 1) * map_w, (self.player.pos.y % 1) * map_h)
        for obj in self.game_object_data["checkpoints"]:
            if utils.point_in_polygon(pixel_pos, obj.points):
                if obj.name == "finish" and self.current_checkpoint == self.num_checkpoints:
                    # show the lap time in the HUD
                    pg.event.post(pg.event.Event(LAP_COMPLETED,
                                 lap=self.current_lap,
                                 lap_time=self.race_time - self.lap_start_time))
                    self.lap_start_time = self.race_time
                    self.current_lap += 1
                    self.current_checkpoint = 0
                elif obj.name == "checkpoint":
                    number = obj.properties.get("number")
                    if number == self.current_checkpoint + 1:
                        self.current_checkpoint = number

        
        if self.traffic_light.done:
            self.started = True

        if self.started and self.current_lap <= self.max_laps:
            self.race_time += dt

        # DEBUGGING
        self.debug_values['pos'] = f'{self.player.pos.x:.3f}, {self.player.pos.y:.3f}'
        self.debug_values['last_road_pos'] = f'{self.player.last_road_pos.x:.3f}, {self.player.last_road_pos.y:.3f}'
        self.debug_values['lap'] = f'{self.current_lap}/{self.max_laps}'
        self.debug_values['checkpoint'] = f'{self.current_checkpoint}'


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
        for s in self.all_sprites:
            s.draw(self.game_screen)

        # overlay
        self.hud.draw(self.game_screen)
        
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
        
        
        
