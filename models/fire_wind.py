"""
Wind-Based Forest Fire Propagation Model

This module implements a forest fire simulation that incorporates wind effects
on fire spread patterns. The model calculates fire propagation based on wind
speed, wind direction, and the geometric relationship between terrain parcels.

The model uses:
- Wind speed and direction parameters for realistic fire behavior
- Directional fire spread coefficients based on wind vectors
- Exponential propagation models accounting for wind acceleration
- 8-directional neighbor connectivity with wind-influenced spread rates

Educational Purpose:
Demonstrates how meteorological conditions, particularly wind patterns,
dramatically affect wildfire behavior and spread dynamics in fire management scenarios.

@author Martin
@created 2022
@version 1.0.0
"""

import math

class Parcel:
    """
    Represents a single terrain cell with wind-influenced fire propagation.
    
    Each parcel calculates its fire spread potential based on wind direction,
    wind speed, and geometric relationships with neighboring cells. Wind effects
    are modeled using directional coefficients and exponential propagation rates.
    """
    
    def __init__(self, position=[], wind=50):
        """
        Initialize a terrain parcel with wind parameters.
        
        Args:
            position (list): Grid coordinates [x, y] of this parcel
            wind (float): Wind speed in km/h (default 50 km/h)
        """
        self.position = position        # Grid coordinates (x, y)
        self.fire = 0                  # Fire intensity: 0=none, 0-1=burning, 1=burned
        self.neighbours = []           # Connected adjacent parcels
        self.ground = 0               # Terrain type (unused in wind model)
        self.wind = (0, -1)           # Wind vector (default: northward)
        
        # Wind-specific parameters
        self.c_phi = 0                # Directional wind coefficient (-1 to 1)
        self.wind_direction = 0       # Wind direction in degrees from south
        self.wind_speed = wind        # Wind speed in m/s
        self.wind_speed /= 3.6        # Convert km/h to m/s
        self.k_phi = 0               # Calculated fire spread coefficient

    def __repr__(self):
        """String representation showing position and fire state."""
        return str(self.position) + ' ' + str(self.fire)

    def add_neighbour(self, parcel):
        """
        Add bidirectional connection to an adjacent parcel.
        
        Creates the neighbor network needed for wind-influenced fire
        propagation calculations across the terrain grid.
        
        Args:
            parcel (Parcel): Adjacent terrain cell to connect
        """
        if parcel not in self.neighbours:
            self.neighbours.append(parcel)

    def calcul_coefs(self):
        """
        Calculate wind-influenced fire spread coefficient.
        
        Uses an exponential model where fire spread rate increases
        exponentially with wind speed and directional alignment.
        Formula based on empirical wildfire research.
        """
        # Exponential wind effect model: k_phi = e^(0.1783 * wind_speed * c_phi * 1.5)
        # Higher positive c_phi (downwind) increases spread rate dramatically
        self.k_phi = math.exp(0.1783 * self.wind_speed * self.c_phi * 1.5)

    def fire_calcul(self):
        """
        Calculate next fire intensity based on wind-influenced neighbor contributions.
        
        For each neighbor, calculates:
        1. Geometric angle between wind direction and neighbor position
        2. Directional coefficient (c_phi) based on wind alignment
        3. Wind-influenced fire spread rate (k_phi)
        4. Weighted fire contribution to this parcel
        
        Returns:
            float: New fire intensity (capped at 1.0 for fully burned)
        """
        neighbor_fire_contribution = 0
        north_vector = (0, 1)  # Reference vector pointing north
        
        # Calculate wind-influenced fire contribution from each neighbor
        for neighbour in self.neighbours:
            # Vector from neighbor to current parcel (fire spread direction)
            direction_vector = (self.position[0] - neighbour.position[0], 
                              self.position[1] - neighbour.position[1])
            
            # Calculate angle between north and fire spread direction
            vector_magnitude = (direction_vector[0]**2 + direction_vector[1]**2)**0.5
            angle_to_north = math.acos((north_vector[0] * direction_vector[0] + 
                                      north_vector[1] * direction_vector[1]) / vector_magnitude)
            
            # Adjust angle sign based on east/west orientation
            if direction_vector[0] == 1:
                angle_to_north = -angle_to_north
            
            # Calculate directional wind coefficient
            # c_phi = cos(wind_direction - 180° - angle_to_north)
            # Positive when fire spreads downwind, negative when upwind
            neighbour.c_phi = math.cos(math.radians(neighbour.wind_direction - 180) - angle_to_north)
            
            # Calculate wind-influenced spread coefficient
            neighbour.calcul_coefs()
            
            # Add weighted fire contribution (square root dampening for stability)
            neighbor_fire_contribution += neighbour.fire * (neighbour.k_phi ** 0.5)
        
        # Average contributions across all neighbors
        average_contribution = neighbor_fire_contribution / len(self.neighbours)
        
        # Calculate new fire intensity with wind speed dampening
        # Higher wind speeds reduce local fire intensity but increase spread rate
        new_fire_intensity = self.fire + (average_contribution / (1 + self.wind_speed))
        
        # Cap at maximum burn level
        return new_fire_intensity if new_fire_intensity < 1 else 1

