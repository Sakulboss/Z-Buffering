// Autor: Frederic Diemer
// Programm zur Umsetzung von Z-Buffering

#include <stdint.h>
#include <stdio.h>
#include <string.h>
#include <math.h>
#include <stdlib.h>

#define ceil_res(value, resolution_factor) (ceil((value)/(resolution_factor))*(resolution_factor))  // Makro zur Rundung von Auflösungen
#define get_precalc_vertex(face_index, vertex_of_face, coordinate) precalc_vertices[2*faces[(face_index)*6+(vertex_of_face)]+(strcmp(#coordinate, "x")==0 || coordinate==0 ? 0 : 1)]    //Makro zum Zugriff auf projizierte Eckpunkte
#define texture_id face_textures[face_index] // Makro zur Abfrage eines Texturindexes

int8_t sign_of_crossP_z(float vec1x, float vec1y, float vec2x, float vec2y) {   // Gibt Vorzeichen des z-Werts eines Kreuzprodukts zurück
    // Parameter: vec1x: x-Wert des ersten Vektors; vec1y: y-Wert des ersten Vektors; vec2x: x-Wert des zweiten Vektors; vec2y: y-Wert des zweiten Vektors
    return vec1x*vec2y-vec1y*vec2x > 0 ? 1 : -1;    // berechnet nur notwendigen Teil (z-Koordinate) des Kreuzprodukts, um Performance zu verbessern
}

float double_area_of_triangle(float vec1x, float vec1y, float vec2x, float vec2y) { // gibt Betrag eines Kreuzprodukts zurück
    // Parameter: vec1x: x-Wert des ersten Vektors; vec1y: y-Wert des ersten Vektors; vec2x: x-Wert des zweiten Vektors; vec2y: y-Wert des zweiten Vektors
    return fabs(vec1x*vec2y-vec1y*vec2x);
    /*
    sqrt(
        (a[1]*0-0*b[1])**2+ | = 0 // da sowieso 0, braucht es nicht zu berechnet werden
        (0*b[0]-a[0]*0)**2+ | = 0
        (a[0]*b[1]-a[1]*b[0])**2 // Quadrat aus der Wurzel von x = Betrag von x
    ) = |a[0]*b[1]-a[1]*b[0]|
    */
}

