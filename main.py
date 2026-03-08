# Autor: Frederic Diemer
# Hauptprogramm zum Projekt 3d-Rendering

from pygame.locals import *         # Pygame als Grafikbibliothek
import pygame as pg
from rendering import Camera
import math, numpy, time
from object_loader import Loader


class Viewer(Camera):   # Klasse Viewer implementiert Beobachter mit Steuerung über Tastatur
    def __init__(self, pos, speed, turnspeed, view_direc=0, view_direc_alpha=0, angle_of_view=90, min_view_distance=0, max_view_distance=100):
        # Parameter: pos: Position des Beobachters; speed: Geschwindigkeit des Beobachters; turnspeed: Geschwindigkeit beim Drehen
        #   view_direc: Blickrichtung (als Winkel); view_direc_alpha: Höhe der Blickrichung (als Winkel); angle_of_view: Blickwinkel (90 Grad ist Standard bzw. kein Zoom)
        #   min_view_distance: minimale Renderdistanz; max_view_distance: maximale Renderdistanz
        super().__init__(pos, view_direc, view_direc_alpha, angle_of_view, W, H, min_view_distance, max_view_distance, bgcolor=(255,255,255))   # Initialisierung der Elternklasse Camera
        self.speed = speed
        self.turnspeed = turnspeed
    
    def update(self):   # Bewegung des Beobachters
        keys_pressed = pg.key.get_pressed()
        if keys_pressed[K_w]:               # Vorwärtsbewegung bei Drücken von w
            self.cam_pos[2] += self.speed/FPS * math.cos(self._view_direc)
            self.cam_pos[0] += self.speed/FPS * math.sin(self._view_direc)
        if keys_pressed[K_s]:               # Rückwärtsbewegung bei Drücken von s
            self.cam_pos[2] -= self.speed/FPS * math.cos(self._view_direc)
            self.cam_pos[0] -= self.speed/FPS * math.sin(self._view_direc)
        if keys_pressed[K_d]:               # Seitwärtsbewegung nach rechts bei Drücken von d
            self.cam_pos[2] += self.speed/FPS * math.cos(self._view_direc - math.pi/2)
            self.cam_pos[0] += self.speed/FPS * math.sin(self._view_direc - math.pi/2)
        if keys_pressed[K_a]:               # Seitwärtsbewegung nach links bei Drücken von a
            self.cam_pos[2] += self.speed/FPS * math.cos(self._view_direc + math.pi/2)
            self.cam_pos[0] += self.speed/FPS * math.sin(self._view_direc + math.pi/2)
        if keys_pressed[K_e]:               # Aufwärtsbewegung bei Drücken von e
            self.cam_pos[1] += self.speed/FPS
        if keys_pressed[K_q]:               # Abwärtsbewegung bei Drücken von q
            self.cam_pos[1] -= self.speed/FPS
        if keys_pressed[K_LEFT]:            # Blick nach links
            self.view_direc = self.view_direc + self.turnspeed/FPS
        if keys_pressed[K_RIGHT]:           # Blick nach rechts
            self.view_direc = self.view_direc - self.turnspeed/FPS
        if keys_pressed[K_UP]:              # Blick nach oben richten
            self.view_direc_alpha = self.view_direc_alpha + self.turnspeed/FPS
        if keys_pressed[K_DOWN]:            # Blick nach unten richten
            self.view_direc_alpha = self.view_direc_alpha - self.turnspeed/FPS
    
    def draw(self): # zeichnet Beobachter mit Blickrichtung in Minimap ein
        # Skaliert x und y auf Minimap
        x = self.cam_pos[2]*MINIMAP_SIZE[0]/MAPX + MINIMAP_SIZE[0]/2
        y = MINIMAP_SIZE[1]/2 - self.cam_pos[0]*MINIMAP_SIZE[1]/MAPY   # Invertieren von y

        if 0 <= x and x <= MINIMAP_SIZE[0] and 0 <= y and y <= MINIMAP_SIZE[1]: # Begrenzen auf Bereich der Minimap
            # Zeichnen der Blickrichtung als Linie
            length = 100# Länge der Linie
            x2 = W      # Endpunkt der Linie
            y2 = H
            while x2 > MINIMAP_SIZE[0] or y2 > MINIMAP_SIZE[1]: # Begrenzen von Linie auf Minimap
                x2 = x + math.cos(self._view_direc)*length
                y2 = y - math.sin(self._view_direc)*length
                length -= 1
            pg.draw.aaline(screen, BLUE, (x,y), (x2,y2))    # Zeichnen der Linie

            # draw viewer
            pg.draw.circle(screen, RED, (x,y), 5)   # Zeichnen des Beobachters als roten Punkt in Minimap

