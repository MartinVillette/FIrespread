import pygame as py
import fire, land_data
import time, sys, math
from datetime import datetime

class Screen:
    def __init__(self, window, p=0.5):
        self.window = window
        self.p = p
        self.modification_possible = False
        
        self.backgrounds_dict = {}
        self.backgrounds = ['map','elevation','temperature','treecover','firms']
        self.i_background = 0

        self.screen_dimensions = (600,600)
        self.map_dimensions = (15,15)

        ## Var  
        self.fire_origin = (3,5)
        self.date = datetime(2021,8,16,17)
        self.boundaries = {
            'north':43.404227,
            'east':6.580468,
            'south':43.185331,
            'west':6.251565
        }
        
        a = self.boundaries['east'],self.boundaries['north']
        b = self.boundaries['west'],self.boundaries['north']
        c = self.boundaries['west'],self.boundaries['south']
        d = self.boundaries['east'],self.boundaries['south']
        self.region = [a,b,c,d,a]

        self.actual_time = self.date
        self.scale = self.distance(self.boundaries['north'],self.boundaries['south']) / self.map_dimensions[1]
        self.delta_scale = {
            'longitude':round((self.boundaries['east'] - self.boundaries['west'] )/ self.map_dimensions[0], 6),
            'latitude':round((self.boundaries['north'] - self.boundaries['south'] )/ self.map_dimensions[1], 6)
            }
        self.fire_visibility = False
        self.map_parameters = {'dimensions':self.map_dimensions, 'scale':self.scale, 'delta_scale':self.delta_scale, 'date':self.date, 'screen_dimensions':self.screen_dimensions, 'boundaries':self.boundaries, 'region':self.region}
        self.screen = self.window.set_mode(self.screen_dimensions)
        self.database = land_data.Database(self.map_parameters['date'],self.map_parameters['screen_dimensions'],self.map_parameters['scale'])
        self.load_map()

    def distance(self,A,B):
        '''
        Retourne la distance en m entre la latitude de deux points de l'espace
        Entrée : la latitude de deux points
        '''
        R = 6373.0
        lat_a = math.radians(A)
        lat_b = math.radians(B)
        dlon = 0
        dlat = abs(lat_b - lat_a)
        a = math.sin(dlat / 2)**2 + math.cos(lat_a) * math.cos(lat_b) * math.sin(dlon / 2)**2
        c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
        return R * c * 1000

    def load_map(self):
        '''
        Importe les différentes images de la zone concernée
        '''
        print('LOAD')
        self.map = fire.Map(self) 

        print('loading the maps...')
        
        png = self.database.load_maps(self.region)

        for key in self.backgrounds:
            self.backgrounds_dict[key] = py.image.load(png[key])
            py.image.save(self.backgrounds_dict[key], f"images\{key}.jpg")
        
        self.screen.blit(self.backgrounds_dict[self.backgrounds[self.i_background]], (0,0))
        self.window.flip()
        print('... loaded')

    def toggle_fire_filter(self):
        '''
        Affiche/Cache le filtre comparant le résultat obtenu avec le feu réel
        '''
        if self.modification_possible:
            self.fire_visibility = not(self.fire_visibility)
            self.update_map()
            self.window.flip()
        
    def update_map(self):
        '''
        Actualise tous les éléments présents à l'écran
        '''
        width,height = [self.screen_dimensions[i]//self.map_dimensions[i] for i in range(2)]
        background = self.backgrounds_dict[self.backgrounds[self.i_background]]
        if background:
            self.screen.blit(background,(0,0))
        else:
            self.screen.fill((0,200,0))
        for x in range(self.map_dimensions[0]):
            for y in range(self.map_dimensions[1]):
                pos = (x * width, y * height)
                surf = py.Surface((width, height),py.SRCALPHA)
                parcel = self.map.map[x][y]
                color = (0,0,0,100)
                if parcel.water:
                    surf.fill((0,0,255,150))
                elif parcel.position == self.fire_origin and parcel.s == 0:
                    surf.fill((255,255,255,200))
                elif self.fire_visibility and self.modification_possible:
                    if parcel.s == 4:
                        if parcel.fire:
                            surf.fill((0,200,0,200))
                        else:
                            surf.fill((200,0,0,100))
                    elif parcel.fire:
                        surf.fill((100,100,0,200))

                else:
                    if parcel.s == 1:
                        surf.fill((255,150,0,70))
                    elif parcel.s == 2:
                        surf.fill((255,0,0,150))
                    elif parcel.s == 3:
                        surf.fill((255,0,0,190))
                    elif parcel.s == 4:
                        surf.fill((0,0,0,125))

                py.draw.rect(surf, color, surf.get_rect(), 1)
                self.screen.blit(surf,(pos[0],pos[1]))
        font = py.font.SysFont('Arial', 40,'white')
        text_img = font.render(str(self.actual_time.strftime('%Y/%m/%d, %Hh%M')), True, (255,255,255))
        text_img = font.render('2021/08/25, 18h06', True, (255,255,255))
        self.screen.blit(text_img, (50,self.screen_dimensions[1]-70))

    def reset(self):
        '''
        Remet toutes les valeurs de la simulation à 0
        '''
        print('RESET')
        self.modification_possible = True
        self.actual_time = self.date
        self.map = fire.Map(self)
        self.map.generate_map(self.map_parameters)
        self.update_map()
        self.window.flip()

    def set_fire(self):
        '''
        Départ de la simulation
        '''
        if self.modification_possible:
            t = time.time()
            print('-' * 15)
            print('FIRE...')
            self.modification_possible = False
            iterations = self.map.fire(self.fire_origin)
            self.modification_possible = True
            self.update_map()
            self.window.flip()
            print(f"END, nombre d'iterations : {iterations} (running time : {round(time.time()-t,2)})",)
            print('-' * 15)


    def click(self):
        '''
        Retourne les informations de la parcelle sur laquelle on a appuyé sur l'écran
        '''
        if self.modification_possible:
            pos = py.mouse.get_pos()
            width,height = [self.screen_dimensions[i]//self.map_dimensions[i] for i in range(2)]
            i,j = pos[0] // width, pos[1] // height
            print(self.map.map[i][j])
            time.sleep(.1)

    def toggle_background(self):
        '''
        Change le fond d'écrans entre les différentes cartes chargées
        '''
        self.i_background = (self.i_background + 1) % len(self.backgrounds)
        if self.backgrounds[self.i_background] == 'firms':
                self.screen.blit(self.backgrounds_dict['map'],(0,0))
        if self.modification_possible:
            self.update_map()
        else:
            self.screen.blit(self.backgrounds_dict[self.backgrounds[self.i_background]], (0,0))
        self.window.flip()

py.init()
screen = Screen(py.display, 0.3)

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
            if event.key == py.K_t:
                screen.toggle_fire_filter()
            if event.key == py.K_u:
                screen.toggle_background()

    if py.mouse.get_pressed():
        p = py.mouse.get_pressed()
        if p == (1,0,0) or p == (0,0,1):
            screen.click(p)