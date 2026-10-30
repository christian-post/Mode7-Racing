import pygame as pg
from math import sin, cos, pi
from os import path
from enum import Enum

from src.particle import Particle

vec = pg.math.Vector2


# ENUMS correspond to kart image index
LEFT = [5, 4, 3, 2, 1, 0]
RIGHT = [5, 6, 7, 8, 9, 10]

class Direction(Enum):
    LEFT = 0
    RIGHT = 1


class Player(pg.sprite.Sprite):
    def __init__(self, game):
        super().__init__(game.all_sprites)
        self.game = game

        self.angle = -1.54  # TODO should depend on teh track's starting line orientation
        self.acc = vec()
        self.vel = vec()
        self.pos = vec(2892.8, 1216.0)  # fallback if course has no start positions
        self.speed = 1800
        self.last_road_pos = vec(0, 0)  # last known position on road
        
        self.image = game.player_images[LEFT[0]]
        self.rect = self.image.get_rect()
        self.rect.topleft = (84, 84)
        
        self.time_passed = 0 # seconds from the start of the game
        self.steer_time = 0 # seconds the player is pressing a direction
        self.lastdir: Direction = Direction.LEFT
        self.moving = 1 # 1 forward, -1 backwards
        self.dust_timer = 0
        self.dirt_timer = 0
        
    
    def update(self, dt):
        self.time_passed += dt

        keys = pg.key.get_pressed()
        
        if not self.game.started:
            if keys[pg.K_w]:
                self.dust_timer += dt
                if self.dust_timer >= 0.3:
                    # create two particles (left and right)
                    Particle(
                        self.game, 
                        self.rect.bottomright, 
                        images=[self.game.cloud_image],
                        colors=[pg.Color('white')],
                        vel=vec(1, 0),
                        random_angle=20,
                        vanish_speed=20,
                        end_size=1.4
                        )
                    Particle(
                        self.game, 
                        self.rect.bottomleft, 
                        images=[self.game.cloud_image],
                        colors=[pg.Color('white')],
                        vel=vec(-1, 0),
                        random_angle=20,
                        vanish_speed=20,
                        end_size=1.4
                        )
                    self.dust_timer = 0
            
        else:
            if self.moving == 1:
                turn_force = 0.00625 # how much the angle changes when turning
            else:
                turn_force = 0.015625
            steer_anim_speed = 10 # turning animation speed
            
            current_speed = self.vel.length()
            
            # steer
            # cap the image index at 4 (len of animation minus 2)
            index = min(4, int(self.steer_time * steer_anim_speed))
            
            if keys[pg.K_a]:
                # turning left
                if self.lastdir == Direction.RIGHT:
                    self.steer_time = 0
                # increase the steering time
                self.steer_time += dt
                self.angle -= turn_force * dt * current_speed * self.moving
                # add 1 to the index to get the first turning sprite and set the image
                if self.moving == 1:
                    self.image = self.game.player_images[LEFT[index + 1]]
                else:
                    self.image = self.game.player_images[RIGHT[index + 1]]
                self.lastdir = Direction.LEFT
            elif keys[pg.K_d]:
                # turning right
                if self.lastdir == Direction.LEFT:
                    self.steer_time = 0
                self.steer_time += dt
                self.angle += turn_force * dt * current_speed * self.moving
                if self.moving == 1:
                    self.image = self.game.player_images[RIGHT[index + 1]]
                else:
                    self.image = self.game.player_images[LEFT[index + 1]]
                self.lastdir = Direction.RIGHT
            else:
                if self.lastdir == Direction.LEFT and self.moving == 1:
                    self.image = self.game.player_images[LEFT[index]]
                elif self.lastdir == Direction.LEFT and self.moving == -1:
                    self.image = self.game.player_images[RIGHT[index]]
                elif self.lastdir == Direction.RIGHT and self.moving == 1:
                    self.image = self.game.player_images[RIGHT[index]]
                elif self.lastdir == Direction.RIGHT and self.moving == -1:
                    self.image = self.game.player_images[LEFT[index]]
                
                self.steer_time -= dt
            
            # limit the steer time between 0 and the maximum image index
            self.steer_time = max(min(self.steer_time, 0.6), 0)
                
            # move forward or backwards
            if keys[pg.K_w]:
                self.moving = 1
                self.acc.x = self.speed
                self.acc.y = self.speed
            elif keys[pg.K_s]:
                self.moving = -1
                self.acc.x = self.speed * -0.4
                self.acc.y = self.speed * -0.4

            # ground tiles affect acceleration
            ground_speed = self.game.ground_speed_at(self.pos)
            #self.game.debug_values['ground_speed'] = f'{ground_speed:.1f}'
            if ground_speed == 1.0:
                # store position if ground_speed is 1 (= on road)
                self.last_road_pos.x = self.pos.x
                self.last_road_pos.y = self.pos.y
            self.acc *= ground_speed
    
            self.vel.x += self.acc.x * cos(self.angle) * dt
            self.vel.y += self.acc.y * sin(self.angle) * dt
            self.pos += self.vel * dt
            
            self.acc *= 0
            # apply friction
            self.vel *= 0.9
    
            
            # jiggle texture up and down
            JIGGLE_SPEED = 8
            if int(self.time_passed * JIGGLE_SPEED) % 2 == 0 and current_speed >= 32:
                self.rect.top = 85
            else:
                self.rect.top = 84
                
            
            # create dust clouds when steering
            self.dust_timer += dt
            if self.dust_timer >= 0.2:
                if self.lastdir == Direction.RIGHT:
                    v = vec(3, 0) * self.moving
                elif self.lastdir == Direction.LEFT:
                    v = vec(-3, 0) * self.moving
                if self.steer_time >= 0.3 and current_speed > 128:
                    if self.moving == 1:
                        p = Particle(
                            self.game, 
                            self.rect.midbottom, 
                            images=[self.game.cloud_image],
                            colors=[pg.Color('white')],
                            vel=v,
                            random_angle=30,
                            vanish_speed=20,
                            end_size=1.4
                            )
                        p.add_force(vec(0, 1), 10)
                    else:
                        p = Particle(
                            self.game, 
                            self.rect.midbottom, 
                            images=[self.game.cloud_image],
                            colors=[pg.Color('white')],
                            vel=v, 
                            random_angle=30,
                            vanish_speed=20,
                            end_size=0.9
                            )
                        p.add_force(vec(0, -2), 10)
                    
                self.dust_timer = 0


            # create dirt/grass particles when offroad
            if ground_speed < 1.0:
                # TODO check for different ground tiles
                if self.vel.length_squared() > 0.0001:
                    self.dirt_timer += dt
                if self.dirt_timer >= 0.2:
                    self.dirt_timer = 0
                    # create two particles (left and right)
                    Particle(
                        self.game, 
                        self.rect.bottomright, 
                        images=[self.game.dirt_image],
                        colors=[pg.Color('white')],
                        vel=vec(1, 0),
                        random_angle=20,
                        vanish_speed=20,
                        end_size=1.4
                        )
                    Particle(
                        self.game, 
                        self.rect.bottomleft, 
                        images=[self.game.dirt_image],
                        colors=[pg.Color('white')],
                        vel=vec(-1, 0),
                        random_angle=20,
                        vanish_speed=20,
                        end_size=1.4
                        )


        # check against the killzone
        if self.game.check_in_killzone(self.pos):
            # warp back to last known road position
            # TODO: trigger event with animation and stuff
            print("Dead")
            self.pos.x = self.last_road_pos.x
            self.pos.y = self.last_road_pos.y

        
        
    def draw(self, screen):
        screen.blit(self.image, self.rect)