def draw_minimap():     # Zeichnet Minimap als weißes Rechteck mit schwarzer Umrandung oben links ein
    pg.draw.rect(screen, WHITE, (0, 0, *MINIMAP_SIZE))
    pg.draw.aaline(screen, BLACK, (0, MINIMAP_SIZE[1]), MINIMAP_SIZE)
    pg.draw.aaline(screen, BLACK, (MINIMAP_SIZE[0], 0), MINIMAP_SIZE)

# Definition von Variabeln
W, H = 1200, 700        # Breite und Höhe des Fensters
FPS = 30                # Framerate
MINIMAP_SIZE = (W//5, H//5) # Größe der Minimap
MAPX = 40                                           # in Minimap angezeigte Breite entspricht MAPX
MAPY = MAPX * MINIMAP_SIZE[1]/MINIMAP_SIZE[0]
obj_files = ["Objects/Car.obj"]             # Liste mit .obj Dateien, die gerendert werden
# Definition von Farben
WHITE = (255,255,255)
BLUE = (50, 50, 200)
RED = (150, 10, 10)
BLACK = (0,0,0)
bg = WHITE              # setzen der Hintergrundfarbe


# Fenster setup
screen = pg.display.set_mode((W, H))
pg.display.set_caption("Rendering demo")
clock = pg.time.Clock()


# Initialisierung von Objekten
viewer = Viewer([0,0,-14], 10, 40, 20, 0)
objects_from_files = []
for file in obj_files:                                  # Laden von 3d-Objekten aus Dateien
    objects_from_files += Loader(file, True).objects


running = True          # Wahrheitswert gibt an, dass das Programm noch läuft & Fenster nicht geschlossen werden soll
while running:          # Loop der das Fenster aktualisiert
    for event in pg.event.get():        # Abfrage von Events
        if event.type == QUIT:          # Event: Schließung des Fensters
            running = False

    # Update des Beobachters
    viewer.update()


    screen.fill(bg)     # Zurücksetzen des Fensters

    # 3d Zeichnen
    for obj in objects_from_files:          # Projektion der Eckpunkte
        viewer.precalc_vertices(obj)
    viewer.reset_zbuffer()                  # Zurücksetzen des Z-Buffers
    for obj in objects_from_files:          # Rendern aller Objekte
        viewer.render_object_to_zbuffer(obj, resolution_factor=1)

    
    screen.blit(pg.surfarray.make_surface(numpy.array(viewer.colors.swapaxes(0,1))), (0,0)) # Anzeigen der color-Matrix


    # Zeichnen der Minimap
    draw_minimap()
    for point in objects_from_files[0].vertices:        # Einzeichnen aller Eckpunkte in Minimap (top-down Perspektive)
        x = int(point[2] * MINIMAP_SIZE[0] / MAPX + MINIMAP_SIZE[0]/2)
        y = int(MINIMAP_SIZE[1]/2 - point[0] * MINIMAP_SIZE[1] / MAPY)
        pg.draw.circle(screen, BLUE, (x,y), 1)
    viewer.draw()                                       # Einzeichnen von Beobachter in Minimap

    pg.display.flip()   # Aktualisieren des Fensters
    clock.tick(FPS)     # Warten bis zum nächsten Frame


pg.quit()   # Schließen des Fensters
