# Autor: Frederic Diemer
# Bibliothek zum Rendern mit Schnittstelle zu zbuffering.dll

import math, ctypes, os     # ctypes stellt Schnittstelle zu C-Programmen bereit
import numpy as np

class Camera:   # Klasse Camera stellt Beobachter dar und implementiert das Rendern
    def __init__(self, cam_pos = [0,0,0], view_direc=0, view_direc_alpha=0, angle_of_view=90, screen_width=100, screen_height=75, min_view_distance=1, max_view_distance=500, bgcolor=(0,0,0)):  # Angabe aller Winkel als Paramter in Grad
        # Parameter: cam_pos: Position des Beobachters; view_direc: (horizontale) Blickrichtung des Beobachters; view_direc_alpha: (vertikale) Blickrichtung des Beobachters; angle_of_view: Winkel des Blickfelds; 
        #       screen_width: Breite des Fensters; screen_height: Höhe des Fensters; min_view_distance: minimale Renderdistanz; max_view_distance: maximale Renderdistanz; bgcolor: Hintergrundfarbe
        self.cam_pos = cam_pos
        self._view_direc = math.radians(view_direc)             # Umwandlung in Bogenmaß
        self._view_direc_alpha = math.radians(view_direc_alpha) # Umwandlung in Bogenmaß
        self.angle_of_view = math.radians(angle_of_view)        # Umwandlung in Bogenmaß
        self.screen_width = screen_width
        self.screen_height = screen_height                      
        self.min_view_distance = min_view_distance
        self.max_view_distance = max_view_distance
        self.screen_distance = 0
        self.bgcolor = bgcolor
        # Erzeugung des Z-Buffers
        self.zbuffer = np.full((self.screen_height, self.screen_width), self.max_view_distance, dtype=np.float32) 
        self.zbuffer_p = self.zbuffer.ctypes.data_as(ctypes.POINTER(ctypes.c_float))
        # Erzeugung eines Arrays zur Speicherung der Pixelfarben
        self.colors = np.zeros(shape=(self.screen_height, self.screen_width, 3), dtype=np.uint8)
        self.colors_p = self.colors.ctypes.data_as(ctypes.POINTER(ctypes.c_uint8))

        # Laden der C-Datei (Dateinamenerweiterung unter Windows: .dll; unter Unix: .so)
        self.clib = ctypes.CDLL(os.path.join(os.path.dirname(os.path.abspath(__file__)), "zbuffering."+"dll" if os.name == "nt" else "so"))
        # Angabe aller Übergabeparameter-Typen zu allen verwendeten C-Funktionen
        self.clib.render.argtypes = [
            ctypes.POINTER(ctypes.c_float),         # zbuffer
            ctypes.POINTER(ctypes.c_uint8),         # color matrix
            ctypes.c_int32,                         # width
            ctypes.c_int32,                         # height
            ctypes.POINTER(ctypes.c_int32),         # faces
            ctypes.c_int32,                         # amount_of_faces
            ctypes.POINTER(ctypes.c_float),         # precalc_vertices
            ctypes.c_int32,                         # amount_of_vertices
            ctypes.POINTER(ctypes.c_float),         # zcords
            ctypes.POINTER(ctypes.c_float),         # uvcords
            ctypes.POINTER(ctypes.c_uint8),         # colors
            ctypes.POINTER(ctypes.c_int32),         # face_textures
            ctypes.POINTER(ctypes.c_int32),         # texture_sizes
            ctypes.POINTER(ctypes.c_uint8)          # textures
        ]
        self.clib.render_with_resolution.argtypes = [
            ctypes.POINTER(ctypes.c_float),         # zbuffer
            ctypes.POINTER(ctypes.c_uint8),         # color matrix
            ctypes.c_int32,                         # width
            ctypes.c_int32,                         # height
            ctypes.POINTER(ctypes.c_int32),         # faces
            ctypes.c_int32,                         # amount_of_faces
            ctypes.POINTER(ctypes.c_float),         # precalc_vertices
            ctypes.c_int32,                         # amount_of_vertices
            ctypes.POINTER(ctypes.c_float),         # zcords
            ctypes.POINTER(ctypes.c_uint8),         # colors
            ctypes.c_uint8                          # resolution_factor
        ]
        self.clib.reset_zbuffer.argtypes = [
            ctypes.POINTER(ctypes.c_float),         # zbuffer
            ctypes.POINTER(ctypes.c_uint8),         # color matrix
            ctypes.c_int32,                         # width
            ctypes.c_int32,                         # height
            ctypes.c_float,                         # max render distance
            ctypes.c_uint8,                         # bgcolor (r)
            ctypes.c_uint8,                         # bgcolor (g)
            ctypes.c_uint8                          # bgcolor (b)
        ]

        self.update_screen_distance()   # berechnet z-Koordinate der Bildebene

    # getters and setters zur Umwandlung von Grad in Bogenmaß und umgekehrt
    def set_view_direc(self, degrees):
        r"setter for view_distance, converts from degrees to radians"
        self._view_direc = math.radians(degrees)
    def set_view_direc_alpha(self, degrees):
        r"setter for view_distance_alpha, converts from degrees to radians"
        self._view_direc_alpha = math.radians(degrees)
    
    view_direc = property(fget=lambda self: math.degrees(self._view_direc), 
                            fset=set_view_direc)
    view_direc_alpha = property(fget=lambda self: math.degrees(self._view_direc_alpha), 
                            fset=set_view_direc_alpha)

    def update_screen_distance(self): # berechnet z-Koordinate der Bildebene aus Fensterbreite und Blickfeld
        r"updates self.screen_distance which is related to self.screen_width and self.angle_of_view"
        self.screen_distance = self.screen_width / (2*math.tan(self.angle_of_view/2))


    # Vektor Verarbeitungsmethoden
    def transform_point(self, coordinates): # Verschiebt und dreht 3d-Punkte
        r"moves and transformes a point to make it suitable for projection"
        # Verschiebung, sodass Beobachter Zentrum des Koordinatensystems
        moved_point = [coordinates[i] - self.cam_pos[i] for i in range(3)]

        turned_point = 3*[0]
        # Rotation eines Punktes in x-z-Ebene (horizontal) entsprechend Blickrichtung
        turned_point[0] = moved_point[2]*math.sin(-self._view_direc)+ \
            moved_point[0]*math.cos(-self._view_direc)
        turned_point[1] = moved_point[1]
        turned_point[2] = moved_point[2]*math.cos(-self._view_direc)- \
            moved_point[0]*math.sin(-self._view_direc)

        # Rotation eines Punktes in y-z-Ebene (vertikal) entsprechend Blickrichtung
        turned_point2 = 3*[0]
        turned_point2[0] = turned_point[0]
        turned_point2[1] = turned_point[2]*math.sin(-self._view_direc_alpha)+ \
            turned_point[1]*math.cos(-self._view_direc_alpha)
        turned_point2[2] = turned_point[2]*math.cos(-self._view_direc_alpha)- \
            turned_point[1]*math.sin(-self._view_direc_alpha)
        return turned_point2

    def project(self, coordinates3d, save_z=None, obj=None):    # Projiziert 3d-Punkt auf Bildebene
        # Parameter: save_z gibt an, ob z-Wert gespeichert werden soll; obj gibt zugehöriges Objekt an
        r"returns a 2d projection of a 3d point !only use on transformed points!"
        if not self.visible(coordinates3d):     # Rendert keine Punkte, welche sich hinter dem Beobachter befinden
            return None
        coordinates2d = 2*[0]
        # Berechnet 2d Punkt durch Strahlensatz
        coordinates2d[0] = coordinates3d[0]* self.screen_distance/coordinates3d[2]
        coordinates2d[1] = coordinates3d[1]* self.screen_distance/coordinates3d[2]
        if save_z != None:      # Speichert z-Wert, sofern gefordert
            obj.vertice_z_values[save_z]=coordinates3d[2]
        return coordinates2d
    
    def render(self, coordinates3d, save_z=None, obj=None): # führt andere Funktionen der Klasse aus um einzelnen Punkt auf Bildebene zu projizieren
        # Parameter: save_z gibt an, ob z-Wert gespeichert werden soll; obj gibt zugehöriges Objekt an
        r"renders a 3d point to 2d"
        return self.project(self.transform_point(coordinates3d), save_z, obj)
    
    def visible(self, coordinates3d): # Gibt an, ob Punkt gerendert werden kann
        # Parameter: coordinates3d: 3d-Koordinaten des Punkts
        r"returns whether a point is not in the area behind the minimum render distance !use on transformed points only!"
        return coordinates3d[2] > self.min_view_distance and \
            (self.max_view_distance==None or coordinates3d[2] < self.max_view_distance) # stellt sicher, dass Punkt nicht Außerhalb der Grenzen für Renderdistanz

    def convert2drawable_coordinate(self, coordinate2d): # Wandelt 2d-Koordinate um, sodass sie Koordinate auf Bildschirm entspricht
        r"invertes x and y value and adds an offset to make them suitable for pygame coordinate system"
        if coordinate2d == None:
            return None, None
        return [(self.screen_width/2)-coordinate2d[0], (self.screen_height/2)-coordinate2d[1]]  # invertieren von x und y Werten + Offset um an pygame Koordinatensystem anzupassen

    def precalc_vertices(self, obj):    # Projiziert alle Eckpunkte eines Objekts auf Bildebene und speichert diese in precalc_vertices
        # Parameter: obj: Objekt, dessen Eckpunkte projiziert werden sollen
        r"renders vertices of a loader so they don't get rendered twice"
        obj.precalc_vertices = []
        for i, vertex in enumerate(obj.vertices):       # Projektion aller Eckpunkte
            obj.precalc_vertices.append(self.convert2drawable_coordinate(self.render(vertex, save_z=i, obj=obj)))
        # Vorbereiten der Liste mit Eckpunkten für Übergabe an C-Programm
        obj.precalc_vertices = np.array(obj.precalc_vertices, dtype=np.float32)
        obj.precalc_vertices_p = obj.precalc_vertices.ctypes.data_as(ctypes.POINTER(ctypes.c_float))

    def render_object_to_zbuffer(self, obj, resolution_factor=1): # Übergibt zu renderndes Objekt an C-Programm
        # Parameter: obj: zu renderndes Objekt; resolution_factor: ganzzahliger Faktor, welcher Auflösung verringert, um Performance zu optimieren
        r"renders all faces of an object to z-buffer"
        if resolution_factor == 1:  # keine Verringerung der Auflösung --> Standardmethode
            self.clib.render(
                                self.zbuffer_p, self.colors_p, self.screen_width, self.screen_height,
                                obj.faces_p, obj.amount_of_faces, obj.precalc_vertices_p, obj.amount_of_vertices, 
                                obj.vertice_z_values_p, obj.texture_vertices_p, obj.face_colors_p, obj.face_textures_p,
                                obj.texture_sizes_p, obj.textures_p
                            )
        else:                       # Verringerung der Auflösung --> angepasste Methode
            self.clib.render_with_resolution(
                                self.zbuffer_p, self.colors_p, self.screen_width, self.screen_height,
                                obj.faces_p, obj.amount_of_faces, obj.precalc_vertices_p, obj.amount_of_vertices, 
                                obj.vertice_z_values_p, #obj.texture_vertices_p, 
                                obj.face_colors_p, #obj.c_face_textures,
                                resolution_factor
                            )
    
    def reset_zbuffer(self):    # Funktion setzt Z-Buffer und Farbmatrix zurück
        r"resets the z-buffer and the color matrix"
        self.clib.reset_zbuffer(    # Aufruf C-Programm für bessere Performance
                                self.zbuffer_p, self.colors_p, self.screen_width, self.screen_height,
                                self.max_view_distance, *self.bgcolor
                               )