class TrafficLight(pg.sprite.Sprite):
    def __init__(self, game, pos):
        super().__init__(game.all_sprites)
        self.game = game
        self.images = [game.traffic_light_images.subsurface((i * 24, 0, 24, 32)) for i in range(5)]
        self.image = self.images[0]
        self.rect = self.image.get_rect()
        self.rect.center = pos
        self.done = False
        self.timer = 0
        self.img_index = 0
        
    
    def update(self, dt):
        self.timer += dt
        if self.timer >= 1:
            self.timer = 0
            self.img_index += 1
            if self.img_index == 4:
                self.done = True
            try:
                self.image = self.images[self.img_index]
            except:
                self.kill()
        

    def draw(self, screen):
        screen.blit(self.image, self.rect)
        
        

class Billboard(pg.sprite.Sprite):
    # static world sprite from a Tiled object, image = assets/<name>.png
    base_images = {}  # name -> surface
    scaled_images = {}  # (name, width) -> surface


    def __init__(self, game, tiled_object):
        super().__init__(game.billboards)
        self.game = game
        self.name = tiled_object.name
        # ground point = center of the object rect
        self.map_pos = vec(tiled_object.x + tiled_object.width / 2,
                           tiled_object.y + tiled_object.height / 2)
        self.world_width = tiled_object.width  # size on the map, set in Tiled

        if self.name not in Billboard.base_images:
            Billboard.base_images[self.name] = pg.image.load(
                path.join(game.assets_folder, f"{self.name}.png")).convert_alpha()
        self.base_image = Billboard.base_images[self.name]
        self.image = self.base_image
        self.rect = self.image.get_rect()
        self.depth = 0
        self.visible = False


    def get_scaled_image(self, width):
        key = (self.name, width)
        if key not in Billboard.scaled_images:
            aspect = self.base_image.get_height() / self.base_image.get_width()
            height = max(1, round(width * aspect))
            Billboard.scaled_images[key] = pg.transform.scale(self.base_image, (width, height))
        return Billboard.scaled_images[key]


    def update(self, dt):
        mode7 = self.game.map
        player = self.game.player
        screen_rect = self.game.game_screen_rect
        horizon_offset = int(screen_rect.h * self.game.config["Visuals.horizon"])

        camera = player.pos - vec(mode7.kart_ground_distance(), 0).rotate_rad(player.angle)
        relative = self.map_pos - camera

        forward_dir = vec(cos(player.angle), sin(player.angle))
        right_dir = vec(-forward_dir.y, forward_dir.x)
        forward = relative.dot(forward_dir)
        lateral = relative.dot(right_dir)
        self.depth = forward

        # inverse of render_mode7: distance along frustum edge -> screen row
        frustum_dist = forward / cos(mode7.fov_half)
        if frustum_dist <= mode7.near:
            self.visible = False
            return
        depth = (mode7.far - mode7.near) / (frustum_dist - mode7.near)
        ground_y = depth * screen_rect.h + horizon_offset
        row_width = 2 * frustum_dist * sin(mode7.fov_half)  # world units across screen
        screen_x = (lateral / row_width + 0.5) * screen_rect.w
        scale = screen_rect.w / row_width

        width = max(1, int(self.world_width * scale))
        if width > screen_rect.w * 2:  # too close, also keeps the cache small
            self.visible = False
            return
        self.image = self.get_scaled_image(width)
        self.rect = self.image.get_rect(midbottom=(screen_x, ground_y))
        self.visible = self.rect.colliderect(screen_rect)


    def draw(self, screen):
        if self.visible:
            screen.blit(self.image, self.rect)


