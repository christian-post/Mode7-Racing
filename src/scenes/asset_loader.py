from pathlib import Path
import pygame as pg

from src.scenes.scene import Scene


class AssetLoader(Scene):
    def __init__(self, game, **kwargs):
        super().__init__(game)

        self.folders = {
            "sprites": Path(game.assets_folder, "sprites"),
            "spritesheets": Path(game.assets_folder, "sprites", "spritesheets"),
            "fonts": Path(game.assets_folder, "fonts"),
            "backgrounds": Path(game.assets_folder, "backgrounds")
        }

        game.kart_names = []


    def load_sprites(self):
        # single image sprites
        sprite_files = self.folders["sprites"].glob("*.png")
        for file in sprite_files:
            img = pg.image.load(file).convert_alpha()
            self.game.assets["sprites"][file.stem] = img

        # cut spritesheets based on info in settings.toml
        spritesheet_files = self.folders["spritesheets"].glob("*.png")
        for file in spritesheet_files:
            key = file.stem
            n = self.game.config["Assets.num_images"].get(key)
            strip = pg.image.load(file).convert_alpha()
            frame_height = strip.get_height()  # spritesheets are just one row
            frame_width = strip.get_width() / n
            frames = [strip.subsurface(
                (i * frame_width, 0, frame_width, frame_height)
                ) for i in range(n)]
            self.game.assets["spritesheets"][key] = frames
            if "kart" in key:
                self.game.kart_names.append(key)
                frames_flipped = [
                    pg.transform.flip(frame, True, False) for frame in frames]
                self.game.assets["spritesheets"][f"{key}_flipped"] = frames_flipped


    def load_backgrounds(self):
        bg_files = self.folders["backgrounds"].glob("*.png")
        for file in bg_files:
            img = pg.image.load(file).convert_alpha()
            key = file.stem

            if key in self.game.config["Assets.bg_scale_factors"]:
                scale = self.game.config["Assets.bg_scale_factors"].get(key)
                img = pg.transform.smoothscale(img,
                        (int(img.get_width() * scale),
                         int(img.get_height() * scale)))

            self.game.assets["backgrounds"][key] = img


    def load_fonts(self):
        # TODO these are currently unused
        font_files = self.folders["fonts"].glob("*.ttf")
        font_sizes = self.game.config["Hud.font_sizes"]
        for file in font_files:
            self.game.assets["fonts"][file.stem] = {}
            for size in font_sizes:
                font = pg.font.Font(file, size)
                self.game.assets["fonts"][file.stem][size] = font


    def startup(self):
        self.load_sprites()
        self.load_backgrounds()
        self.load_fonts()

        # TODO temporary stuff (should be handled dynamically)
        self.game.background = self.game.assets["backgrounds"]["cloudy_sky"]
        self.game.mountains = self.game.assets["backgrounds"]["mountains"]

        horizon_y = int(self.game.game_screen.get_height() * self.game.config["Visuals.horizon"])
        self.game.background_y = horizon_y - self.game.background.get_height()
        self.game.mountains_y = horizon_y - self.game.mountains.get_height()

        self.game.switch_scene("TitleScreen")
        # TODO do the loading in update() to enable a loading screen