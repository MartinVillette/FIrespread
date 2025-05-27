"""
Tree Coverage-Based Forest Fire Propagation Model

This module implements a forest fire simulation based on tree coverage density
and vegetation distribution. Fire spreads according to the tree density in each
area, creating realistic propagation patterns that follow vegetation gradients.

The model uses:
- Tree coverage maps generated from random terrain data
- Propagation coefficient based on vegetation density
- 8-directional neighbor connectivity for fire spread
- Iterative fire intensity calculation with threshold-based propagation

Educational Purpose:
Demonstrates how vegetation density affects wildfire spread patterns and
the importance of fuel load distribution in fire management planning.

@author Martin
@created 2022
@version 1.0.0
"""

import random

class Parcel:
    """
    Represents a single terrain cell in the forest fire simulation.
    
    Each parcel contains information about its vegetation density, current fire
    state, and connectivity to neighboring cells for fire propagation calculations.
    """
    
    def __init__(self, position=[]):
        """
        Initialize a terrain parcel with default properties.
        
        Args:
            position (list): Grid coordinates [x, y] of this parcel
        """
        self.position = position        # Grid coordinates (x, y)
        self.fire = 0                  # Fire intensity: 0=none, 0-1=burning, 1=burned
        self.neighbours = []           # Connected adjacent parcels
        self.k_s = 0                  # Fire spread coefficient (vegetation-dependent)
        self.ground = 0               # Vegetation density: 0=forest, 1=bare ground

    def __repr__(self):
        """String representation showing position and fire state."""
        return str(self.position) + ' ' + str(self.fire)

    def add_neighbour(self, parcel):
        """
        Add bidirectional connection to an adjacent parcel.
        
        Creates the neighbor network needed for fire propagation
        calculations across the terrain grid.
        
        Args:
            parcel (Parcel): Adjacent terrain cell to connect
        """
        if parcel not in self.neighbours:
            self.neighbours.append(parcel)

    def fire_calcul(self):
        """
        Calculate next fire intensity based on neighboring fire states.
        
        Uses weighted average of neighbor fire intensities, where weights
        are determined by each neighbor's vegetation density (k_s coefficient).
        
        Returns:
            float: New fire intensity (capped at 1.0 for fully burned)
        """
        # Sum fire contributions from all neighbors weighted by their vegetation
        neighbor_fire_influence = 0
        for neighbour in self.neighbours:
            neighbor_fire_influence += neighbour.fire * neighbour.k_s
        
        # Average the influence across all neighbors
        average_influence = neighbor_fire_influence / len(self.neighbours)
        
        # Update fire intensity (cumulative effect)
        new_fire_intensity = self.fire + average_influence
        
        # Cap at maximum burn level
        return new_fire_intensity if new_fire_intensity < 1 else 1

class Map:
    """
    Complete terrain representation for forest fire simulation.
    
    Manages the full landscape including vegetation distribution, terrain
    generation, and fire propagation dynamics across the entire area.
    """
    
    def __init__(self, map_dimensions, parent):
        """
        Initialize the terrain map with specified dimensions.
        
        Args:
            map_dimensions (tuple): Grid size (width, height) in cells
            parent: Reference to display interface for visualization updates
        """
        self.parent = parent  # Reference to visualization system
        self.generate_map(map_dimensions)

    def generate_map(self, dimensions):
        """
        Generate terrain with realistic vegetation distribution patterns.
        
        Creates a two-level terrain system:
        1. Coarse-grained tree coverage map (10x10 cell regions)
        2. Fine-grained parcel grid with interpolated vegetation values
        
        Args:
            dimensions (tuple): Map dimensions (width, height) in parcels
        """
        # Generate base tree coverage map at 1/10th resolution
        # Values 1-100 represent tree density percentage in each region
        coarse_width = int(dimensions[0] / 10)
        coarse_height = int(dimensions[1] / 10)
        self.ground_map = [[random.randint(1, 100) for j in range(coarse_height)] 
                          for i in range(coarse_width)]
        
        # Create detailed parcel grid
        self.map = [[Parcel(position=(x, y)) for y in range(dimensions[1])] 
                   for x in range(dimensions[0])]
        
        # Configure each parcel based on regional tree coverage
        for x in range(dimensions[0]):
            for y in range(dimensions[1]):
                parcel = self.map[x][y]
                
                # Map parcel to corresponding coarse grid region
                region_x, region_y = x // 10, y // 10
                tree_coverage = self.ground_map[region_x][region_y]
                
                # Calculate fire spread coefficient based on vegetation density
                # Higher tree coverage = higher fire spread potential
                # Formula: cubic scaling for realistic fire behavior
                parcel.k_s = (((tree_coverage + 30) / 100) ** 3)
                parcel.ground = tree_coverage / 100  # Normalize for display
                
                # Establish 8-directional connectivity (Moore neighborhood)
                for i in range(x - 1, x + 2):
                    for j in range(y - 1, y + 2):
                        # Check bounds and exclude self-connection
                        if (0 <= i < dimensions[0] and 0 <= j < dimensions[1] and 
                            (x, y) != (i, j)):
                            parcel.add_neighbour(self.map[i][j])

    def fire(self, position, iterations=0):
        """
        Execute fire propagation simulation from specified ignition point.
        
        Implements iterative fire spread using a queue-based algorithm where
        fire intensity is calculated for each parcel based on its neighbors,
        and new parcels are added to the active fire front when they ignite.
        
        Args:
            position (tuple): Ignition coordinates (x, y)
            iterations (int): Maximum iterations (0 = run until completion)
            
        Returns:
            int: Total number of simulation iterations executed
        """
        def spread_iteration(active_queue, max_iterations):
            """
            Execute one complete fire spread iteration across all active parcels.
            
            Args:
                active_queue (list): Parcels currently burning or at risk
                max_iterations (int): Iteration limit (0 = unlimited)
                
            Returns:
                int: Number of iterations completed
            """
            iteration_count = 0
            next_active_queue = []
            fire_updates = {}  # Store calculated fire values before applying
            
            # Continue until fire stops spreading or iteration limit reached
            while ((active_queue != [] and max_iterations <= 0) or 
                   (active_queue != [] and iteration_count < max_iterations and max_iterations > 0)):
                
                next_active_queue = []
                
                # Calculate new fire intensities for all active parcels
                for parcel in active_queue:
                    new_fire_intensity = parcel.fire_calcul()
                    fire_updates[parcel] = new_fire_intensity
                    
                    # If parcel is actively burning, check neighbors for spread
                    if 10**-4 < new_fire_intensity < 1:  # Active fire threshold
                        for neighbour in parcel.neighbours:
                            # Add unburned neighbors with sufficient vegetation to queue
                            if (0 <= neighbour.fire < 1 and 
                                neighbour not in next_active_queue and 
                                neighbour.ground > 0.1):  # Minimum vegetation for fire spread
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
        
        # Execute fire propagation simulation
        return spread_iteration(initial_queue, iterations)