class PathFollower(Billboard):
    # billboard that steers along a closed polygon (Nature of Code path following)
    def __init__(self, game, path_points, image_name="bush", world_width=12):
        pg.sprite.Sprite.__init__(self, game.billboards)
        self.game = game
        self.name = image_name
        self.world_width = world_width
        if self.name not in Billboard.base_images:
            Billboard.base_images[self.name] = pg.image.load(
                path.join(game.assets_folder, f"{self.name}.png")).convert_alpha()
        self.base_image = Billboard.base_images[self.name]
        self.image = self.base_image
        self.rect = self.image.get_rect()
        self.depth = 0
        self.visible = False

        self.path_points = [vec(point) for point in path_points]
        self.path_radius = 8       # px, no steering while inside
        # player's terminal speed on road: v = friction * (v + speed / FPS)
        friction = 0.9
        player_top_speed = friction * game.player.speed / game.config["Video.fps"] / (1 - friction)
        speed_factor = 1.2
        self.max_speed = player_top_speed * speed_factor
        self.max_force = 5 * self.max_speed 
        self.look_ahead_time = 0.2  # s
        self.target_ahead = 40      # px along the path

        # self.map_pos = self.path_points[0].copy()
        self.map_pos = vec(1168, 689)
        start_direction = self.path_points[1] - self.path_points[0]
        self.vel = start_direction.normalize() * self.max_speed
        self.acc = vec()


    def get_normal_point(self, point, segment_start, segment_end):
        # closest point to 'point' on the segment
        segment = segment_end - segment_start
        projection = (point - segment_start).dot(segment) / segment.length_squared()
        projection = max(0.0, min(1.0, projection))
        return segment_start + segment * projection


    def follow_path(self):
        predicted_pos = self.map_pos + self.vel * self.look_ahead_time
        closest_distance = float("inf")
        target = None
        point_count = len(self.path_points)
        for i in range(point_count):
            segment_start = self.path_points[i]
            segment_end = self.path_points[(i + 1) % point_count]
            normal_point = self.get_normal_point(predicted_pos, segment_start, segment_end)
            distance = predicted_pos.distance_to(normal_point)
            if distance < closest_distance:
                closest_distance = distance
                segment_direction = (segment_end - segment_start).normalize()
                target = normal_point + segment_direction * self.target_ahead

        if closest_distance > self.path_radius:
            self.seek(target)


    def seek(self, target):
        desired = target - self.map_pos
        if desired.length_squared() == 0:
            return
        desired.scale_to_length(self.max_speed)
        steer = desired - self.vel
        if steer.length() > self.max_force:
            steer.scale_to_length(self.max_force)
        self.acc += steer


    def update(self, dt):
        if self.game.started:
            self.game.debug_values["player_speed"] = f"{self.game.player.vel.length():.0f}"
            self.game.debug_values["bush_speed"] = f"{self.vel.length():.0f}"
            self.follow_path()
            self.vel += self.acc * dt
            if self.vel.length() > self.max_speed:
                self.vel.scale_to_length(self.max_speed)
            # self.vel.scale_to_length(self.max_speed)
            self.map_pos += self.vel * dt
            self.acc *= 0
        super().update(dt)  # projection to screen