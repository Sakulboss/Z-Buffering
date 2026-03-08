# Autor: Frederic Diemer
# Programm zum laden von .obj-Dateien

from PIL import Image       # Bibliothek zum Einlesen von Bilddateien
import os, ctypes
import numpy as np

class Object3d: # Klasse zur Speicherung von 3d-Objekten
    def __init__(self, name, direc_path, filename):
        # Parameter: name: Name des Objekts; direc_path: Dateipfad zum Ordner, in welchem sich Datei befindet; filename: Dateiname
        self.name, self.direc_path, self.filename = name, direc_path, filename
        self.vertices = []          # Speichert Eckpunkte
        self.texture_vertices = []  # Liste mit uv-Koordinaten
        self.face_colors = []       # Liste mit Farben der Oberflächen
        self.face_textures = []     # Liste für Zuordnung von Texturen zu Flächen
        self.texture_sizes = []     # Liste mit Formaten der Texturen
        self.textures = []          # Liste mit Texturen
        self.faces = []             # Liste mit Flächen im Format [ [v1, v2, v3, t1, t2, t3], ...] (v=vertex/Eckpunkt, t=uv-Koordinaten)
    
    def __str__(self):
        return "<3d-Object "+self.name+" from "+self.filename+">"

    def __repr__(self):
        return self.__str__()

    def to_np_arrays(self):         # bereitet Objekt auf Übergabe an C-Programm vor
        self.amount_of_faces = len(self.faces)          # Anzahl der Flächen
        self.amount_of_vertices = len(self.vertices)    # Anzahl der Eckpunkte
        # Umwandeln der Listen in numpy Arrays und Erzeugen von Pointern
        self.vertices = np.array(self.vertices, dtype=np.float32)
        self.vertice_z_values = np.array([x[2] for x in self.vertices], dtype=np.float32)
        self.vertice_z_values_p = self.vertice_z_values.ctypes.data_as(ctypes.POINTER(ctypes.c_float))
        self.texture_vertices = np.array(self.texture_vertices, dtype=np.float32)
        self.texture_vertices_p = self.texture_vertices.ctypes.data_as(ctypes.POINTER(ctypes.c_float))
        self.face_colors = np.array(self.face_colors, dtype=np.uint8)
        self.face_colors_p = self.face_colors.ctypes.data_as(ctypes.POINTER(ctypes.c_uint8))
        self.faces = np.array(self.faces, dtype=np.uint32)
        self.faces_p = self.faces.ctypes.data_as(ctypes.POINTER(ctypes.c_int32))

        # Einlesen der Bilddateien zu Texturen
        loaded_textures = []
        for index in range(len(self.face_textures)):
            if self.face_textures[index] == "":         # Überspringen von ungültigen / nicht vorhandenen Texturen
                self.face_textures[index] = -1
            elif self.face_textures[index] in loaded_textures:  # Überspringen von bereits geladenen Texturen
                self.face_textures[index] = loaded_textures.index(self.face_textures[index])
            else:
                loaded_textures.append(self.face_textures[index])
                with Image.open(self.face_textures[index]) as img:  # öffnen der Datei
                    img.convert("RGB")
                    self.texture_sizes += list(img.size)        # Auslesen des Formats
                    self.textures.append([])
                    pic = img.load()
                    for y in range(img.size[1]):                # Iteration über alle Pixel
                        for x in range(img.size[0]):
                            self.textures[-1].append(pic[x,y])  # Speichern der Pixel in Liste
                self.face_textures[index] = len(self.textures)-1

        # Umwandeln der Listen in numpy Arrays und Erzeugen von Pointern
        self.face_textures_p = np.array(self.face_textures, dtype=np.int32).ctypes.data_as(ctypes.POINTER(ctypes.c_int32))
        self.texture_sizes_p = np.array(self.texture_sizes, dtype=np.int32).ctypes.data_as(ctypes.POINTER(ctypes.c_int32))
        self.textures_p = np.array(self.textures, dtype=np.uint8).ctypes.data_as(ctypes.POINTER(ctypes.c_uint8))

