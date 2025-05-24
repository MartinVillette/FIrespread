import pygame as py
import fire_treecover, fire_wind
import time, sys

class Screen:
    def __init__(self, window):
        self.window = window
        self.modification_possible = True

        self.screen_dimensions = (500,500)
        self.map_dimensions = (100,100)
        self.fire_origin = (51,51)
        self.mod = 1

        self.screen = self.window.set_mode(self.screen_dimensions)
        self.screen.fill((133,255,52))
        
        self.reset()

    def update_map(self):
        width,height = [self.screen_dimensions[i]//self.map_dimensions[i] for i in range(2)]
        for x in range(self.map_dimensions[0]):
            for y in range(self.map_dimensions[1]):
                pos = (x * width, y * height)
                rect = py.Rect(pos[0],pos[1], width, height)
                parcel = self.map.map[x][y]
                if parcel.position == self.fire_origin:
                    color = (255,255,255)
                elif 0 < parcel.fire < 1:
                    yellow = 255 * (1-parcel.fire ** 0.5)
                    color = (225, yellow, 0)
                elif parcel.fire == 1:
                    color = (34,34,34)
                elif parcel.fire == -1:
                    color = (0,0,255)
                else:
                    if parcel.ground == 0:
                        r,g,b = 133,255,52
                    elif 0.1 < parcel.ground:
                        c = parcel.ground
                        r,g,b = 0, 255*c, 0
                    else:
                        c = parcel.ground
                        r,g,b = 150*(1-parcel.ground), 60*(1-parcel.ground), 30*(1-parcel.ground)
                    color = (r,g,b)
                py.draw.rect(self.screen, color ,rect)
        time.sleep(0.01)

    def reset(self):
        print('RESET')
        self.modification_possible = True
        if self.mod == 1:
            self.map = fire_wind.Map(self.map_dimensions, self)
        elif self.mod == 2:
            self.map = fire_treecover.Map(self.map_dimensions, self)
        self.update_map()
        self.window.flip()

    def set_fire(self):
        t = time.time()
        print('-' * 15)
        print('FIRE...')
        self.modification_possible = False
        iterations = self.map.fire(self.fire_origin)
        self.window.flip()
        print(f"END, nombre d'iterations : {iterations} (running time : {round(time.time()-t,2)})",)
        print('-' * 15)

    def switch_mod(self, mod):
        if self.mod != mod:
            print(f'swith from {self.mod} to {mod}')
            self.mod = mod
            self.reset()

py.init()
screen = Screen(py.display)

while True:
    for event in py.event.get():
        if event.type == py.QUIT:
            sys.exit()
        if event.type == py.KEYDOWN:
            if event.key == py.K_f:
                screen.set_fire()
            if event.key == py.K_RETURN:
                sys.exit()
            if event.key == py.K_r:
                screen.reset()
            if event.key == py.K_1:
                screen.switch_mod(1)
            if event.key == py.K_2:
                screen.switch_mod(2)