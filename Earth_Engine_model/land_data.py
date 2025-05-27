"""
Google Earth Engine Data Interface for Forest Fire Simulation

This module provides a comprehensive interface to Google Earth Engine databases
for retrieving real-world environmental data used in forest fire simulations.
It manages satellite imagery, weather data, elevation models, and fire detection
information with local caching for performance optimization.

Data Sources Integrated:
- COPERNICUS Landcover: Global vegetation coverage data
- USGS SRTM: High-resolution elevation models
- NOAA GFS: Real-time weather and atmospheric conditions
- NASA FIRMS: Active fire detection from satellite sensors
- Landsat 8: High-resolution satellite imagery

Features:
- Local SQLite database caching for performance
- Automatic data retrieval and storage management
- Multi-layer satellite imagery generation
- Real-time weather data integration
- Fire detection validation data

@author Martin
@created 2022
@version 1.0.0
"""

import ee, ssl, sqlite3, math, urllib.request, io
from dateutil.relativedelta import relativedelta

def create_database(db_file):
    """
    Create SQLite database for environmental data caching.
    
    Creates a table to store comprehensive environmental data for each
    geographic coordinate and date, enabling fast local data retrieval
    without repeated Google Earth Engine API calls.
    
    Schema includes:
    - Geographic coordinates (latitude, longitude)
    - Topographic data (elevation)
    - Vegetation information (tree cover percentage)
    - Fire detection status (boolean from NASA FIRMS)
    - Temporal information (date)
    - Weather conditions (temperature, humidity, wind speed/direction)
    
    Args:
        db_file (str): Path to SQLite database file
    """
    conn = None
    try:
        conn = sqlite3.connect(db_file)
        cur = conn.cursor()
        cur.execute('''CREATE TABLE Land
        (latitude FLOAT, longitude FLOAT, elevation FLOAT, treecover INT, 
         fire BOOL, date DATE, temp FLOAT, humidity FLOAT, 
         windspeed FLOAT, winddir FLOAT, 
         PRIMARY KEY (latitude, longitude, date));''')
        print(f"Environmental data database created: {db_file}")
    except sqlite3.Error as e:
        print(f"Database creation error: {e}")
    finally:
        if conn:
            conn.close()

def image_database(db_file):
    """
    Create SQLite database for satellite imagery caching.
    
    Creates a table to store processed satellite images for different
    data layers (elevation, temperature, vegetation, fire detection)
    as binary data for fast local retrieval.
    
    Args:
        db_file (str): Path to SQLite database file
    """
    conn = None
    try:
        conn = sqlite3.connect(db_file)
        cur = conn.cursor()
        cur.execute('''CREATE TABLE Images
        (region VARCHAR, date DATE, map VARBINARY, elevation VARBINARY, 
         temperature VARBINARY, treecover VARBINARY, firms VARBINARY, 
         PRIMARY KEY (region, date));''')
        print(f"Satellite imagery database created: {db_file}")
    except sqlite3.Error as e:
        print(f"Image database creation error: {e}")
    finally:
        if conn:
            conn.close()

def clear_database(db_file, table):
    """
    Clear all data from specified database table.
    
    Utility function for database maintenance and testing.
    Removes all records from the specified table.
    
    Args:
        db_file (str): Path to SQLite database file
        table (str): Name of table to clear
    """
    conn = None
    try:
        conn = sqlite3.connect(db_file)
        cur = conn.cursor()
        cur.execute(f'''DELETE FROM {table}''')
        conn.commit()
        print(f"Database table '{table}' cleared successfully")
    except sqlite3.Error as e:
        print(f"Database clearing error: {e}")
    finally:
        if conn:
            conn.close()

