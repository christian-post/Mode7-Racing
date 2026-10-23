import numpy as np
from numba import njit
import pygame as pg
from math import sin, cos, pi


class Mode7:
    def __init__(self, game, sprite=None, size=(1024, 1024)):
        self.game = game
        if sprite:
            self.image = sprite
            self.size = sprite.get_size()
        else:
            self.image = pg.Surface(size)
            self.image.fill(pg.Color("black"))
            
            tilesize = 32
            for x in range(0, size[0], tilesize):
                pg.draw.line(self.image, pg.Color("darkturquoise"),
                             (x, 0), (x, size[1]), 4)
            for y in range(0, size[1], tilesize):
                pg.draw.line(self.image, pg.Color("blueviolet"),
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
        
                # forward distance shown at the screen row where the kart touches the ground
        kart_ground_row = 115  # roughly player.rect.bottom (without jiggle)
        horizon_offset = int(screen_rect.h * self.game.HORIZON)
        sample_depth = (kart_ground_row - horizon_offset) / screen_rect.h
        edge_distance = (self.far - self.near) / sample_depth + self.near
        camera_offset = edge_distance * cos(self.fov_half)

        # move camera back so player.pos lands under the kart sprite
        camera_x = player.pos.x - cos(player.angle) * camera_offset
        camera_y = player.pos.y - sin(player.angle) * camera_offset

        # Calculate frustum corners
        far_x1 = camera_x + cos(player.angle - self.fov_half) * self.far
        far_y1 = camera_y + sin(player.angle - self.fov_half) * self.far
        near_x1 = camera_x + cos(player.angle - self.fov_half) * self.near
        near_y1 = camera_y + sin(player.angle - self.fov_half) * self.near

        far_x2 = camera_x + cos(player.angle + self.fov_half) * self.far
        far_y2 = camera_y + sin(player.angle + self.fov_half) * self.far
        near_x2 = camera_x + cos(player.angle + self.fov_half) * self.near
        near_y2 = camera_y + sin(player.angle + self.fov_half) * self.near
        
        # Render using compiled function
        screen_array = pg.surfarray.pixels3d(screen)

        # tile grid dimensions (same mapping as ground_speed_at)
        if self.game.speed_grid is not None:
            grid_w, grid_h = self.game.speed_grid.shape
        else:
            grid_w, grid_h = 32, 32
        player_tile_x = int((player.pos.x % 1) * grid_w)
        player_tile_y = int((player.pos.y % 1) * grid_h)
        
        render_mode7(
            screen_array,
            self.image_array,
            screen_rect.w, screen_rect.h,
            self.rect.w, self.rect.h,
            far_x1, far_y1, near_x1, near_y1,
            far_x2, far_y2, near_x2, near_y2,
            self.game.HORIZON,
            grid_w, grid_h,
            player_tile_x, player_tile_y, 
            self.game.show_debug
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
def render_mode7(
    screen_array, image_array, screen_w, screen_h,
    image_w, image_h,
    far_x1, far_y1, near_x1, near_y1,
    far_x2, far_y2, near_x2, near_y2,
    horizon, grid_w, grid_h,
    player_tile_x, player_tile_y, highlight):
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
            
            # Copy pixel (RGB), tint the player's tile
            tile_x = int(wrapped_x * grid_w)
            tile_y = int(wrapped_y * grid_h)
            if highlight and tile_x == player_tile_x and tile_y == player_tile_y:
                screen_array[x, y_screen, 0] = (int(image_array[tex_x, tex_y, 0]) + 255) // 2
                screen_array[x, y_screen, 1] = int(image_array[tex_x, tex_y, 1]) // 2
                screen_array[x, y_screen, 2] = int(image_array[tex_x, tex_y, 2]) // 2
            else:
                screen_array[x, y_screen, 0] = image_array[tex_x, tex_y, 0]
                screen_array[x, y_screen, 1] = image_array[tex_x, tex_y, 1]
                screen_array[x, y_screen, 2] = image_array[tex_x, tex_y, 2]
            
            # Move to next pixel along scanline
            sample_x += dx
            sample_y += dy
            