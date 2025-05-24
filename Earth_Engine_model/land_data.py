import ee, ssl, sqlite3, math, urllib.request, io
from dateutil.relativedelta import relativedelta

def create_database(db_file):
    '''
    Créée la base de donnée contenant :
    latitude, longitude, altitute, densité de végétation, état du feu (BOOL), date, température, humidité, vitesse du vent, direction du vent
    '''
    conn = None
    try:
        conn = sqlite3.connect(db_file)
        cur = conn.cursor()
        cur.execute('''CREATE TABLE Land
        (latitude FLOAT, longitude FLOAT, elevation FLOAT, treecover INT, fire BOOL, date DATE, temp FLOAT, humidity FLOAT, windspeed FLOAT, winddir FLOAT, PRIMARY KEY (latitude, longitude, date));''')
    except sqlite3.Error as e:
        print(e)
    finally:
        if conn:
            conn.close()

def image_database(db_file):
    '''
    Créée la base de donnée contenant les différentes cartes/images de la zone consernée
    '''
    conn = None
    try:
        conn = sqlite3.connect(db_file)
        cur = conn.cursor()
        cur.execute('''CREATE TABLE Images
        (region VARCHAR, date DATE, map VARBINARY, elevation VARBINARY, temperature VARBINARY, treecover VARBINARY, firms VARBINARY, PRIMARY KEY (region, date));''')
    except sqlite3.Error as e:
        print(e)
    finally:
        if conn:
            conn.close()

def clear_database(db_file, table):
    '''
    Vide une base de donnée
    '''
    conn = None
    try:
        conn = sqlite3.connect(db_file)
        cur = conn.cursor()
        cur.execute(f'''DELETE FROM {table}''')
        conn.commit()
    except sqlite3.Error as e:
        print(e)
    finally:
        if conn:
            conn.close()

