"""
Forest Fire Propagation Simulation - Main Interface

This module provides the main visualization and interaction interface for a forest fire
propagation simulation system. It manages the display of terrain, vegetation, and fire
spread dynamics using Pygame for real-time visualization.

The system supports two simulation models:
- Wind-based fire propagation (fire_wind)
- Tree coverage-based propagation (fire_treecover)

Features:
- Real-time fire spread visualization
- Interactive terrain modification
- Multiple simulation models
- Color-coded terrain and fire states
- Performance timing and iteration counting

@author Martin
@created 2022
@version 1.0.0
"""

import pygame as py
import fire_treecover, fire_wind
import time, sys

class Screen:
    """
    Main visualization and control system for forest fire simulation.
    
    Manages the graphical interface, user interaction, and simulation execution
    for studying fire propagation patterns under different environmental conditions.
    """
    
    def __init__(self, window):
        """
        Initialize the fire simulation interface.
        
        Sets up display parameters, creates the initial map, and prepares
        the visualization system for interactive fire simulation.
        
        Args:
            window: Pygame display object for rendering
        """
        self.window = window
        self.modification_possible = True  # Flag to prevent changes during simulation
        
        # Display configuration
        self.screen_dimensions = (500, 500)  # Window size in pixels
        self.map_dimensions = (100, 100)    # Grid resolution (100x100 cells)
        self.fire_origin = (51, 51)         # Default ignition point (center)
        self.mod = 1                        # Current simulation model (1=wind, 2=tree cover)
        
        # Initialize display with forest green background
        self.screen = self.window.set_mode(self.screen_dimensions)
        self.screen.fill((133, 255, 52))  # Light green for healthy vegetation
        
        self.reset()

    def update_map(self):
        """
        Render the current map state with color-coded terrain and fire visualization.
        
        Color coding system:
        - White: Fire ignition point
        - Yellow-Red gradient: Active fire (intensity-based)
        - Dark gray: Burned areas
        - Blue: Water/firebreaks
        - Green variations: Vegetation density
        - Brown: Bare ground/low vegetation
        """
        # Calculate cell dimensions for grid display
        width, height = [self.screen_dimensions[i] // self.map_dimensions[i] for i in range(2)]
        
        # Render each map cell with appropriate color
        for x in range(self.map_dimensions[0]):
            for y in range(self.map_dimensions[1]):
                pos = (x * width, y * height)
                rect = py.Rect(pos[0], pos[1], width, height)
                parcel = self.map.map[x][y]
                
                # Determine cell color based on current state
                if parcel.position == self.fire_origin:
                    color = (255, 255, 255)  # White for ignition point
                elif 0 < parcel.fire < 1:
                    # Active fire: yellow to red gradient based on intensity
                    yellow = 255 * (1 - parcel.fire ** 0.5)
                    color = (225, yellow, 0)
                elif parcel.fire == 1:
                    color = (34, 34, 34)     # Dark gray for burned areas
                elif parcel.fire == -1:
                    color = (0, 0, 255)      # Blue for water/firebreaks
                else:
                    # Terrain visualization based on vegetation density
                    if parcel.ground == 0:
                        # No vegetation: light green grass
                        r, g, b = 133, 255, 52
                    elif 0.1 < parcel.ground:
                        # Dense vegetation: darker green
                        c = parcel.ground
                        r, g, b = 0, 255 * c, 0
                    else:
                        # Sparse vegetation: brown tones
                        c = parcel.ground
                        r, g, b = 150 * (1 - parcel.ground), 60 * (1 - parcel.ground), 30 * (1 - parcel.ground)
                    color = (r, g, b)
                
                py.draw.rect(self.screen, color, rect)
        
        time.sleep(0.01)  # Small delay for smooth animation

    def reset(self):
        """
        Reset the simulation to initial state with fresh terrain generation.
        
        Creates a new map using the selected simulation model and restores
        the interface to allow terrain modifications before fire ignition.
        """
        print('RESET')
        self.modification_possible = True
        
        # Initialize map based on selected simulation model
        if self.mod == 1:
            # Wind-based fire propagation model
            self.map = fire_wind.Map(self.map_dimensions, self)
        elif self.mod == 2:
            # Tree coverage-based propagation model
            self.map = fire_treecover.Map(self.map_dimensions, self)
        
        # Update display and refresh screen
        self.update_map()
        self.window.flip()

    def set_fire(self):
        """
        Execute fire propagation simulation from the designated origin point.
        
        Runs the complete fire simulation, tracking performance metrics
        including execution time and iteration count. Disables terrain
        modification during simulation execution.
        """
        t = time.time()
        print('-' * 15)
        print('FIRE...')
        
        # Lock terrain modifications during simulation
        self.modification_possible = False
        
        # Execute fire propagation algorithm
        iterations = self.map.fire(self.fire_origin)
        
        # Update final display state
        self.window.flip()
        
        # Report simulation performance metrics
        execution_time = round(time.time() - t, 2)
        print(f"END, nombre d'iterations : {iterations} (running time : {execution_time}s)")
        print('-' * 15)

    def switch_mod(self, mod):
        """
        Switch between different fire propagation simulation models.
        
        Changes the underlying physics model used for fire spread calculation
        and resets the simulation with the new model parameters.
        
        Args:
            mod (int): Simulation model identifier
                      1 = Wind-based propagation
                      2 = Tree coverage-based propagation
        """
        if self.mod != mod:
            print(f'Switch from model {self.mod} to model {mod}')
            self.mod = mod
            self.reset()  # Regenerate map with new model


# Application initialization and main event loop
if __name__ == "__main__":
    py.init()
    screen = Screen(py.display)

    print("\nForest Fire Propagation Simulation")
    print("Controls:")
    print("- Press 'F' to ignite fire")
    print("- Press 'R' to reset simulation")
    print("- Press '1' for wind-based model")
    print("- Press '2' for tree coverage model")
    print("- Press 'ENTER' to exit")

    while True:
        for event in py.event.get():
            if event.type == py.QUIT:
                sys.exit()
                
            if event.type == py.KEYDOWN:
                if event.key == py.K_f:          # Ignite fire
                    screen.set_fire()
                if event.key == py.K_RETURN:     # Exit application
                    sys.exit()
                if event.key == py.K_r:          # Reset simulation
                    screen.reset()
                if event.key == py.K_1:          # Switch to wind model
                    screen.switch_mod(1)
                if event.key == py.K_2:          # Switch to tree coverage model
                    screen.switch_mod(2)