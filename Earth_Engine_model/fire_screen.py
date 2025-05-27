"""
Real-World Forest Fire Simulation Interface - Google Earth Engine Integration

This module provides the main visualization and interaction interface for a forest fire
simulation system using real-world satellite and weather data from Google Earth Engine.
The interface displays multiple data layers including elevation, temperature, vegetation,
and actual fire detection data for model validation.

Features:
- Multi-layer satellite imagery display (map, elevation, temperature, tree cover)
- Real-time fire spread visualization with temporal progression
- Fire detection validation using NASA FIRMS data
- Interactive terrain exploration and parcel inspection
- Performance timing and accuracy metrics
- Real geographic coordinates and scale

Educational Purpose:
Demonstrates integration of real-world environmental data sources for accurate
wildfire behavior modeling and prediction validation.

@author Martin
@created 2022
@version 1.0.0
"""

import pygame as py
import fire, land_data
import time, sys, math
from datetime import datetime

class Screen:
    """
    Main visualization interface for real-world forest fire simulation.
    
    Manages satellite imagery display, user interaction, and simulation execution
    using actual environmental data from Google Earth Engine and NASA fire detection.
    """
    
    def __init__(self, window, p=0.5):
        """
        Initialize the real-world fire simulation interface.
        
        Sets up the geographic region (French Riviera), loads satellite data,
        and prepares the visualization system for fire simulation.
        
        Args:
            window: Pygame display object for rendering
            p (float): Probability parameter for terrain generation (0.5 default)
        """
        self.window = window
        self.p = p  # Terrain generation probability
        self.modification_possible = False  # Simulation state control
        
        # Satellite imagery layers configuration
        self.backgrounds_dict = {}  # Storage for loaded satellite images
        self.backgrounds = ['map', 'elevation', 'temperature', 'treecover', 'firms']
        self.i_background = 0  # Current background layer index
        
        # Display configuration
        self.screen_dimensions = (600, 600)  # Window size in pixels
        self.map_dimensions = (15, 15)      # Grid resolution (15x15 cells)
        
        # Simulation parameters
        self.fire_origin = (3, 5)           # Default ignition point
        self.date = datetime(2021, 8, 16, 17)  # Simulation start date/time
        
        # Geographic boundaries (French Riviera region)
        self.boundaries = {
            'north': 43.404227,   # Northern latitude boundary
            'east': 6.580468,     # Eastern longitude boundary  
            'south': 43.185331,   # Southern latitude boundary
            'west': 6.251565      # Western longitude boundary
        }
        
        # Create region polygon for Earth Engine queries
        a = self.boundaries['east'], self.boundaries['north']
        b = self.boundaries['west'], self.boundaries['north']
        c = self.boundaries['west'], self.boundaries['south']
        d = self.boundaries['east'], self.boundaries['south']
        self.region = [a, b, c, d, a]  # Closed polygon
        
        # Calculate real-world scale parameters
        self.actual_time = self.date
        self.scale = self.distance(self.boundaries['north'], self.boundaries['south']) / self.map_dimensions[1]
        self.delta_scale = {
            'longitude': round((self.boundaries['east'] - self.boundaries['west']) / self.map_dimensions[0], 6),
            'latitude': round((self.boundaries['north'] - self.boundaries['south']) / self.map_dimensions[1], 6)
        }
        
        # Visualization state
        self.fire_visibility = False  # Toggle for fire detection overlay
        
        # Compile map parameters for data loading
        self.map_parameters = {
            'dimensions': self.map_dimensions,
            'scale': self.scale,
            'delta_scale': self.delta_scale,
            'date': self.date,
            'screen_dimensions': self.screen_dimensions,
            'boundaries': self.boundaries,
            'region': self.region
        }
        
        # Initialize display and data systems
        self.screen = self.window.set_mode(self.screen_dimensions)
        self.database = land_data.Database(
            self.map_parameters['date'],
            self.map_parameters['screen_dimensions'],
            self.map_parameters['scale']
        )
        
        self.load_map()

    def distance(self, A, B):
        """
        Calculate great circle distance between two latitude points.
        
        Uses simplified Haversine formula for latitudinal distance calculation
        (assumes longitude difference is zero for this specific use case).
        
        Args:
            A (float): First latitude in decimal degrees
            B (float): Second latitude in decimal degrees
            
        Returns:
            float: Distance in meters between the two latitudes
        """
        R = 6373.0  # Earth radius in kilometers
        
        # Convert to radians
        lat_a = math.radians(A)
        lat_b = math.radians(B)
        
        # Calculate latitudinal difference (longitude difference = 0)
        dlon = 0
        dlat = abs(lat_b - lat_a)
        
        # Haversine formula
        a = (math.sin(dlat / 2)**2 + 
             math.cos(lat_a) * math.cos(lat_b) * math.sin(dlon / 2)**2)
        c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
        
        return R * c * 1000  # Convert to meters

    def load_map(self):
        """
        Load terrain data and satellite imagery for the simulation region.
        
        Downloads environmental data from Google Earth Engine and NASA FIRMS,
        processes satellite imagery for display, and initializes the fire
        propagation model with real-world data.
        """
        print('LOAD')
        
        # Initialize fire propagation model with real environmental data
        self.map = fire.Map(self)
        
        print('Loading satellite imagery and environmental data...')
        
        # Download satellite images for all background layers
        png = self.database.load_maps(self.region)
        
        # Load and save each satellite imagery layer
        for key in self.backgrounds:
            self.backgrounds_dict[key] = py.image.load(png[key])
            py.image.save(self.backgrounds_dict[key], f"images/{key}.jpg")
        
        # Display initial background (satellite map)
        self.screen.blit(self.backgrounds_dict[self.backgrounds[self.i_background]], (0, 0))
        self.window.flip()
        print('... Environmental data loaded successfully')

    def toggle_fire_filter(self):
        """
        Toggle display of fire detection validation overlay.
        
        Shows/hides comparison between simulation results and actual fire
        detection data from NASA FIRMS for model accuracy assessment.
        """
        if self.modification_possible:
            self.fire_visibility = not(self.fire_visibility)
            self.update_map()
            self.window.flip()

    def update_map(self):
        """
        Render the current simulation state with fire progression overlay.
        
        Displays the selected satellite background with fire state visualization:
        - White: Ignition point
        - Orange/Red gradient: Fire progression states
        - Black: Burned areas
        - Blue: Water bodies
        - Validation colors: Green (correct prediction), Red (missed fire)
        """
        # Calculate cell dimensions for grid overlay
        width, height = [self.screen_dimensions[i] // self.map_dimensions[i] for i in range(2)]
        
        # Display selected satellite background
        background = self.backgrounds_dict[self.backgrounds[self.i_background]]
        if background:
            self.screen.blit(background, (0, 0))
        else:
            self.screen.fill((0, 200, 0))  # Fallback green background
        
        # Render fire state overlay for each grid cell
        for x in range(self.map_dimensions[0]):
            for y in range(self.map_dimensions[1]):
                pos = (x * width, y * height)
                surf = py.Surface((width, height), py.SRCALPHA)  # Transparent overlay
                parcel = self.map.map[x][y]
                color = (0, 0, 0, 100)  # Default border color
                
                # Determine cell visualization based on state
                if parcel.water:
                    # Water bodies (cannot burn)
                    surf.fill((0, 0, 255, 150))  # Blue with transparency
                elif parcel.position == self.fire_origin and parcel.s == 0:
                    # Ignition point before fire starts
                    surf.fill((255, 255, 255, 200))  # White marker
                elif self.fire_visibility and self.modification_possible:
                    # Fire detection validation mode
                    if parcel.s == 4:  # Completely burned
                        if parcel.fire:
                            # Correct prediction: both simulated and detected
                            surf.fill((0, 200, 0, 200))  # Green
                        else:
                            # False negative: simulated but not detected
                            surf.fill((200, 0, 0, 100))  # Red
                    elif parcel.fire:
                        # False positive: detected but not simulated
                        surf.fill((100, 100, 0, 200))  # Yellow
                else:
                    # Normal fire progression visualization
                    if parcel.s == 1:
                        # Ignition threshold reached
                        surf.fill((255, 150, 0, 70))  # Light orange
                    elif parcel.s == 2:
                        # Actively burning
                        surf.fill((255, 0, 0, 150))  # Red
                    elif parcel.s == 3:
                        # Fire cooling down
                        surf.fill((255, 0, 0, 190))  # Dark red
                    elif parcel.s == 4:
                        # Completely burned
                        surf.fill((0, 0, 0, 125))  # Semi-transparent black
                
                # Draw cell border and overlay
                py.draw.rect(surf, color, surf.get_rect(), 1)
                self.screen.blit(surf, (pos[0], pos[1]))
        
        # Display current simulation time
        font = py.font.SysFont('Arial', 40, 'white')
        time_text = self.actual_time.strftime('%Y/%m/%d, %Hh%M')
        text_img = font.render(time_text, True, (255, 255, 255))
        self.screen.blit(text_img, (50, self.screen_dimensions[1] - 70))

    def reset(self):
        """
        Reset simulation to initial state with fresh environmental data.
        
        Reloads terrain data, resets fire states, and restores interface
        to allow new simulation execution.
        """
        print('RESET')
        self.modification_possible = True
        self.actual_time = self.date
        
        # Regenerate map with current environmental data
        self.map = fire.Map(self)
        self.map.generate_map(self.map_parameters)
        
        # Update display
        self.update_map()
        self.window.flip()

    def set_fire(self):
        """
        Execute real-world fire propagation simulation.
        
        Runs the fire spread algorithm using actual environmental data,
        tracking performance metrics including execution time and iteration count.
        Incorporates real temporal progression during simulation.
        """
        if self.modification_possible:
            t = time.time()
            print('-' * 15)
            print('FIRE SIMULATION STARTING...')
            
            # Lock interface during simulation
            self.modification_possible = False
            
            # Execute fire propagation with real environmental data
            iterations = self.map.fire(self.fire_origin)
            
            # Restore interface control
            self.modification_possible = True
            
            # Update final display
            self.update_map()
            self.window.flip()
            
            # Report simulation performance
            execution_time = round(time.time() - t, 2)
            print(f"SIMULATION COMPLETE - Iterations: {iterations} (Runtime: {execution_time}s)")
            print('-' * 15)

    def click(self, mouse_pressed):
        """
        Handle mouse clicks for terrain parcel inspection.
        
        Displays detailed environmental data for the clicked terrain cell,
        including satellite data, weather conditions, and fire state.
        
        Args:
            mouse_pressed (tuple): Mouse button state from pygame
        """
        if self.modification_possible:
            pos = py.mouse.get_pos()
            
            # Convert screen coordinates to grid indices
            width, height = [self.screen_dimensions[i] // self.map_dimensions[i] for i in range(2)]
            i, j = pos[0] // width, pos[1] // height
            
            # Display parcel information
            print(self.map.map[i][j])
            time.sleep(0.1)  # Prevent multiple rapid clicks

    def toggle_background(self):
        """
        Cycle through available satellite imagery layers.
        
        Switches between different data visualizations:
        - Map: Standard satellite imagery
        - Elevation: Topographic data
        - Temperature: Thermal conditions
        - Treecover: Vegetation coverage
        - FIRMS: NASA fire detection data
        """
        # Cycle to next background layer
        self.i_background = (self.i_background + 1) % len(self.backgrounds)
        
        # Special handling for FIRMS overlay (uses map as base)
        if self.backgrounds[self.i_background] == 'firms':
            self.screen.blit(self.backgrounds_dict['map'], (0, 0))
        
        # Update display based on simulation state
        if self.modification_possible:
            self.update_map()  # Full update with fire overlay
        else:
            # Just switch background without fire overlay
            self.screen.blit(self.backgrounds_dict[self.backgrounds[self.i_background]], (0, 0))
        
        self.window.flip()


# Application initialization and main event loop
py.init()
screen = Screen(py.display, 0.3)

print("\nReal-World Forest Fire Simulation")
print("Controls:")
print("- Press 'F' to start fire simulation")
print("- Press 'R' to reset simulation")
print("- Press 'T' to toggle fire detection validation")
print("- Press 'U' to cycle satellite imagery layers")
print("- Click parcels to view environmental data")
print("- Press 'ENTER' to exit")

while True:
    for event in py.event.get():
        if event.type == py.QUIT:
            sys.exit()
            
        if event.type == py.KEYDOWN:
            if event.key == py.K_f:          # Start fire simulation
                screen.set_fire()
            if event.key == py.K_RETURN:     # Exit application
                sys.exit()
            if event.key == py.K_r:          # Reset simulation
                screen.reset()
            if event.key == py.K_t:          # Toggle fire validation overlay
                screen.toggle_fire_filter()
            if event.key == py.K_u:          # Switch satellite imagery layer
                screen.toggle_background()

    # Handle mouse clicks for parcel inspection
    if py.mouse.get_pressed():
        mouse_state = py.mouse.get_pressed()
        if mouse_state == (1, 0, 0) or mouse_state == (0, 0, 1):  # Left or right click
            screen.click(mouse_state)