import time, math, datetime

class Parcel:
    """
    Classe définissant une parcelle de terrain
    """
    def __init__(self, position=[], parameters={}, scale=0):

        self.parameters = parameters
        self.location = {'latitude':parameters['latitude'],'longitude':parameters['longitude']}
        self.position = position
        self.neighbours = []
        self.explored = False
        self.fire = parameters['fire'] if 'fire' in parameters else None

        self.water = False
        self.combustible = True

        self.elevation = parameters['elevation'] if 'elevation' in parameters else None
        self.treecover = parameters['treecover'] #%
        self.temperature = parameters['temp'] #°C
        self.scale = scale #m
        self.m = 0.005 #précision
        
        self.humidity = parameters['humidity'] #%
        self.wind_direction = parameters['winddir'] #deg
        self.wind_speed = parameters['windspeed'] #m/s

        self.c_phi = 0 #rad
        self.t_theta = 0 #rad
        self.r_max = 1 #m/min

        self.s = 0  #état de la parcelle
        self.dt = self.m * self.scale / self.r_max #min
        self.calcul_coefs()

    def calcul_coefs(self):
        """
        calcul les différents coefficient de la parcelle par rapport à ses voisins
        W, K_phi, K_theta, K_s, R_O, R
        """
        a,b,c,d = 0.03,0.05,0.01,0.3 
        self.w = (self.wind_speed / 0.836) ** (2/3)
        self.k_phi = math.exp(0.1783*self.wind_speed*self.c_phi)
        self.k_theta = math.exp(3.553*self.t_theta)
        self.k_s = ((self.treecover + 30) / 100) ** 3
        self.r_0 = a * self.temperature + b * self.w + c * (100 - self.humidity) - d
        self.r = self.r_0 * self.k_phi * self.k_theta * self.k_s ** 2 * 0.13

    def __repr__(self):
        return f"""
        ----
        latitude : {self.location['latitude']}, 
        longitude : {self.location['longitude']}, 
        elevation : {self.elevation},
        temp : {self.temperature},
        treecover : {self.treecover},
        wind (dir, speed) : {self.wind_direction}, {self.wind_speed}
        ----
        """

    def add_neighbour(self, parcel):
        """
        Entrée : la parcelle à ajouter
        Ajoute à la parcelle "voisine" à une parcelle
        """
        if parcel not in self.neighbours:
            self.neighbours.append(parcel)

    def distance(self,A,B):
        """
        Calcul la distance entre deux point en fonction de leurs latitude et longitude.
        """
        R = 6373.0
        lat_a = math.radians(A['latitude'])
        long_a = math.radians(A['longitude'])
        lat_b = math.radians(B['latitude'])
        long_b = math.radians(B['longitude'])
        dlon = long_b - long_a
        dlat = lat_b - lat_a
        a = math.sin(dlat / 2)**2 + math.cos(lat_a) * math.cos(lat_b) * math.sin(dlon / 2)**2
        c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
        return R * c * 1000

    def fire_calcul(self):
        """
        Calcul le coefficient S d'une parcelle en fonction des parcelles voisines
        """
        
        if self.s == 0 and not self.explored:
            self.explored = True

        elif self.explored:
            u = (0,1)
            for neighbour in self.neighbours:
                if neighbour.s >= 2:
                    #dénivelé
                    d_elevation = self.elevation - neighbour.elevation
                    d = abs(self.distance(neighbour.location,self.location))
                    neighbour.t_theta = math.tan(1.2 * math.atan(d_elevation / d)) 
                    
                    #vent
                    v = (self.position[0]-neighbour.position[0], self.position[1]-neighbour.position[1])
                    angle_v = math.acos((u[0]*v[0] + u[1]*v[1])/((v[0]**2+v[1]**2)**0.5))
                    if v[0] == 1:
                        angle_v = -angle_v
                    neighbour.c_phi = math.cos(math.radians(neighbour.wind_direction - 180) - angle_v)
                    neighbour.calcul_coefs()

            neighbours_r = [neighbour.r for neighbour in self.neighbours]
            if self.s == 1:
                self.s = 2
            elif self.s == 2:
                if all([True if not neighbour.combustible or neighbour.s >= 2 else False for neighbour in self.neighbours]):
                    self.s = 3
            elif self.s == 3: 
                self.s = 4 
            else:
                if self.s < 1:
                    a = (sum(neighbours_r) * self.dt) / self.scale
                    x = self.s + a 
                    self.s = x if x < 1 else 1

class Map:
    """
    Classe définissant le terrain au complet
    Elle est composé de plusieurs parcelles de terrain
    """
    def __init__(self, parent):
        self.parent = parent
        self.database = parent.database

    def generate_map(self,map_parameters):
        """
        Génére la carte dans les dimensions souhaiter à partir de parcelles de terrains
        Entrée : les dimensions de la carte
        """
        dimensions = map_parameters['dimensions']
        boundaries = map_parameters['boundaries']
        scale = map_parameters['scale'] #dimension d'une parcelle
        delta_scale = map_parameters['delta_scale']

        t = time.time()
        print('load data...')
        self.map = []
        for x in range(dimensions[0]):
            row = []
            for y in range(dimensions[1]):
                lat = round(boundaries['north'] - y * delta_scale['latitude'], 6)
                long = round(boundaries['west'] + x * delta_scale['longitude'], 6)
                h = self.database.land_data({'latitude':lat,'longitude':long})
                row.append(Parcel(position=(x,y),parameters=h,scale=scale))
            self.map.append(row)
        
        for x in range(dimensions[0]):
            for y in range(dimensions[1]):
                parcel = self.map[x][y]
                for i in range(x-1,x+2):
                    for j in range(y-1,y+2):
                        if 0 <= i < dimensions[0] and 0 <= j < dimensions[1] and (x,y) != (i,j):
                            parcel.add_neighbour(self.map[i][j])
        
        print(f'Loading time : {time.time() - t}')

    def fire(self, position):
        """
        Met en feu la carte
        Entrée : la position du feu au départ, la nombre d'iterations de la simulation*
        """
        def spread_it(queue, iteration=1800):
            i = 0
            dt = queue[0].dt
            while (queue != [] and iteration <= 0) or (queue != [] and i < iteration and iteration > 0):
                next_queue = []
                for parcel in queue:
                    parcel.fire_calcul()
                    if parcel.s == 2:
                        for neighbour in parcel.neighbours:
                            if not neighbour in next_queue and neighbour.combustible:
                                next_queue.append(neighbour)
                        if not parcel in next_queue:
                            next_queue.append(parcel)
                    elif parcel.s == 3:
                        if not parcel in next_queue:
                            next_queue.append(parcel)

                queue = next_queue.copy()
                self.parent.update_map()
                self.parent.window.flip()
                self.parent.actual_time += datetime.timedelta(minutes=dt)
                i = i + 1
                time.sleep(10**-3)
            return i

        x,y = position            
        origin = self.map[x][y]
        origin.explored = True
        origin.s = 2
        queue = origin.neighbours + [origin]
        return spread_it(queue)