class Database():
    """
    Main interface to Google Earth Engine environmental data services.
    
    Manages data retrieval from multiple satellite and weather databases,
    implements local caching for performance, and provides processed
    environmental data for fire simulation models.
    """
    
    def __init__(self, date, screen_dimensions, scale):
        """
        Initialize the Earth Engine data interface.
        
        Sets up connections to Google Earth Engine, initializes local
        caching database, and configures data retrieval parameters.
        
        Args:
            date (datetime): Simulation date for temporal data queries
            screen_dimensions (tuple): Display resolution for image generation
            scale (float): Spatial resolution in meters per pixel
        """
        self.date = date                        # Simulation temporal context
        self.screen_dimensions = screen_dimensions  # Image output resolution
        self.scale = scale                      # Spatial scale in meters
        
        # Local data storage
        self.init_data = []                     # Cached environmental data
        self.init_images = []                   # Cached satellite imagery
        self.db_file = 'database/pythonsqlite.db'  # Local database path
        
        # Network configuration for secure data retrieval
        self.gcontext = ssl.SSLContext()
        self.locations = []                     # Processed coordinate list
        
        # Initialize data systems
        self.get_init_data()    # Load existing cached data
        self.init_datasets()    # Configure Earth Engine datasets

    def get_init_data(self):
        """
        Load previously cached environmental data from local database.
        
        Retrieves all environmental data and satellite imagery that has
        been previously downloaded for the simulation date, enabling
        fast local access without repeated API calls.
        """
        conn = None
        try:
            conn = sqlite3.connect(self.db_file)
            cur = conn.cursor()
            
            # Load environmental data for simulation date
            cur.execute('''SELECT * FROM Land WHERE date=?''', [self.date])
            response = cur.fetchall()
            desc = [x[0] for x in cur.description]
            for x in response:
                self.init_data.append(dict(zip(desc, x)))
            
            # Load cached satellite imagery for simulation date
            cur.execute('''SELECT * FROM Images WHERE date=?''', [self.date])
            response = cur.fetchall()
            desc = [x[0] for x in cur.description]
            for x in response:
                self.init_images.append(dict(zip(desc, x)))
                
            print(f"Loaded {len(self.init_data)} cached environmental records")
            print(f"Loaded {len(self.init_images)} cached image sets")

        except sqlite3.Error as e:
            print(f"Data loading error: {e}")
        finally:
            if conn:
                conn.close()

    def init_datasets(self):
        """
        Initialize Google Earth Engine dataset connections.
        
        Configures access to multiple satellite and weather data sources
        with appropriate temporal filtering for the simulation date.
        Each dataset provides specific environmental information:
        
        - Vegetation: Tree coverage and land use classification
        - Elevation: High-resolution topographic data
        - Atmosphere: Real-time weather conditions
        - FIRMS: Active fire detection from satellite sensors
        - Landsat: High-resolution optical satellite imagery
        """
        # Initialize Google Earth Engine API
        ee.Initialize()
        
        # Calculate temporal windows for different data types
        i_date = (self.date - relativedelta(hours=2)).strftime('%Y-%m-%dT%H:%M')
        f_date = (self.date + relativedelta(months=1)).strftime('%Y-%m-%dT%H:%M')
        
        # Global vegetation coverage data (100m resolution)
        # Source: COPERNICUS Landcover dataset
        self.vegetation = ee.ImageCollection("COPERNICUS/Landcover/100m/Proba-V-C3/Global")
        
        # High-resolution elevation data (30m resolution)
        # Source: USGS Shuttle Radar Topography Mission
        self.elevation = ee.Image('USGS/SRTMGL1_003')
        
        # Real-time atmospheric conditions (6-hour forecast window)
        # Source: NOAA Global Forecast System
        f_date = (self.date + relativedelta(hours=6)).strftime('%Y-%m-%dT%H:%M')
        self.atmosphere = ee.ImageCollection("NOAA/GFS0P25").filter(ee.Filter.date(i_date, f_date))
        
        # Active fire detection data (2-day window)
        # Source: NASA Fire Information for Resource Management System
        i_date = self.date.strftime('%Y-%m-%d')
        f_date = (self.date + relativedelta(days=2)).strftime('%Y-%m-%d')
        self.firms = ee.ImageCollection("FIRMS").filter(ee.Filter.date(i_date, f_date))
        
        # High-resolution satellite imagery (30-day window for cloud-free images)
        # Source: Landsat 8 Collection 1 Tier 1
        f_date = (self.date + relativedelta(days=30)).strftime('%Y-%m-%d')
        self.landsat = ee.ImageCollection("LANDSAT/LC08/C01/T1").filter(ee.Filter.date(i_date, f_date))
        
        print(f'Earth Engine datasets initialized, spatial scale: {self.scale}m')

    def land_data(self, coords):  
        """
        Retrieve comprehensive environmental data for specific coordinates.
        
        First checks local cache for existing data, then queries Google Earth Engine
        if needed. Returns complete environmental profile including topography,
        vegetation, weather, and fire detection status.
        
        Args:
            coords (dict): Geographic coordinates with 'latitude' and 'longitude' keys
            
        Returns:
            dict: Complete environmental data profile containing:
                - date: Temporal context
                - latitude, longitude: Geographic position
                - elevation: Height above sea level (meters)
                - treecover: Vegetation coverage percentage (0-100)
                - temp: Temperature at 2m above ground (Celsius)
                - humidity: Relative humidity percentage (0-100)
                - windspeed: Wind speed magnitude (m/s)
                - winddir: Wind direction (degrees from north)
                - fire: Fire detection status (boolean)
        """
        # Check if data exists in local cache
        init_data_locations = [(x['latitude'], x['longitude']) for x in self.init_data]
        coord_key = (coords['latitude'], coords['longitude'])
        
        if coord_key in init_data_locations:
            # Return cached data
            for cached_data in self.init_data:
                if coord_key == (cached_data['latitude'], cached_data['longitude']):
                    return cached_data
        else:
            # Query Google Earth Engine for new data
            point = ee.Geometry.Point(coords['longitude'], coords['latitude'])

            # Fire detection from NASA FIRMS
            try:
                firms_sample = self.firms.first().sample(point, self.scale).first().getInfo()
                fire = (firms_sample is not None)
            except:
                fire = False  # No fire detected or data unavailable

            # Vegetation data from COPERNICUS
            vegetation_sample = self.vegetation.first().sample(point, self.scale).first()
            treecover = vegetation_sample.get("tree-coverfraction").getInfo()

            # Elevation from USGS SRTM
            elevation = self.elevation.sample(point, self.scale).first().get('elevation').getInfo()

            # Atmospheric conditions from NOAA GFS
            atmosphere_sample = self.atmosphere.first().sample(point, self.scale).first()
            temperature = atmosphere_sample.get('temperature_2m_above_ground').getInfo()
            humidity = atmosphere_sample.get('relative_humidity_2m_above_ground').getInfo()
            
            # Wind components (u = east-west, v = north-south)
            u_component = atmosphere_sample.get('u_component_of_wind_10m_above_ground').getInfo()
            v_component = atmosphere_sample.get('v_component_of_wind_10m_above_ground').getInfo()

            # Calculate wind speed and direction from components
            windspeed = math.sqrt(u_component**2 + v_component**2)
            winddir = (180 + 180/math.pi * math.atan2(v_component, u_component)) % 360

            # Compile complete environmental profile
            environmental_data = {
                'date': self.date,
                'latitude': coords['latitude'],
                'longitude': coords['longitude'],
                'elevation': elevation,
                'treecover': treecover,
                'temp': temperature,
                'humidity': humidity,
                'windspeed': windspeed,
                'winddir': winddir,
                'fire': fire
            }
            
            # Cache data locally for future use
            self.add_data(environmental_data)
            return environmental_data

    def add_data(self, data):
        """
        Add newly retrieved environmental data to local cache database.
        
        Stores complete environmental data profile in SQLite database
        for fast future retrieval without repeated API calls.
        
        Args:
            data (dict): Environmental data dictionary to cache
        """
        conn = None
        try:
            conn = sqlite3.connect(self.db_file)
            cur = conn.cursor()
            cur.execute(f'''INSERT INTO Land (latitude, longitude, date, temp, humidity, 
                           windspeed, winddir, elevation, treecover, fire)
                           VALUES (?,?,?,?,?,?,?,?,?,?)''',
                       (data['latitude'], data['longitude'], data['date'], data['temp'],
                        data['humidity'], data['windspeed'], data['winddir'],
                        data['elevation'], data['treecover'], data['fire']))
            conn.commit()
        except sqlite3.Error as e:
            print(f"Data insertion error: {e}")
        finally:
            # Update local cache
            self.init_data.append(data)
            if conn:
                conn.close()

    def load_maps(self, boundaries):
        """
        Generate satellite imagery maps for visualization layers.
        
        Creates multiple thematic maps from different data sources:
        - Elevation: Topographic visualization
        - Temperature: Thermal conditions
        - Tree Cover: Vegetation density
        - FIRMS: Fire detection overlay
        - Landsat: True-color satellite imagery
        
        Args:
            boundaries (list): Polygon coordinates defining the region of interest
            
        Returns:
            dict: Collection of satellite imagery layers as BytesIO objects
        """
        region = ee.Geometry.Polygon(boundaries)
        
        # Check for cached imagery
        cached_images = [img for img in self.init_images if img['region'] == str(boundaries)]
        
        if not cached_images:
            print("Generating satellite imagery from Earth Engine...")
            
            # Elevation map with terrain visualization
            elevation_image = self.elevation.updateMask(self.elevation.gt(0))
            elevation_url = elevation_image.getThumbURL({
                'min': 0, 'max': 700, 'region': region, 'dimensions': self.screen_dimensions,
                'palette': ['006633', 'E5FFCC', '662A00', 'D8D8D8', 'F5F5F5']
            })
            elevation_response = urllib.request.urlopen(elevation_url, context=self.gcontext)
            elevation_png = io.BytesIO(elevation_response.read())

            # Temperature map with thermal color scale
            temperature_image = self.atmosphere.first().select('temperature_2m_above_ground')
            temperature_url = temperature_image.getThumbURL({
                'min': -40.0, 'max': 35.0, 'region': region, 'dimensions': self.screen_dimensions,
                'palette': ['blue', 'purple', 'cyan', 'green', 'yellow', 'red'],
            })
            temperature_response = urllib.request.urlopen(temperature_url, context=self.gcontext)
            temperature_png = io.BytesIO(temperature_response.read())

            # Tree coverage map with vegetation color scale
            treecover_image = self.vegetation.first().select('tree-coverfraction')         
            treecover_url = treecover_image.getThumbURL({
                'min': 0, 'max': 100, 'region': region, 'dimensions': self.screen_dimensions,
                'palette': ['black', 'brown', 'yellow', 'green'],
            })
            treecover_response = urllib.request.urlopen(treecover_url, context=self.gcontext)
            treecover_png = io.BytesIO(treecover_response.read())

            # Fire detection map with heat visualization
            firms_image = self.firms.first().select('T21')
            firms_url = firms_image.getThumbURL({
                'min': 325, 'max': 400, 'region': region, 'dimensions': self.screen_dimensions,
                "palette": ['red', 'orange', 'yellow'],
            })
            firms_response = urllib.request.urlopen(firms_url, context=self.gcontext)
            firms_png = io.BytesIO(firms_response.read())
 
            # True-color satellite imagery from Landsat
            satellite_image = self.landsat.mosaic()
            satellite_url = satellite_image.getThumbURL({
                'min': 0, 'max': 30000, 'bands': ['B4', 'B3', 'B2'],
                'region': region, 'dimensions': self.screen_dimensions,
            })
            satellite_response = urllib.request.urlopen(satellite_url, context=self.gcontext)
            satellite_png = io.BytesIO(satellite_response.read())

            # Compile imagery collection
            imagery_data = {
                'elevation': elevation_png,
                'date': self.date,
                'temperature': temperature_png,
                'treecover': treecover_png,
                'firms': firms_png,
                'map': satellite_png,
                'region': boundaries
            }
            
            # Cache imagery for future use
            self.add_images_to_database(imagery_data)
            return imagery_data
        else:
            # Return cached imagery
            cached_data = cached_images[0]
            cached_data['elevation'] = io.BytesIO(cached_data['elevation'])
            cached_data['temperature'] = io.BytesIO(cached_data['temperature'])
            cached_data['treecover'] = io.BytesIO(cached_data['treecover'])
            cached_data['firms'] = io.BytesIO(cached_data['firms'])
            cached_data['map'] = io.BytesIO(cached_data['map'])
            print("Using cached satellite imagery")
            return cached_data

    def add_images_to_database(self, data):
        """
        Store generated satellite imagery in local cache database.
        
        Saves processed satellite images as binary data in SQLite database
        for fast future retrieval without Earth Engine API calls.
        
        Args:
            data (dict): Imagery data collection with binary image data
        """
        conn = None
        try:
            conn = sqlite3.connect(self.db_file)
            cur = conn.cursor()
            cur.execute(f'''INSERT INTO Images (region, date, elevation, temperature, 
                           treecover, firms, map)
                           VALUES (?,?,?,?,?,?,?)''',
                       (str(data['region']), data['date'],
                        data['elevation'].getvalue(), data['temperature'].getvalue(),
                        data['treecover'].getvalue(), data['firms'].getvalue(),
                        data['map'].getvalue()))
            conn.commit()
            print("Satellite imagery cached successfully")
        except sqlite3.Error as e:
            print(f"Image caching error: {e}")
        finally:
            # Update local cache
            self.init_images.append(data)
            if conn:
                conn.close()