class Loader:       # Klasse zum Einlesen einer .obj-Datei
    def __init__(self, filepath, to_np_array=False):
        # Parameter: filepath: Dateipfad, to_np_array: Wahrheitswert, ob Übergabe an C-Programm vorbereitet werden soll
        self.direc_path, self.filename = os.path.split(filepath)        # Aufteilen des Dateipfads
        self.vertices = []                  # Liste mit Eckpunkte
        self.normals = []                   # Liste mit Normalen
        self.texture_vertices = []          # Liste mit uv-Koordinaten
        self.objects = []                   # Liste mit Objekten
        self.mtllibs = []                   # Liste mit .mtl - Bibliotheken
        self.face_colors = {}               # Dictionary mit Farben der Flächen
        self.face_textures = {}             # Dictionary mit Texturen der Flächen
        self.face_materials = []            # Liste mit Materialien der Flächen
        self.read()                         # Aufruf der Funktion zum auslesen der Datei
        if to_np_array:                     # Vorbereiten der Objekte auf Verwendung in C-Programm
            for obj in self.objects:
                obj.to_np_arrays()

    def read(self):                         # Einlesen der Datei
        current_object = Object3d("default", self.direc_path, self.filename)    # Gibt aktuelles Objekt an
        current_mtl = None                                                      # gibt aktuelles Material an
        with open(self.direc_path+os.sep+self.filename, "r") as obj_file:       # Öffnen der Datei
            for line in obj_file.readlines():                                   # Auslesen Zeile für Zeile
                line_content = line.split("#")[0].strip().split(" ")            # Trennen an '#' um Kommentare zu überspringen

                # Entfernen leerer Strings
                index = 0
                while index < len(line_content):
                    if len(line_content[index]) == 0:
                        del line_content[index]
                    else:
                        index += 1

                # Überspringen der aktuellen Zeile falls Zeile leer
                if len(line_content) == 0:
                    continue
                
                # Verarbeitung des Inhalts
                if line_content[0] == "o":
                    current_object = Object3d(" ".join(line_content[1:]), self.direc_path, self.filename)
                elif line_content[0] == "f":
                    if current_object not in self.objects:
                        self.objects.append(current_object)
                    temp = [[int(value)-1 if value.strip() != "" else 0 for value in vertex.split("/")] for vertex in line_content[1:]]
                    # Umwandlung von Format [[v1, uv1, vn1], [v2, uv2, vn2], ...] zu Format [[v1, v2, ...], [uv1, uv2, ...], [vn1, vn2, ...]]
                    turned = [[temp[i][j] for i in range(len(temp))] for j in range(2)]
                    for i in range(1, len(temp)-1):
                        current_object.faces.append([[turned[0][0],turned[0][i],turned[0][i+1]], [turned[1][0],turned[1][i],turned[1][i+1]]])
                        self.face_materials.append(current_mtl)
                elif line_content[0] == "v":
                    self.vertices.append([float(value) for value in line_content[1:]])
                elif line_content[0] == "vn":
                    self.normals.append([float(value) for value in line_content[1:]])
                elif line_content[0] == "vt":
                    self.texture_vertices.append([float(value) for value in line_content[1:]])
                elif line_content[0] == "mtllib":
                    self.mtllibs.append(" ".join(line_content[1:]))
                elif line_content[0] == "usemtl":
                    current_mtl = " ".join(line_content[1:])
        
        if len(self.texture_vertices) == 0:
            self.texture_vertices.append((0.0, 0.0))


        for mtllib in self.mtllibs:     # Einlesen aller .mtl Bibliotheken
            current_mtl = None
            with open(self.direc_path+os.sep+mtllib, "r") as mtl_file:
                for line in mtl_file.readlines():
                    line_content = line.split("#")[0].strip().split(" ")            # Trennen an '#' um Kommentare zu überspringen

                    # Entfernen leerer Strings
                    index = 0
                    while index < len(line_content):
                        if len(line_content[index]) == 0:
                            del line_content[index]
                        else:
                            index += 1

                    # Überspringen leerer Zeilen
                    if len(line_content) == 0:
                        continue
                    
                    # Verarbeiten / Auslesen des Inhalts
                    if line_content[0] == "newmtl":
                        current_mtl = " ".join(line_content[1:])
                    # Ignoration von Ka, Ks, Ns, illum etc. da zu komplex für Rahmen des Projekts
                    elif line_content[0] == "Kd":
                        self.face_colors[current_mtl] = [float(value) for value in line_content[1:4]]
                    elif line_content[0] == "map_Kd":
                        texture_path = " ".join(line_content[1:])
                        if not os.path.isabs(texture_path): 
                            texture_path = os.path.join(self.direc_path, texture_path)
                        self.face_textures[current_mtl] = texture_path
                        

        for obj in self.objects:        # Erzeugen von Objekten der Klasse Object für jedes 3d-Objekt
            for face_index, face in enumerate(obj.faces):
                # Kopieren der Eckpunkte
                for vertex_index in range(3):
                    if self.vertices[face[0][vertex_index]] not in obj.vertices:
                        obj.vertices.append(self.vertices[face[0][vertex_index]])
                        face[0][vertex_index] = len(obj.vertices)-1
                    else:
                        face[0][vertex_index] = obj.vertices.index(self.vertices[face[0][vertex_index]])
                # Kopieren der uv-Koordinaten
                for vertex_index in range(3):
                    if self.texture_vertices[face[1][vertex_index]] not in obj.texture_vertices:
                        obj.texture_vertices.append(self.texture_vertices[face[1][vertex_index]])
                        face[1][vertex_index] = len(obj.texture_vertices)-1
                    else:
                        face[1][vertex_index] = obj.texture_vertices.index(self.texture_vertices[face[1][vertex_index]])
                # Kopieren der Texturen
                if self.face_materials[face_index] == None:
                    obj.face_colors.append((0,0,0))
                    obj.face_textures.append("")
                else:
                    obj.face_colors.append(self.convert_color(self.face_colors[self.face_materials[face_index]]))
                    obj.face_textures.append(self.face_textures[self.face_materials[face_index]] if self.face_materials[face_index] in self.face_textures.keys() else "")

            
                
    
    def convert_color(self, color):     # Konvertiert Farben von [0;1] zu [0;255]
        return [int(255*color[0]), int(255*color[1]), int(255*color[2])]