class Map:
    """
    Complete terrain representation for wind-influenced forest fire simulation.
    
    Manages the full landscape with uniform wind conditions across all parcels
    and coordinates fire propagation dynamics throughout the simulation area.
    """
    
    def __init__(self, map_dimensions, parent, wind=50):
        """
        Initialize the wind-based fire simulation terrain.
        
        Args:
            map_dimensions (tuple): Grid size (width, height) in cells
            parent: Reference to display interface for visualization updates
            wind (float): Uniform wind speed across terrain in km/h
        """
        self.parent = parent  # Reference to visualization system
        self.wind = wind     # Global wind speed parameter
        self.generate_map(map_dimensions)

    def generate_map(self, dimensions):
        """
        Generate uniform terrain grid with wind parameters.
        
        Creates a homogeneous landscape where all parcels share the same
        wind conditions, focusing the simulation on wind effects rather
        than terrain variation.
        
        Args:
            dimensions (tuple): Map dimensions (width, height) in parcels
        """
        # Create grid of parcels with uniform wind conditions
        self.map = [[Parcel(position=(x, y), wind=self.wind) 
                    for y in range(dimensions[1])] 
                   for x in range(dimensions[0])]
        
        # Establish 8-directional connectivity for each parcel
        for x in range(dimensions[0]):
            for y in range(dimensions[1]):
                parcel = self.map[x][y]
                
                # Connect to all adjacent cells (Moore neighborhood)
                for i in range(x - 1, x + 2):
                    for j in range(y - 1, y + 2):
                        # Check bounds and exclude self-connection
                        if (0 <= i < dimensions[0] and 0 <= j < dimensions[1] and 
                            (x, y) != (i, j)):
                            parcel.add_neighbour(self.map[i][j])

    def fire(self, position, iterations=300):
        """
        Execute wind-influenced fire propagation simulation.
        
        Runs the fire spread algorithm with wind effects, typically requiring
        fewer iterations than vegetation-based models due to wind acceleration.
        
        Args:
            position (tuple): Ignition coordinates (x, y)
            iterations (int): Maximum iterations (300 default for wind model)
            
        Returns:
            int: Total number of simulation iterations executed
        """
        def spread_iteration(active_queue, max_iterations):
            """
            Execute iterative fire spread with wind influence.
            
            Args:
                active_queue (list): Parcels currently burning or at risk
                max_iterations (int): Iteration limit (0 = unlimited)
                
            Returns:
                int: Number of iterations completed
            """
            iteration_count = 0
            fire_updates = {}  # Store calculated fire values before applying
            
            # Continue until fire stops spreading or iteration limit reached
            while ((active_queue != [] and max_iterations <= 0) or 
                   (active_queue != [] and iteration_count < max_iterations and max_iterations > 0)):
                
                next_active_queue = []
                
                # Calculate wind-influenced fire intensities for all active parcels
                for parcel in active_queue:
                    new_fire_intensity = parcel.fire_calcul()
                    fire_updates[parcel] = new_fire_intensity
                    
                    # If parcel is actively burning, check neighbors for spread
                    if 10**-4 < new_fire_intensity < 1:  # Active fire threshold
                        for neighbour in parcel.neighbours:
                            # Add unburned neighbors to next iteration queue
                            if (0 <= neighbour.fire < 1 and 
                                neighbour not in next_active_queue):
                                next_active_queue.append(neighbour)
                        
                        # Keep current parcel active if still burning
                        if parcel not in next_active_queue:
                            next_active_queue.append(parcel)

                # Update to next iteration's active parcels
                active_queue = next_active_queue.copy()

                # Apply all calculated fire intensity updates simultaneously
                for parcel in fire_updates:
                    parcel.fire = fire_updates[parcel]

                # Update visualization display
                self.parent.update_map()
                self.parent.window.flip()
                
                iteration_count += 1
                
            return iteration_count

        # Initialize fire at specified origin point
        x, y = position
        origin_parcel = self.map[x][y]
        origin_parcel.fire = 0.1  # Set initial fire intensity
        
        # Start with neighbors of ignition point as initial fire front
        initial_queue = origin_parcel.neighbours
        
        # Execute wind-influenced fire propagation simulation
        return spread_iteration(initial_queue, iterations)