// Rendern von Objekt mit verringerter Auflösung; !!! unterstüzt keine Texturen !!!
void render_with_resolution(float* zbuffer, uint8_t* color_matrix, int32_t width, int32_t height, 
    int32_t* faces, int32_t amount_of_faces, float* precalc_vertices, int32_t amount_of_vertices, 
    float* zcords, uint8_t* colors, uint8_t resolution_factor) {
    // Parameter: zbuffer: Z-Buffer; color_matrix: Liste zur Zwischenspeicherung der Pixelfarben; width: Fensterbreite; height: Fensterhöhe
    //            faces: Liste mit Flächen (siehe object_loader.py); amount_of_faces: Anzahl der Flächen; precalc_vertices: projizierte Eckpunkte; amount_of_vertices: Anzahl der Eckpunkte
    //            zcords: Z-Koordinaten der Eckpunkte; colors: Farben der Flächen; resolution_factor: Auflösungsfaktor (ganzzahlig)

    for (int face_index=0; face_index<amount_of_faces; face_index++) {  // Iteration über alle Flächen
        uint8_t face_valid = 1;     // gibt an, ob Fläche gültig ist (ungültig heißt: soll nicht gerendert werden)
        // Berechnung von min und max Werten
        float minx = precalc_vertices[2*faces[face_index*6]];       // Initialisierung von min and max mit Werten des ersten Eckpunkts
        float maxx = precalc_vertices[2*faces[face_index*6]];
        float miny = precalc_vertices[2*faces[face_index*6]+1];
        float maxy = precalc_vertices[2*faces[face_index*6]+1];
        // Iteration über alle Eckpunte der Fläche um tatsächliche min/max Werte zu finden
        for (int vertex_index=0; vertex_index<3; vertex_index++) {
            if (isnan(precalc_vertices[2*faces[face_index*6+vertex_index]]) || isnan(precalc_vertices[2*faces[face_index*6+vertex_index]+1])) {
                face_valid = 0;
                break;
            }
            if (precalc_vertices[2*faces[face_index*6+vertex_index]] < minx) {minx = precalc_vertices[2*faces[face_index*6+vertex_index]];}
            if (precalc_vertices[2*faces[face_index*6+vertex_index]] > maxx) {maxx = precalc_vertices[2*faces[face_index*6+vertex_index]];}
            if (precalc_vertices[2*faces[face_index*6+vertex_index]+1] < miny) {miny = precalc_vertices[2*faces[face_index*6+vertex_index]+1];}
            if (precalc_vertices[2*faces[face_index*6+vertex_index]+1] > maxy) {maxy = precalc_vertices[2*faces[face_index*6+vertex_index]+1];}
        }
        if (!face_valid) { // Übersprinen ungültiger Flächen
            continue;
        }
        // Begrenzung von min und max auf Fenstergröße
        if (minx < 0.0) {minx = 0.0;}
        if (miny < 0.0) {miny = 0.0;}
        if (maxx > width) {maxx = width;}
        if (maxy > height) {maxy = height;}

        float border_vectors[] = {  // Enthält Vektoren entlang Kanten der Fläche
            precalc_vertices[2*faces[face_index*6+1]]-precalc_vertices[2*faces[face_index*6]],      // vec(a,b)[0]
            precalc_vertices[2*faces[face_index*6+1]+1]-precalc_vertices[2*faces[face_index*6]+1],  // vec(a,b)[1]
            
            precalc_vertices[2*faces[face_index*6+2]]-precalc_vertices[2*faces[face_index*6+1]],    // vec(b,c)[0]
            precalc_vertices[2*faces[face_index*6+2]+1]-precalc_vertices[2*faces[face_index*6+1]+1],// vec(b,c)[1]

            precalc_vertices[2*faces[face_index*6]]-precalc_vertices[2*faces[face_index*6+2]],      // vec(c,a)[0]
            precalc_vertices[2*faces[face_index*6]+1]-precalc_vertices[2*faces[face_index*6+2]+1]   // vec(c,a)[1]
        }; 
        float face_area = double_area_of_triangle(  // berechnet doppelten Flächeninhalt der Fläche
            border_vectors[0], border_vectors[1], 
            border_vectors[2], border_vectors[3]
        );

        // Iteration über alle Pixel im Rechteckigen Bereich um Fläche
        for (int x=ceil_res(minx, resolution_factor)+resolution_factor/2; x<maxx; x+=resolution_factor) {           // +resolution_factor/2 macht Berechnung ob innerhalb Fläche für Mitte des Pixels; anschließend gleiche Farbe für umliegende Pixel
            for (int y=ceil_res(miny, resolution_factor)+resolution_factor/2; y<maxy; y+=resolution_factor) {
                uint8_t pixel_inside_face = 1;                  // Wahrheitswert, ob Pixel innerhalb Fläche
                for (int vertex_index=0; vertex_index<3; vertex_index++) { // iteriert über Kanten der Fläche
                    int8_t new_orientation = sign_of_crossP_z(
                        border_vectors[2*vertex_index],
                        border_vectors[2*vertex_index+1],
                        x-precalc_vertices[2*faces[face_index*6+vertex_index]],         // vec(v,p)[0]  (v kann a, b oder c sein)
                        y-precalc_vertices[2*faces[face_index*6+vertex_index]+1]        // vec(v,p)[1]  (v kann a, b oder c sein)
                    );
                    if (new_orientation == 1) {pixel_inside_face = 0; break;}           // Abbruch, wenn Pixel nicht auf Richtiger Seite der Kante der Fläche ist
                }
                if (!pixel_inside_face) {   // Überspringen aktuellen Pixels, falls nicht in Fläche
                    continue;
                }
                // Berechnung des z-Wertes des Pixels über baryzentrische Koordinaten
                float z_value = 0;
                for (int vertex_index=0; vertex_index<3; vertex_index++) {
                    z_value += zcords[faces[face_index*6+vertex_index]] * double_area_of_triangle(  // Berechung von je u / v / w und Multiplikation mit z-Koordinate von Eckpunkt
                        border_vectors[2*((vertex_index+1)%3)],
                        border_vectors[2*((vertex_index+1)%3)+1],
                        x-precalc_vertices[2*faces[face_index*6+((vertex_index+1)%3)]],         // vec(v,p)[0]  (v kann a, b oder c sein)
                        y-precalc_vertices[2*faces[face_index*6+((vertex_index+1)%3)]+1]        // vec(v,p)[1]  (v kann a, b oder c sein)
                    ) / face_area;
                }
                if (z_value < zbuffer[y*width+x]) {     // überprüfen, ob z-Wert kleiner als der im z-Buffer
                    for (int dx=-resolution_factor/2; dx < resolution_factor/2 && x+dx < width; dx++) {     // Füllen aller zugehöriger Pixel in Abhängigkeit der Auflösung
                        for (int dy=-resolution_factor/2; dy < resolution_factor/2 && y+dy < height; dy++) {
                            zbuffer[(y+dy)*width+x+dx] = z_value;               // Setzen des z-Buffers
                            // Überschreiben der Farbmatrix
                            color_matrix[3*((y+dy)*width+x+dx)] = colors[3*face_index];   
                            color_matrix[3*((y+dy)*width+x+dx)+1] = colors[3*face_index+1]; 
                            color_matrix[3*((y+dy)*width+x+dx)+2] = colors[3*face_index+2]; 
                        }
                    }
                }
            }
        }
    }
}

