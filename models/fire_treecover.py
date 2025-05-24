import random

class Parcel:
    """
    Classe définissant une parcelle de terrain
    Elle admet :
    - une position relative : (x,y)
    - un coefficient de feu : 0 < f < 1 (1 : la parcelle est en feu)
    - un coefficient de terrain
    """
    def __init__(self, position=[]):
        self.position = position
        self.fire = 0
        self.neighbours = []
        self.k_s = 0
        self.ground = 0 #0 c'est normal : forêt / 1 c'est sol, se propage pas

    def __repr__(self):
        return str(self.position) + ' ' + str(self.fire)

    def add_neighbour(self, parcel):
        """
        Entrée : la parcelle à ajouter
        Ajoute à la parcelle "voisine" à une parcelle
        """
        if parcel not in self.neighbours:
            self.neighbours.append(parcel)

    def fire_calcul(self):
        n_fire = 0
        for neighbour in self.neighbours:
            n_fire += neighbour.fire * neighbour.k_s
        n_fire = n_fire / len(self.neighbours)
        fire = self.fire + n_fire
        return fire if fire < 1 else 1

class Map:
    """
    Classe définissant le terrain au complet
    Elle est composé de plusieurs parcelles de terrain
    Elle admet :
    - des dimensions : (x,y)
    """
    def __init__(self, map_dimensions, parent):
        self.parent = parent
        self.generate_map(map_dimensions)

    def generate_map(self,dimensions):
        """
        Entrée : les dimensions de la carte
        Génére la carte dans les dimensions souhaiter à partir de parcelles de terrains
        """
        self.ground_map = [[random.randint(1,100) for i in range(int(dimensions[1]/10))] for x in range(int(dimensions[0]/10))]
        self.map = [[Parcel(position=(x,y)) for y in range(dimensions[1])] for x in range(dimensions[0])]
        for x in range(dimensions[0]):
            for y in range(dimensions[1]):
                parcel = self.map[x][y]
                treecover = random.randint(0,100)
                i,j = x//10,y//10
                treecover = self.ground_map[i][j]
                parcel.k_s = (((treecover + 30) / 100) ** 3)
                parcel.ground = treecover / 100

                #propagation en carré (8voisins)
                for i in range(x-1,x+2):
                    for j in range(y-1,y+2):
                        if 0 <= i < dimensions[0] and 0 <= j < dimensions[1] and (x,y) != (i,j):
                            parcel.add_neighbour(self.map[i][j])

    def fire(self, position, iterations=0):
        def spread_it(queue, iteration):
            i = 0
            next_queue = []
            d = {}
            while (queue != [] and iteration <= 0) or (queue != [] and i < iteration and iteration > 0):
                next_queue = []
                for parcel in queue:
                    f = parcel.fire_calcul()
                    d[parcel] = f
                    if 10**-4 < f < 1:
                        for neighbour in parcel.neighbours:
                            if (0 <= neighbour.fire < 1) and not neighbour in next_queue and neighbour.ground > 0.1:
                                next_queue.append(neighbour)
                        if not parcel in next_queue:
                            next_queue.append(parcel)

                queue = next_queue.copy()

                for parcel in d:
                    parcel.fire = d[parcel]

                self.parent.update_map()
                self.parent.window.flip()
                i = i + 1
            return i

        x,y = position              #on récupère l'origine du feu
        origin = self.map[x][y]     #définit l'origine du feu
        origin.fire = 0.1             #met en feu la parcelle de départ
        queue = origin.neighbours            #la liste des parcelles à examiner
        return spread_it(queue, iterations)