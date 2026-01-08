import pygame as pg
from math import sin, cos, pi

from src.particle import Particle

vec = pg.math.Vector2


# ENUMS correspond to kart image index
LEFT = [5, 4, 3, 2, 1, 0]
RIGHT = [5, 6, 7, 8, 9, 10]


class Player(pg.sprite.Sprite):
    def __init__(self, game):
        super().__init__(game.all_sprites)
        self.game = game
        self.pos = vec(999.904, 1000.38)
        self.angle = -1.54
        self.acc = vec()
        self.vel = vec()
        self.speed = 0.5
        
        self.image = game.player_images[LEFT[0]]
        self.rect = self.image.get_rect()
        self.rect.topleft = (84, 84)
        
        self.time_passed = 0 # seconds from the start of the game
        self.steer_time = 0 # seconds the player is pressing a direction
        self.lastdir = 'LEFT'
        self.moving = 1 # 1 forward, -1 backwards
        self.dust_timer = 0
        
    
    def update(self, dt):
        self.time_passed += dt

        keys = pg.key.get_pressed()
        
        if not self.game.started:
            if keys[pg.K_w]:
                self.dust_timer += dt
                if self.dust_timer >= 0.3:
                    # create two particles (left and right)
                    Particle(self.game, self.rect.bottomright, 
                             images=[self.game.cloud_image],
                             colors=[pg.Color('white')],
                             vel=vec(1, 0),
                             random_angle=20,
                             vanish_speed=20,
                             end_size=1.4)
                    Particle(self.game, self.rect.bottomleft, 
                             images=[self.game.cloud_image],
                             colors=[pg.Color('white')],
                             vel=vec(-1, 0),
                             random_angle=20,
                             vanish_speed=20,
                             end_size=1.4)
                    self.dust_timer = 0
            
        else:
            if self.moving == 1:
                turn_force = 20 # how much the angle changes when turning
            else:
                turn_force = 50
            steer_anim_speed = 10 # turning animation speed
            
            current_speed = self.vel.length()
            
            # steer
            # cap the image index at 4 (len of animation minus 2)
            index = min(4, int(self.steer_time * steer_anim_speed))
            
            if keys[pg.K_a]:
                # turning left
                if self.lastdir == 'RIGHT':
                    self.steer_time = 0
                # increase the steering time
                self.steer_time += dt
                self.angle -= turn_force * dt * current_speed * self.moving
                # add 1 to the index to get the first turning sprite and set the image
                if self.moving == 1:
                    self.image = self.game.player_images[LEFT[index + 1]]
                else:
                    self.image = self.game.player_images[RIGHT[index + 1]]
                self.lastdir = 'LEFT'
            elif keys[pg.K_d]:
                # turning right
                if self.lastdir == 'LEFT':
                    self.steer_time = 0
                self.steer_time += dt
                self.angle += turn_force * dt * current_speed * self.moving
                if self.moving == 1:
                    self.image = self.game.player_images[RIGHT[index + 1]]
                else:
                    self.image = self.game.player_images[LEFT[index + 1]]
                self.lastdir = 'RIGHT'
            else:
                if self.lastdir == 'LEFT' and self.moving == 1:
                    self.image = self.game.player_images[LEFT[index]]
                elif self.lastdir == 'LEFT' and self.moving == -1:
                    self.image = self.game.player_images[RIGHT[index]]
                elif self.lastdir == 'RIGHT' and self.moving == 1:
                    self.image = self.game.player_images[RIGHT[index]]
                elif self.lastdir == 'RIGHT' and self.moving == -1:
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
    
            self.vel.x += self.acc.x * cos(self.angle) * dt
            self.vel.y += self.acc.y * sin(self.angle) * dt
            self.pos += self.vel * dt
            
            self.acc *= 0
            self.vel *= 0.9
    
            
            # move image up and down
            if int(self.time_passed * 5) % 2 == 0 and current_speed >= 0.01:
                self.rect.top = 85
            else:
                self.rect.top = 84
                
            
            # create dust clouds
            self.dust_timer += dt
            if self.dust_timer >= 0.2:
                if self.lastdir == 'RIGHT':
                    v = vec(3, 0) * self.moving
                elif self.lastdir == 'LEFT':
                    v = vec(-3, 0) * self.moving
                if self.steer_time >= 0.3 and current_speed > 0.04:
                    if self.moving == 1:
                        p = Particle(self.game, self.rect.midbottom, 
                                     images=[self.game.cloud_image],
                                     colors=[pg.Color('white')],
                                     vel=v, random_angle=30,
                                     vanish_speed=20,
                                     end_size=1.4)
                        p.add_force(vec(0, 1), 10)
                    else:
                        p = Particle(self.game, self.rect.midbottom, 
                                     images=[self.game.cloud_image],
                                     colors=[pg.Color('white')],
                                     vel=v, random_angle=30,
                                     vanish_speed=20,
                                     end_size=0.9)
                        p.add_force(vec(0, -2), 10)
                    
                self.dust_timer = 0
        
        
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
        
        

class Bush(pg.sprite.Sprite):
    # TODO: work in progress
    def __init__(self, game, map_pos):
        super().__init__(game.all_sprites)
        self.game = game
        self.image = game.bush_image
        self.rect = self.image.get_rect()
        # position on the map
        self.map_pos = map_pos
        
        
    def update(self, dt):
        # calculate screen position and size based on relative position
        # on game map to the player
        dist_vec = self.map_pos - self.game.player.pos
        distance = dist_vec.length()