// Rendern von Objekt mit normaler Auflösung; unterstüzt Texturen 
void render(float* zbuffer, uint8_t* color_matrix, int32_t width, int32_t height, 
    int32_t* faces, int32_t amount_of_faces, float* precalc_vertices, int32_t amount_of_vertices, 
    float* zcords, float* uvcords, uint8_t* colors, int32_t* face_textures, int32_t* texture_sizes, uint8_t* textures) {
    // Parameter: zbuffer: Z-Buffer; color_matrix: Liste zur Zwischenspeicherung der Pixelfarben; width: Fensterbreite; height: Fensterhöhe
    //            faces: Liste mit Flächen (siehe object_loader.py); amount_of_faces: Anzahl der Flächen; precalc_vertices: projizierte Eckpunkte; amount_of_vertices: Anzahl der Eckpunkte
    //            zcords: Z-Koordinaten der Eckpunkte; colors: Farben der Flächen; face_textures: Indizes der Texturen; texture_sizes: Formate der Texturen; textures: Texturen in rgb


    for (int face_index=0; face_index<amount_of_faces; face_index++) {// Iteration über alle Flächen
        uint8_t face_valid = 1;     // gibt an, ob Fläche gültig ist (ungültig heißt: soll nicht gerendert werden)
        // Berechnung von min und max Werten
        float minx = precalc_vertices[2*faces[face_index*6]];       // Initialisierung von min and max mit Werten des ersten Eckpunkts
        float maxx = precalc_vertices[2*faces[face_index*6]];
        float miny = precalc_vertices[2*faces[face_index*6]+1];
        float maxy = precalc_vertices[2*faces[face_index*6]+1];
        // Iteration über alle Eckpunte der Fläche um tatsächliche min/max Werte zu finden
        for (int vertex_index=0; vertex_index<3; vertex_index++) {
            if (isnan(precalc_vertices[2*faces[face_index*6+vertex_index]]) || isnan(precalc_vertices[2*faces[face_index*6+vertex_index]+1])) { // Abbruch, falls ein Eckpunkt nicht existiert
                face_valid = 0;
                break;
            }
            if (precalc_vertices[2*faces[face_index*6+vertex_index]] < minx) {minx = precalc_vertices[2*faces[face_index*6+vertex_index]];}
            if (precalc_vertices[2*faces[face_index*6+vertex_index]] > maxx) {maxx = precalc_vertices[2*faces[face_index*6+vertex_index]];}
            if (precalc_vertices[2*faces[face_index*6+vertex_index]+1] < miny) {miny = precalc_vertices[2*faces[face_index*6+vertex_index]+1];}
            if (precalc_vertices[2*faces[face_index*6+vertex_index]+1] > maxy) {maxy = precalc_vertices[2*faces[face_index*6+vertex_index]+1];}
        }
        if (!face_valid) { // Überspringen ungültiger Flächen
            continue;
        }
        // Begrenzung von Berechungen auf Fenstergröße
        if (minx < 0.0) {minx = 0.0;}
        if (miny < 0.0) {miny = 0.0;}
        if (maxx > width) {maxx = width;}
        if (maxy > height) {maxy = height;}

        float border_vectors[] = { // Vektoren entlang Kanten der Fläche
            precalc_vertices[2*faces[face_index*6+1]]-precalc_vertices[2*faces[face_index*6]],      // vec(a,b)[0]
            precalc_vertices[2*faces[face_index*6+1]+1]-precalc_vertices[2*faces[face_index*6]+1],  // vec(a,b)[1]
            
            precalc_vertices[2*faces[face_index*6+2]]-precalc_vertices[2*faces[face_index*6+1]],    // vec(b,c)[0]
            precalc_vertices[2*faces[face_index*6+2]+1]-precalc_vertices[2*faces[face_index*6+1]+1],// vec(b,c)[1]

            precalc_vertices[2*faces[face_index*6]]-precalc_vertices[2*faces[face_index*6+2]],      // vec(c,a)[0]
            precalc_vertices[2*faces[face_index*6]+1]-precalc_vertices[2*faces[face_index*6+2]+1]   // vec(c,a)[1]
        }; 
        float face_area = double_area_of_triangle( // Speichert doppelten Flächeninhalt von Fläche für Berechnung von uv-Koordinaten
            border_vectors[0], border_vectors[1], 
            border_vectors[2], border_vectors[3]
        );

        int32_t texture_offset = 0;     // Gibt Startposition zum Lesen aktueller Textur an
        if (texture_id >= 0) {
            for (int i=0; i < texture_id; i++) {    // Addiert Texturbreite * Texturhöhe aller vorhergehenden Texturen zu texture_offset
                texture_offset += texture_sizes[2*texture_id] * texture_sizes[2*texture_id+1];
            }
        }

        // Iteration über alle Pixel im kleinstmöglichen Rechteck um Fläche
        for (int x=(int) ceil(minx); x<maxx; x++) {
            for (int y=(int) ceil(miny); y<maxy; y++) {
                uint8_t pixel_inside_face = 1;          // Wahheitswert gibt an, ob Pixel innerhalb Fläche
                for (int vertex_index=0; vertex_index<3; vertex_index++) {      // Iteriert über Kanten der Fläche
                    int8_t new_orientation = sign_of_crossP_z(
                        border_vectors[2*vertex_index],
                        border_vectors[2*vertex_index+1],
                        x-precalc_vertices[2*faces[face_index*6+vertex_index]],         // vec(v,p)[0]  (v kann a, b oder c sein)
                        y-precalc_vertices[2*faces[face_index*6+vertex_index]+1]        // vec(v,p)[1]  (v kann a, b oder c sein)
                    );  // gibt an, auf welcher Seite der Kante sich der Punkt befindet
                    if (new_orientation == 1) {pixel_inside_face = 0; break;}   // Abbruch, sobald Pixel auf falscher Seite einer Kante
                }
                if (!pixel_inside_face) {   // Überspringen ungültiger Pixel
                    continue;
                }
                // Berechnung von baryzentrischen Koordinaten
                float w = double_area_of_triangle(
                        border_vectors[2],
                        border_vectors[3],
                        x-precalc_vertices[2*faces[face_index*6+1]],            // vec(b,p)[0]  
                        y-precalc_vertices[2*faces[face_index*6+1]+1]           // vec(b,p)[1] 
                    ) / face_area;
                float u = double_area_of_triangle(
                        border_vectors[4],
                        border_vectors[5],
                        x-precalc_vertices[2*faces[face_index*6+2]],            // vec(c,p)[0]  
                        y-precalc_vertices[2*faces[face_index*6+2]+1]           // vec(c,p)[1]  
                    ) / face_area;
                float v = double_area_of_triangle(
                        border_vectors[0],
                        border_vectors[1],
                        x-precalc_vertices[2*faces[face_index*6]],              // vec(a,p)[0]  
                        y-precalc_vertices[2*faces[face_index*6]+1]             // vec(a,p)[1]  
                    ) / face_area;
                // Berechnung des z-Werts des aktuellen Pixels mittels baryzentrischer Koordinaten
                float z_value = zcords[faces[face_index*6]] * w + zcords[faces[face_index*6]+1] * u + zcords[faces[face_index*6]+2] * v;
                
                if (z_value < zbuffer[y*width+x]) {
                    if (texture_id < 0) {                    // keine Textur verfügbar
                        zbuffer[y*width+x] = z_value;           // --> setzen des Pixels auf Farbe der Fläche
                        color_matrix[3*(y*width+x)] = colors[3*face_index];  
                        color_matrix[3*(y*width+x)+1] = colors[3*face_index+1]; 
                        color_matrix[3*(y*width+x)+2] = colors[3*face_index+2]; 
                    } else {                                // wenn Textur verfügbar
                        // Berechung von Textur-Koordinaten über baryzentrische Koordinaten
                        int32_t texture_x = (int32_t) roundl((w * uvcords[2*faces[6*face_index+3]] + u * uvcords[2*faces[6*face_index+4]] + v * uvcords[2*faces[6*face_index+5]]) * (texture_sizes[2*texture_id]-1));
                        int32_t texture_y = (int32_t) roundl((w*uvcords[2*faces[6*face_index+3]+1] + u*uvcords[2*faces[6*face_index+4]+1] + v*uvcords[2*faces[6*face_index+5]+1])*(texture_sizes[2*texture_id+1]-1));
                        // Auslesen der Textur-Farbwerte
                        uint8_t r = textures[3*(texture_offset+texture_y*texture_sizes[2*texture_id+1]+texture_x)];
                        uint8_t g = textures[3*(texture_offset+texture_y*texture_sizes[2*texture_id+1]+texture_x)+1];
                        uint8_t b = textures[3*(texture_offset+texture_y*texture_sizes[2*texture_id+1]+texture_x)+2];

                        // setzen des Pixels auf Textur-Farbwerte
                        color_matrix[3*(y*width+x)] = r;
                        color_matrix[3*(y*width+x)+1] = g;
                        color_matrix[3*(y*width+x)+2] = b;
                    }
                }
            }
        }
    }
    
}

// Funktion zum zurücksetzen des z-Buffers
void reset_zbuffer(float* zbuffer, uint8_t* color_matrix, int32_t width, int32_t height, float max_renderdistance, 
    uint8_t bgcolor_r, uint8_t bgcolor_g, uint8_t bgcolor_b) {
    // Parameter: zbuffer: Z-Buffer; color_matrix: Liste zur Zwischenspeicherung der Pixelfarben; width: Fensterbreite; height: Fensterhöhe
    //            max_renderdistance: maximale Rernderdistanz; bgcolor_r, bgcolor_g, bgcolor_b: rgb-Werte der Hintergrundfarbe

    // Iteration über alle Pixel des Fensters
    for (int x=0; x<width; x++) {
        for (int y=0; y<height; y++) {
            zbuffer[y*width+x] = max_renderdistance;    // Setzen des z-Buffers auf maximale Renderdistanz
            // Setzen der Farbmatrix auf Hintergrundfarbe
            color_matrix[(y*width+x)*3] = bgcolor_r;
            color_matrix[(y*width+x)*3+1] = bgcolor_g;
            color_matrix[(y*width+x)*3+2] = bgcolor_b;
        }
    }
}