class Database():
    def __init__(self, date, screen_dimensions, scale):
        self.date = date
        self.screen_dimensions = screen_dimensions
        self.scale = scale
        self.init_data = []
        self.init_images = []
        self.db_file = 'database/pythonsqlite.db'
        self.gcontext = ssl.SSLContext()
        self.locations = []
        self.get_init_data()
        self.init_datasets()

    def get_init_data(self):
        '''
        Récupère l'ensemble des informations stockées dans la base de données
        '''
        conn = None
        try:
            conn = sqlite3.connect(self.db_file)
            cur = conn.cursor()
            cur.execute('''SELECT * FROM Land WHERE date=?''',[self.date])
            response = cur.fetchall()
            desc = [x[0] for x in cur.description]
            for x in response:
                self.init_data.append(dict(zip(desc,x)))
            
            cur.execute('''SELECT * FROM Images WHERE date=?''',[self.date])
            response = cur.fetchall()
            desc = [x[0] for x in cur.description]
            for x in response:
                self.init_images.append(dict(zip(desc,x)))  

        except sqlite3.Error as e:
            print(e)
        finally:
            if conn:
                conn.close()

    def init_datasets(self):
        '''
        Initialise l'ensemble des base de données de Google Earth qui nous intéressent 
        '''
        ee.Initialize()
        i_date = (self.date - relativedelta(hours=2)).strftime('%Y-%m-%dT%H:%M')
        f_date = (self.date + relativedelta(months=1)).strftime('%Y-%m-%dT%H:%M')
        self.vegetation = ee.ImageCollection("COPERNICUS/Landcover/100m/Proba-V-C3/Global") #https://developers.google.com/earth-engine/datasets/catalog/COPERNICUS_Landcover_100m_Proba-V-C3_Global

        self.elevation = ee.Image('USGS/SRTMGL1_003')

        f_date = (self.date + relativedelta(hours=6)).strftime('%Y-%m-%dT%H:%M')
        self.atmosphere = ee.ImageCollection("NOAA/GFS0P25").filter(ee.Filter.date(i_date, f_date)) #https://developers.google.com/earth-engine/datasets/catalog/NOAA_GFS0P25#bands
        
        i_date = self.date.strftime('%Y-%m-%d')
        f_date = (self.date + relativedelta(days=2)).strftime('%Y-%m-%d')
        self.firms = ee.ImageCollection("FIRMS").filter(ee.Filter.date(i_date, f_date)) #https://developers.google.com/earth-engine/datasets/catalog/FIRMS#bands
        
        f_date = (self.date + relativedelta(days=30)).strftime('%Y-%m-%d')
        self.landsat = ee.ImageCollection("LANDSAT/LC08/C01/T1").filter(ee.Filter.date(i_date, f_date)) #.filter(ee.Filter.lt('CLOUDY_PIXEL_PERCENTAGE', 20))

        print('datasets initiated, scale :', self.scale)

    def land_data(self, coords):  
        '''
        Récupère les données relatives à une coordonnée à partir de la base de données Google Earth si la parcelle consernée à une date n'a jamais été recherché, sinon à partir de notre base de données. 
        Entrée : les coordonnées de la parcelle consernée
        '''
        init_data_locations = [(x['latitude'],x['longitude']) for x in self.init_data]
        h = {}
        if (coords['latitude'],coords['longitude']) in init_data_locations:
            i = 0
            while i < len(self.init_data) and not h:
                x = self.init_data[i]
                if (coords['latitude'],coords['longitude']) == (x['latitude'],x['longitude']):
                    h = self.init_data[i]
                i = i + 1
            return h 
        else:
            point = ee.Geometry.Point(coords['longitude'],coords['latitude'])

            firms = self.firms.first().sample(point, self.scale).first().getInfo()
            fire = (firms != None)

            vege = self.vegetation.first().sample(point, self.scale).first()

            treecover = vege.get("tree-coverfraction").getInfo()

            elev = self.elevation.sample(point, self.scale).first().get('elevation').getInfo()

            atm = self.atmosphere.first().sample(point, self.scale).first()
            temp = atm.get('temperature_2m_above_ground').getInfo()
            humidity = atm.get('relative_humidity_2m_above_ground').getInfo()
            u_ms = atm.get('u_component_of_wind_10m_above_ground').getInfo()
            v_ms = atm.get('v_component_of_wind_10m_above_ground').getInfo()

            windspeed = math.sqrt(u_ms**2 + v_ms**2)
            winddir = (180 + 180/math.pi * math.atan2(v_ms,u_ms)) % 360

            h = {'date':self.date,'latitude':coords['latitude'],'longitude':coords['longitude'],'elevation':elev, 'treecover':treecover, 'temp':temp, 'humidity':humidity, 'windspeed':windspeed, 'winddir':winddir, 'fire':fire}
            self.add_data(h)
            return h

    def add_data(self, data):
        '''
        Ajoute les données recherchées dans la base de données Google Earth à notre base de données
        Entrée : un dictionnaire de données
        '''
        conn = None
        try:
            conn = sqlite3.connect(self.db_file)
            cur = conn.cursor()
            cur.execute(f'''INSERT INTO Land (latitude, longitude, date, temp, humidity, windspeed, winddir, elevation, treecover, fire)
            VALUES (?,?,?,?,?,?,?,?,?,?)''',(data['latitude'],data['longitude'],data['date'],data['temp'],data['humidity'],data['windspeed'],data['winddir'],data['elevation'],data['treecover'],data['fire']))
            conn.commit()
        except sqlite3.Error as e:
            print(e)
        finally:
            self.init_data.append(data)
            if conn:
                conn.close()

    def load_maps(self, boundaries):
        '''
        Charge l'ensemble des cartes qui nous intéressent à partir de Google Earth ou de notre base de données.
        Entrée : listes des coordonnées de la bordure de la zone consernée
        '''
        region = ee.Geometry.Polygon(boundaries)
        b = [h for h in self.init_images if h['region'] == str(boundaries)]
        if b == []:
            elv_img = self.elevation.updateMask(self.elevation.gt(0))
            url = elv_img.getThumbURL({
                'min': 0, 'max': 700, 'region': region, 'dimensions': self.screen_dimensions,
                'palette': ['006633', 'E5FFCC', '662A00', 'D8D8D8', 'F5F5F5']})
            reponse = urllib.request.urlopen(url, context=self.gcontext)
            elv_png = io.BytesIO(reponse.read())

            temp_img = self.atmosphere.first().select('temperature_2m_above_ground')
            url = temp_img.getThumbURL({
                'min': -40.0, 'max': 35.0, 'region': region, 'dimensions': self.screen_dimensions,
                'palette': ['blue', 'purple', 'cyan', 'green', 'yellow', 'red'],
            })
            reponse = urllib.request.urlopen(url, context=self.gcontext)
            temp_png = io.BytesIO(reponse.read())

            treecover_img = self.vegetation.first().select('tree-coverfraction')         
            url = treecover_img.getThumbURL({
                'min': 0, 'max': 100, 'region': region, 'dimensions': self.screen_dimensions,
                'palette': ['black', 'brown', 'yellow', 'green'],
            })
            reponse = urllib.request.urlopen(url, context=self.gcontext)
            treecover_png = io.BytesIO(reponse.read())

            firms_img = self.firms.first().select('T21')
            url = firms_img.getThumbURL({
                'min': 325, 'max': 400, 'region': region, 'dimensions': self.screen_dimensions,
                "palette": ['red', 'orange', 'yellow'],
            })
            reponse = urllib.request.urlopen(url, context=self.gcontext)
            firms_png = io.BytesIO(reponse.read())
 
            map_img = self.landsat.mosaic()
            url = map_img.getThumbURL({
                'min':0, 'max':30000, 'bands':['B4','B3','B2'],'region': region, 'dimensions': self.screen_dimensions,
            })
            reponse = urllib.request.urlopen(url, context=self.gcontext)
            map_png = io.BytesIO(reponse.read())

            h = {'elevation':elv_png,'date':self.date,'temperature':temp_png,'treecover':treecover_png,'firms':firms_png,'map':map_png,'region':boundaries}
            self.add_images_to_database(h)
            return h
        else:
            b = b[0]
            b['elevation'] = io.BytesIO(b['elevation'])
            b['temperature'] = io.BytesIO(b['temperature'])
            b['treecover'] = io.BytesIO(b['treecover'])
            b['firms'] = io.BytesIO(b['firms'])
            b['map'] = io.BytesIO(b['map'])
            return b

    
    def add_images_to_database(self, data):
        '''
        Ajoute les cartes recherchées dans la base de données Google Earth à notre base de données
        Entrée : un dictionnaire de données
        '''
        conn = None
        try:
            conn = sqlite3.connect(self.db_file)
            cur = conn.cursor()
            cur.execute(f'''INSERT INTO Images (region, date, elevation, temperature, treecover, firms, map)
            VALUES (?,?,?,?,?,?,?)''',(str(data['region']),data['date'],data['elevation'].getvalue(),data['temperature'].getvalue(),data['treecover'].getvalue(),data['firms'].getvalue(),data['map'].getvalue()))
            conn.commit()
        except sqlite3.Error as e:
            print(e)
        finally:
            self.init_images.append(data)
            if conn:
                conn.close()