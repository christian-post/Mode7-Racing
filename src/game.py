import pygame as pg

try:
    from pytmx.util_pygame import load_pygame
except ModuleNotFoundError:
    print('Warning: Pytmx is not installed')
    
import traceback
from math import sin, cos, pi
from os import path
import numpy as np
from numba import njit

from src.sprites import Player, TrafficLight



def load_map(folder, name):
    """
    load a Tiled map in .tmx format and return a background image Surface, 
    map objects as a TiledObjectGroup and layer_data as a list of 2D arrays
    with tile indices
    """
    tiled_map = load_pygame(path.join(folder, f'{name}.tmx'))
    # create empty surface based on tile map dimensions
    bg_image = pg.Surface((tiled_map.width * tiled_map.tilewidth,
                          tiled_map.height * tiled_map.tileheight))
    # iterate through each tile layer and blit the corresponding tile
    layer_data = []
    for layer in tiled_map.layers:
        if hasattr(layer, 'data'):
            layer_data.append(layer.data)
            for x, y, image in layer.tiles():
                if image:
                    bg_image.blit(image, (x * tiled_map.tilewidth, 
                                          y * tiled_map.tileheight))
    return bg_image, layer_data


class Game:

    HORIZON = 0.2

    def __init__(self):
        pg.init()
        self.clock = pg.time.Clock()
        self.display_screen = pg.display.set_mode((800, 600))
        self.display_rect = self.display_screen.get_rect()
        self.game_screen = pg.Surface((200, 150))
        self.game_screen_rect = self.game_screen.get_rect()
        # specify the directories for asset loading
        base_dir = path.dirname(__file__)
        assets_folder = path.join(base_dir, '..', 'assets')

        bg_image = pg.image.load(path.join(assets_folder, 'clouds-4258726_640.jpg')).convert()
        
        # Calculate horizon position (must match Mode7.update())
        horizon_y = int(self.game_screen.get_height() * self.HORIZON)
        
        # Scale image to fit width and height above horizon
        self.background = pg.transform.scale(bg_image, 
                                            (self.game_screen.get_width(), horizon_y))

        self.fps = 60
        self.all_sprites = pg.sprite.Group()
        self.running = True
        
        player_image_strip = pg.image.load(
                path.join(assets_folder, 'kart.png')).convert_alpha()
        self.player_images = [player_image_strip.subsurface((i * 30, 0, 30, 32)) 
                              for i in range(11)]
        
        self.cloud_image = pg.image.load(
                path.join(assets_folder, 'cloud.png')).convert_alpha()
        self.traffic_light_images = pg.image.load(
                path.join(assets_folder, 'lights.png')).convert_alpha()
        self.bush_image = pg.image.load(
                path.join(assets_folder, 'bush.png')).convert_alpha()  # TODO: unused
        
        self.player = Player(self)
        self.traffic_light = TrafficLight(self, (100, 60))
        
        try:
            self.map_img, _ = load_map(folder=assets_folder, name='track2')
            self.map = Mode7(self, self.map_img)
        except Exception:
            traceback.print_exc()
            self.map = Mode7(self)
            
        self.started = False
        
    
    def events(self):
        for event in pg.event.get():
            if event.type == pg.QUIT:
                self.running = False

    
    def update(self, dt):
        self.game_screen.blit(self.background, (0, 0))
        self.map.update(dt)
        self.all_sprites.update(dt)
        
        if self.traffic_light.done:
            self.started = True
        

    def draw(self):
        for s in self.all_sprites:
            s.draw(self.game_screen)
        
        transformed_screen = pg.transform.scale(self.game_screen,
                                                self.display_rect.size)
        self.display_screen.blit(transformed_screen, (0, 0))
        pg.display.update()
        
        
    def run(self):
        self.running = True
        while self.running:
            delta_time = self.clock.tick(self.fps) / 1000
            pg.display.set_caption(f'FPS: {round(self.clock.get_fps(), 2)}')
            self.events()        
            self.update(delta_time)
            self.draw()
        
        pg.quit()
        
        
        
