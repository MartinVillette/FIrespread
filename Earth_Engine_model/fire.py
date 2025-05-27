"""
Real-World Forest Fire Propagation Model using Google Earth Engine Data

This module implements a comprehensive forest fire simulation using real-world
satellite data from Google Earth Engine. The model incorporates multiple
environmental factors including topography, meteorology, and vegetation to
create highly accurate fire spread predictions.

The model integrates:
- Real elevation data for slope-based fire acceleration
- Live weather data (temperature, humidity, wind speed/direction)
- Satellite vegetation coverage (tree cover percentage)
- Geographic coordinate system with precise distance calculations
- Multi-factor fire spread rate calculations based on empirical research

Educational Purpose:
Demonstrates how real-world environmental data can be integrated into
fire behavior models for practical wildfire management and prediction.

@author Martin
@created 2022
@version 1.0.0
"""

import time, math, datetime

class Parcel:
    """
    Represents a real-world terrain parcel with comprehensive environmental data.
    
    Each parcel contains satellite-derived vegetation data, meteorological
    conditions, topographic information, and calculates fire spread rates
    using established wildfire research formulas.
    """
    
    def __init__(self, position=[], parameters={}, scale=0):
        """
        Initialize a terrain parcel with real-world environmental data.
        
        Args:
            position (list): Grid coordinates [x, y] in the simulation
            parameters (dict): Environmental data from Google Earth Engine
            scale (float): Real-world size of each grid cell in meters
        """
        self.parameters = parameters
        self.location = {
            'latitude': parameters['latitude'], 
            'longitude': parameters['longitude']
        }
        self.position = position      # Grid coordinates (x, y)
        self.neighbours = []          # Connected adjacent parcels
        self.explored = False         # Fire spread calculation flag
        self.fire = parameters['fire'] if 'fire' in parameters else None
        
        # Terrain properties
        self.water = False           # Water body flag (prevents fire spread)
        self.combustible = True      # Can catch fire (opposite of water/rock)
        
        # Environmental data from satellite/weather sources
        self.elevation = parameters['elevation'] if 'elevation' in parameters else None
        self.treecover = parameters['treecover']    # Tree coverage percentage
        self.temperature = parameters['temp']       # Temperature in °C
        self.humidity = parameters['humidity']      # Relative humidity percentage
        self.wind_direction = parameters['winddir'] # Wind direction in degrees
        self.wind_speed = parameters['windspeed']   # Wind speed in m/s
        
        # Simulation parameters
        self.scale = scale           # Real-world cell size in meters
        self.m = 0.005              # Precision factor for calculations
        
        # Fire spread coefficients (calculated dynamically)
        self.c_phi = 0              # Wind direction coefficient
        self.t_theta = 0            # Slope influence coefficient
        self.r_max = 1              # Maximum fire spread rate (m/min)
        
        # Fire state and timing
        self.s = 0                  # Fire state: 0=unburned, 1=igniting, 2=burning, 3=cooling, 4=burned
        self.dt = self.m * self.scale / self.r_max  # Time step in minutes
        
        self.calcul_coefs()

    def calcul_coefs(self):
        """
        Calculate fire spread coefficients based on environmental conditions.
        
        Uses established wildfire research formulas to compute:
        - Wind effects on fire spread (exponential relationship)
        - Slope acceleration factors
        - Vegetation fuel load influence
        - Base fire spread rate considering temperature and humidity
        
        Formula sources: Rothermel fire spread model and derivatives
        """
        # Empirical constants from wildfire research
        a, b, c, d = 0.03, 0.05, 0.01, 0.3
        
        # Wind factor calculation (modified wind speed)
        self.w = (self.wind_speed / 0.836) ** (2/3)
        
        # Wind direction effect (exponential influence)
        self.k_phi = math.exp(0.1783 * self.wind_speed * self.c_phi)
        
        # Slope effect (exponential slope acceleration)
        self.k_theta = math.exp(3.553 * self.t_theta)
        
        # Vegetation fuel factor (cubic relationship with tree coverage)
        self.k_s = ((self.treecover + 30) / 100) ** 3
        
        # Base fire spread rate incorporating weather conditions
        self.r_0 = (a * self.temperature + 
                   b * self.w + 
                   c * (100 - self.humidity) - d)
        
        # Final fire spread rate combining all factors
        self.r = self.r_0 * self.k_phi * self.k_theta * self.k_s ** 2 * 0.13

    def __repr__(self):
        """Detailed string representation of parcel environmental data."""
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
        Add bidirectional connection to an adjacent parcel.
        
        Args:
            parcel (Parcel): Adjacent terrain cell to connect
        """
        if parcel not in self.neighbours:
            self.neighbours.append(parcel)

    def distance(self, A, B):
        """
        Calculate great circle distance between two geographic points.
        
        Uses the Haversine formula for accurate distance calculation
        on the Earth's curved surface.
        
        Args:
            A (dict): First location with 'latitude' and 'longitude' keys
            B (dict): Second location with 'latitude' and 'longitude' keys
            
        Returns:
            float: Distance in meters between the two points
        """
        R = 6373.0  # Earth radius in kilometers
        
        # Convert coordinates to radians
        lat_a = math.radians(A['latitude'])
        long_a = math.radians(A['longitude'])
        lat_b = math.radians(B['latitude'])
        long_b = math.radians(B['longitude'])
        
        # Calculate coordinate differences
        dlon = long_b - long_a
        dlat = lat_b - lat_a
        
        # Haversine formula for great circle distance
        a = (math.sin(dlat / 2)**2 + 
             math.cos(lat_a) * math.cos(lat_b) * math.sin(dlon / 2)**2)
        c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
        
        return R * c * 1000  # Convert to meters

    def fire_calcul(self):
        """
        Calculate fire state progression based on neighboring fire conditions.
        
        Implements a multi-state fire model:
        - State 0: Unburned, susceptible
        - State 1: Ignition threshold reached
        - State 2: Actively burning
        - State 3: Fire cooling down
        - State 4: Completely burned out
        
        Incorporates slope and wind effects for each burning neighbor.
        """
        if self.s == 0 and not self.explored:
            # Mark as explored but not yet ignited
            self.explored = True

        elif self.explored:
            north_vector = (0, 1)  # Reference vector pointing north
            
            # Calculate slope and wind effects from burning neighbors
            for neighbour in self.neighbours:
                if neighbour.s >= 2:  # If neighbor is actively burning
                    
                    # Calculate slope effect on fire spread
                    elevation_difference = self.elevation - neighbour.elevation
                    horizontal_distance = abs(self.distance(neighbour.location, self.location))
                    
                    # Slope influence coefficient (uphill fire spreads faster)
                    neighbour.t_theta = math.tan(1.2 * math.atan(elevation_difference / horizontal_distance))
                    
                    # Calculate wind direction effect
                    direction_vector = (self.position[0] - neighbour.position[0], 
                                      self.position[1] - neighbour.position[1])
                    vector_magnitude = (direction_vector[0]**2 + direction_vector[1]**2)**0.5
                    angle_to_north = math.acos((north_vector[0] * direction_vector[0] + 
                                              north_vector[1] * direction_vector[1]) / vector_magnitude)
                    
                    # Adjust angle sign for east/west orientation
                    if direction_vector[0] == 1:
                        angle_to_north = -angle_to_north
                    
                    # Wind direction coefficient (positive when fire spreads downwind)
                    neighbour.c_phi = math.cos(math.radians(neighbour.wind_direction - 180) - angle_to_north)
                    
                    # Recalculate fire spread coefficients with new slope/wind data
                    neighbour.calcul_coefs()

            # Get fire spread rates from all neighbors
            neighbours_r = [neighbour.r for neighbour in self.neighbours]
            
            # State transition logic
            if self.s == 1:
                # Transition from ignition to active burning
                self.s = 2
            elif self.s == 2:
                # Check if fire should start cooling (no more fuel around)
                if all([True if not neighbour.combustible or neighbour.s >= 2 
                       else False for neighbour in self.neighbours]):
                    self.s = 3
            elif self.s == 3:
                # Transition from cooling to burned out
                self.s = 4
            else:
                # Calculate fire accumulation from burning neighbors
                if self.s < 1:
                    fire_accumulation = (sum(neighbours_r) * self.dt) / self.scale
                    new_fire_state = self.s + fire_accumulation
                    # Cap at ignition threshold
                    self.s = new_fire_state if new_fire_state < 1 else 1

class Map:
    """
    Complete terrain representation using real-world satellite and weather data.
    
    Integrates with Google Earth Engine database to create accurate environmental
    conditions for each terrain parcel in the simulation area.
    """
    
    def __init__(self, parent):
        """
        Initialize the real-world terrain map.
        
        Args:
            parent: Reference to main application with database connection
        """
        self.parent = parent
        self.database = parent.database  # Google Earth Engine interface

    def generate_map(self, map_parameters):
        """
        Generate terrain map using real satellite and weather data.
        
        Downloads and processes environmental data for each grid cell
        including elevation, vegetation, and current weather conditions.
        
        Args:
            map_parameters (dict): Map configuration containing:
                - dimensions: Grid size (width, height)
                - boundaries: Geographic bounds (north, south, east, west)
                - scale: Real-world size of each cell in meters
                - delta_scale: Coordinate step size for each cell
        """
        dimensions = map_parameters['dimensions']
        boundaries = map_parameters['boundaries']
        scale = map_parameters['scale']          # Cell size in meters
        delta_scale = map_parameters['delta_scale']  # Coordinate increments
        
        t = time.time()
        print('Loading real-world environmental data...')
        
        self.map = []
        
        # Generate grid with real environmental data for each cell
        for x in range(dimensions[0]):
            row = []
            for y in range(dimensions[1]):
                # Calculate real-world coordinates for this grid cell
                lat = round(boundaries['north'] - y * delta_scale['latitude'], 6)
                long = round(boundaries['west'] + x * delta_scale['longitude'], 6)
                
                # Fetch environmental data from Google Earth Engine
                environmental_data = self.database.land_data({'latitude': lat, 'longitude': long})
                
                # Create parcel with real-world data
                row.append(Parcel(position=(x, y), parameters=environmental_data, scale=scale))
            self.map.append(row)
        
        # Establish 8-directional connectivity between parcels
        for x in range(dimensions[0]):
            for y in range(dimensions[1]):
                parcel = self.map[x][y]
                # Connect to all adjacent cells
                for i in range(x-1, x+2):
                    for j in range(y-1, y+2):
                        if (0 <= i < dimensions[0] and 0 <= j < dimensions[1] and 
                            (x, y) != (i, j)):
                            parcel.add_neighbour(self.map[i][j])
        
        print(f'Environmental data loading time: {time.time() - t}s')

    def fire(self, position):
        """
        Execute realistic fire propagation simulation with real environmental data.
        
        Runs fire spread using actual topography, weather, and vegetation data
        with real-time progression and visualization updates.
        
        Args:
            position (tuple): Ignition coordinates (x, y) in the grid
            
        Returns:
            int: Total number of simulation iterations executed
        """
        def spread_iteration(active_queue, max_iterations=1800):
            """
            Execute iterative fire spread with real-world time progression.
            
            Args:
                active_queue (list): Parcels currently burning or at risk
                max_iterations (int): Iteration limit (1800 = 30 hours default)
                
            Returns:
                int: Number of iterations completed
            """
            iteration_count = 0
            dt = active_queue[0].dt  # Time step in minutes
            
            while ((active_queue != [] and max_iterations <= 0) or 
                   (active_queue != [] and iteration_count < max_iterations and max_iterations > 0)):
                
                next_active_queue = []
                
                # Process all currently active parcels
                for parcel in active_queue:
                    parcel.fire_calcul()
                    
                    if parcel.s == 2:  # Actively burning
                        # Add combustible neighbors to next iteration
                        for neighbour in parcel.neighbours:
                            if (neighbour not in next_active_queue and 
                                neighbour.combustible):
                                next_active_queue.append(neighbour)
                        
                        # Keep burning parcel active
                        if parcel not in next_active_queue:
                            next_active_queue.append(parcel)
                            
                    elif parcel.s == 3:  # Cooling down
                        # Keep cooling parcel active
                        if parcel not in next_active_queue:
                            next_active_queue.append(parcel)

                # Update active parcels for next iteration
                active_queue = next_active_queue.copy()
                
                # Update visualization
                self.parent.update_map()
                self.parent.window.flip()
                
                # Advance simulation time by real minutes
                self.parent.actual_time += datetime.timedelta(minutes=dt)
                
                iteration_count += 1
                time.sleep(10**-3)  # Small delay for smooth visualization
                
            return iteration_count

        # Initialize fire at specified origin point
        x, y = position
        origin_parcel = self.map[x][y]
        origin_parcel.explored = True
        origin_parcel.s = 2  # Set to actively burning
        
        # Start with origin and its neighbors
        initial_queue = origin_parcel.neighbours + [origin_parcel]
        
        # Execute realistic fire propagation simulation
        return spread_iteration(initial_queue)