class Mode7:
    def __init__(self, game, sprite=None, size=(1024, 1024)):
        self.game = game
        if sprite:
            self.image = sprite
            self.size = sprite.get_size()
        else:
            self.image = pg.Surface(size)
            self.image.fill(pg.Color('black'))
            
            tilesize = 32
            for x in range(0, size[0], tilesize):
                pg.draw.line(self.image, pg.Color('darkturquoise'),
                             (x, 0), (x, size[1]), 4)
            for y in range(0, size[1], tilesize):
                pg.draw.line(self.image, pg.Color('blueviolet'),
                             (0, y), (size[0], y), 4)
        self.rect = self.image.get_rect()
        
        # Convert source image to numpy array once
        self.image_array = pg.surfarray.array3d(self.image)
        
        self.near = 0.005
        self.far = 0.01215
        self.fov_half = pi / 4
        
    def update(self, dt):
        screen = self.game.game_screen
        screen_rect = self.game.game_screen_rect
        player = self.game.player
        
        # Calculate frustum corners
        far_x1 = player.pos.x + cos(player.angle - self.fov_half) * self.far
        far_y1 = player.pos.y + sin(player.angle - self.fov_half) * self.far
        near_x1 = player.pos.x + cos(player.angle - self.fov_half) * self.near
        near_y1 = player.pos.y + sin(player.angle - self.fov_half) * self.near
        
        far_x2 = player.pos.x + cos(player.angle + self.fov_half) * self.far
        far_y2 = player.pos.y + sin(player.angle + self.fov_half) * self.far
        near_x2 = player.pos.x + cos(player.angle + self.fov_half) * self.near
        near_y2 = player.pos.y + sin(player.angle + self.fov_half) * self.near
        
        # Render using compiled function
        screen_array = pg.surfarray.pixels3d(screen)
        
        render_mode7(
            screen_array,
            self.image_array,
            screen_rect.w, screen_rect.h,
            self.rect.w, self.rect.h,
            far_x1, far_y1, near_x1, near_y1,
            far_x2, far_y2, near_x2, near_y2,
            self.game.HORIZON
        )
        
        del screen_array  # Release the lock on the surface
        
        # Debug controls
        keys = pg.key.get_pressed()
        if keys[pg.K_LEFT]:
            self.near -= 0.05 * dt
        elif keys[pg.K_RIGHT]:
            self.near += 0.05 * dt
            self.near = min(self.near, 0.01)
        if keys[pg.K_UP]:
            self.far += 0.05 * dt
        elif keys[pg.K_DOWN]:
            self.far -= 0.05 * dt
            self.far = max(self.far, 0.01)
        if keys[pg.K_q]:
            self.fov_half -= 0.2 * dt
        elif keys[pg.K_e]:
            self.fov_half += 0.2 * dt


@njit(cache=True, fastmath=True)
def render_mode7(screen_array, image_array, screen_w, screen_h,
                 image_w, image_h,
                 far_x1, far_y1, near_x1, near_y1,
                 far_x2, far_y2, near_x2, near_y2,
                 horizon):
    """
    JIT-compiled Mode7 renderer - this will be compiled to machine code
    """
    horizon_offset = int(screen_h * horizon)
    
    for y in range(screen_h):
        # Prevent division by zero
        sample_depth = y / screen_h + 0.0000001
        
        # Perspective calculation
        start_x = (far_x1 - near_x1) / sample_depth + near_x1
        start_y = (far_y1 - near_y1) / sample_depth + near_y1
        end_x = (far_x2 - near_x2) / sample_depth + near_x2
        end_y = (far_y2 - near_y2) / sample_depth + near_y2
        
        # Pre-calculate deltas for the scanline
        dx = (end_x - start_x) / screen_w
        dy = (end_y - start_y) / screen_w
        
        # Current sample position
        sample_x = start_x
        sample_y = start_y
        
        y_screen = y + horizon_offset
        if y_screen >= screen_h:
            continue
        
        for x in range(screen_w):
            # Wrap coordinates for infinite tiling
            wrapped_x = sample_x - int(sample_x)
            wrapped_y = sample_y - int(sample_y)
            
            if wrapped_x < 0:
                wrapped_x += 1
            if wrapped_y < 0:
                wrapped_y += 1
            
            # Sample texture
            tex_x = int(wrapped_x * image_w) % image_w
            tex_y = int(wrapped_y * image_h) % image_h
            
            # Copy pixel (RGB)
            screen_array[x, y_screen, 0] = image_array[tex_x, tex_y, 0]
            screen_array[x, y_screen, 1] = image_array[tex_x, tex_y, 1]
            screen_array[x, y_screen, 2] = image_array[tex_x, tex_y, 2]
            
            # Move to next pixel along scanline
            sample_x += dx
            sample_y += dy
            