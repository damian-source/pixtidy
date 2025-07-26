from PyQt5.QtWidgets import QWidget, QVBoxLayout
from PyQt5.QtWebEngineWidgets import QWebEngineView
from PyQt5.QtWebChannel import QWebChannel
from PyQt5.QtCore import pyqtSignal, QObject, pyqtSlot


class MarkerManager(QObject):
    def __init__(self, view):
        super().__init__()
        self.view = view

    @pyqtSlot(list)
    def add_markers(self, coordinates):
        script = """
        if (typeof markers === 'undefined') {
            markers = [];
        } else {
            markers.forEach(marker => map.removeLayer(marker));
            markers = [];
        }
        var bounds = [];
        """
        for lat, lon in coordinates:
            script += f"""
            var marker = L.marker([{lat}, {lon}]).addTo(map);
            markers.push(marker);
            bounds.push([{lat}, {lon}]);
            """
        script += """
        if (bounds.length > 0) {
            var boundsGroup = L.featureGroup(markers);
            map.fitBounds(boundsGroup.getBounds());
        }
        """
        self.view.page().runJavaScript(script)

    @pyqtSlot()
    def clear_markers(self):
        script = """
        if (typeof markers !== 'undefined') {
            markers.forEach(marker => map.removeLayer(marker));
            markers = [];
        }
        """
        self.view.page().runJavaScript(script)


class RectangleManager(QObject):
    rectangle_selected = pyqtSignal(float, float, float, float)

    def __init__(self, timeline_widget):
        super().__init__()
        self.rectangle = None  # Zmieniamy na przechowywanie tylko jednego prostokąta
        self.timeline_widget = timeline_widget

    @pyqtSlot(float, float, float, float)
    def add_rectangle(self, lat1, lon1, lat2, lon2):
        # Nadpisujemy poprzedni prostokąt
        self.rectangle = (lat1, lon1, lat2, lon2)
        self.rectangle_selected.emit(lat1, lon1, lat2, lon2)

    @pyqtSlot()
    def clear_rectangles(self):
        # Czyszczenie prostokąta i resetowanie zaznaczeń
        self.rectangle = None
        self.rectangle_selected.emit(0, 0, 0, 0)
        self.timeline_widget.reset_event_colors()  # Przywrócenie domyślnych kolorów

    @pyqtSlot()
    def print_rectangles(self):
        # Zastępujemy debugowanie, jeśli niepotrzebne
        if self.rectangle:
            #print(f"Current rectangle: {self.rectangle}")
            pass
        else:
            #print("No rectangle selected.")
            pass


class MapWidget(QWidget):
    rectangle_selected = pyqtSignal(float, float, float, float)

    def __init__(self, timeline_widget, parent=None):
        super().__init__(parent)
        self.setWindowTitle("OpenStreetMap")
        self.setGeometry(100, 100, 800, 600)

        layout = QVBoxLayout()
        self.setLayout(layout)

        self.browser = QWebEngineView()
        self.browser.setHtml("""
        <!DOCTYPE html>
        <html>
        <head>
            <title>OpenStreetMap</title>
            <link rel="stylesheet" href="https://unpkg.com/leaflet@1.7.1/dist/leaflet.css" />
            <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/leaflet.draw/1.0.4/leaflet.draw.css"/>
            <script src="https://unpkg.com/leaflet@1.7.1/dist/leaflet.js"></script>
            <script src="https://cdnjs.cloudflare.com/ajax/libs/leaflet.draw/1.0.4/leaflet.draw.js"></script>
            <script src="qrc:///qtwebchannel/qwebchannel.js"></script>
            <style>
                body, html, #mapid { 
                    margin: 0; 
                    padding: 0; 
                    height: 100%; 
                }
                
                /* Obniżenie całej grupy przycisków o 50px */
                .leaflet-control {
                    margin-top: 50px !important;
                }
                
                /* Dostosowanie marginesów między poszczególnymi przyciskami */
                .leaflet-bar a {
                    margin-bottom: 5px !important;  /* Dodaje 5px przerwy między przyciskami */
                    margin-top: 0 !important;  /* Zmniejsza górny margines na 0 */
                }
                
                /* Dostosowanie przycisku "X", aby nie miał dodatkowych marginesów */
                .leaflet-control-custom {
                    margin-bottom: 0 !important;
                    margin-top: 0 !important;
                }

            </style>
        </head>
        <body>
            <div id="mapid"></div>
            <div id="internetWarning" style="display:none; position: absolute; top: 0; left: 0; width: 100%; background-color: red; color: white; text-align: center; font-weight: bold; padding: 5px; z-index: 1000;">
                No internet connection. Some parts of the map may not load.
            </div>
            <script>
                var map = L.map('mapid').setView([51.7592, 19.4560], 10);
                var tileLayer = L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
                    attribution: '© OpenStreetMap contributors',
                    maxZoom: 19,
                });
        
                var tileErrorCount = 0;  // Licznik błędów ładowania kafelków
                var hideWarningTimeout;  // Zmienna do timeoutu ukrywania komunikatu
        
                // Obsługa błędów ładowania kafelków (tileerror)
                tileLayer.on('tileerror', function() {
                    tileErrorCount++;
                    document.getElementById("internetWarning").style.display = 'block';
                    
                    // Jeśli wcześniej był ustawiony timeout, go usuwamy
                    if (hideWarningTimeout) {
                        clearTimeout(hideWarningTimeout);
                    }
                    
                    // Ustawiamy timeout na ukrycie komunikatu po 5 sekundach
                    hideWarningTimeout = setTimeout(function() {
                        document.getElementById("internetWarning").style.display = 'none';
                    }, 5000);
                });
        
                // Obsługa załadowania kafelków
                tileLayer.on('load', function() {
                    // Zmniejszamy licznik błędów (jeśli jest większy od 0)
                    if (tileErrorCount > 0) {
                        tileErrorCount--;
                    }
        
                    // Jeśli wszystkie kafelki zostały załadowane i nie ma więcej błędów, ukrywamy komunikat
                    if (tileErrorCount === 0 && hideWarningTimeout) {
                        clearTimeout(hideWarningTimeout);  // Usuwamy timeout
                        document.getElementById("internetWarning").style.display = 'none';
                    }
                });
        
                tileLayer.addTo(map);
        
                var markers = [];
                var rectangles = [];
        
                var drawnItems = new L.FeatureGroup();
                map.addLayer(drawnItems);
        
                // Konfiguracja rysowania prostokątów
                var drawControl = new L.Control.Draw({
                    edit: false,  // Wyłącz edytowanie
                    draw: {
                        polyline: false,
                        polygon: false,
                        circle: false,
                        marker: false,
                        circlemarker: false,
                        rectangle: true  // Rysowanie prostokątów
                    }
                });
                map.addControl(drawControl);
        
                // Obsługa dodawania prostokątów
                map.on(L.Draw.Event.CREATED, function (event) {
                    var layer = event.layer;
                    drawnItems.addLayer(layer);
                    rectangles.push(layer);
        
                    var bounds = layer.getBounds();
                    var southWest = bounds.getSouthWest();
                    var northEast = bounds.getNorthEast();
        
                    var lat1 = southWest.lat, lon1 = southWest.lng;
                    var lat2 = northEast.lat, lon2 = northEast.lng;
        
                    if (window.rectangleManager) {
                        window.rectangleManager.add_rectangle(lat1, lon1, lat2, lon2);
                    }
                });
        
                // Dodajemy ręczny przycisk do czyszczenia prostokątów z ikoną X i tooltipem
                var clearButton = L.Control.extend({
                    options: {
                        position: 'topleft'  // Ustawienie przycisku w lewym górnym rogu
                    },
                    onAdd: function () {
                        var container = L.DomUtil.create('div', 'leaflet-bar leaflet-control leaflet-control-custom');
        
                        container.title = "Clear All Rectangles";  // Dodajemy opis (tooltip)
                        container.style.backgroundColor = 'white';
                        container.style.width = '30px';
                        container.style.height = '30px';
                        container.style.display = 'flex';
                        container.style.alignItems = 'center';
                        container.style.justifyContent = 'center';
                        container.style.fontSize = '18px';  // Zwiększamy rozmiar "X"
                        container.style.fontWeight = 'bold';  // Dodajemy pogrubienie
                        container.style.cursor = 'pointer';  // Zmieniamy kursor na "rączkę"
        
                        container.innerHTML = '✖';  // Ustawiamy "X" jako zawartość przycisku
        
                        container.onclick = function () {
                            rectangles.forEach(rectangle => map.removeLayer(rectangle));
                            rectangles = [];
                            if (window.rectangleManager) {
                                window.rectangleManager.clear_rectangles();
                            }
                        };
        
                        return container;
                    }
                });
                map.addControl(new clearButton());
        
                new QWebChannel(qt.webChannelTransport, function(channel) {
                    window.markerManager = channel.objects.markerManager;
                    window.rectangleManager = channel.objects.rectangleManager;
                });
            </script>
        </body>
        </html>


        """)

        layout.addWidget(self.browser)

        self.channel = QWebChannel()
        self.marker_manager = MarkerManager(self.browser)
        self.rectangle_manager = RectangleManager(timeline_widget)
        self.rectangle_manager.rectangle_selected.connect(self.on_rectangle_selected)
        self.channel.registerObject('markerManager', self.marker_manager)
        self.channel.registerObject('rectangleManager', self.rectangle_manager)
        self.browser.page().setWebChannel(self.channel)

    def show_markers(self, df, scale_view=True):
        #print('MapWidget show_markers function')
        coordinates = []
        for index, row in df.iterrows():
            coords = row['Koordynaty'].split(', ')
            if len(coords) == 2:
                try:
                    lat, lon = float(coords[0]), float(coords[1])
                    coordinates.append((lat, lon))
                except ValueError:
                    continue  # Ignorujemy nieprawidłowe wartości współrzędnych

        # Składamy skrypt JavaScript do dodania znaczników
        script = """
        if (typeof markers === 'undefined') {
            markers = [];
        } else {
            markers.forEach(marker => map.removeLayer(marker));
            markers = [];
        }
        var bounds = [];
        """

        for lat, lon in coordinates:
            script += f"""
            var marker = L.marker([{lat}, {lon}]).addTo(map);
            markers.push(marker);
            bounds.push([{lat}, {lon}]);
            """

        # Przeskaluj mapę tylko wtedy, gdy scale_view == True
        if scale_view:
            script += """
            if (bounds.length > 0) {
                var boundsGroup = L.featureGroup(markers);
                map.fitBounds(boundsGroup.getBounds());
            }
            """

        self.browser.page().runJavaScript(script)  # Poprawione odwołanie do self.browser


    def on_rectangle_selected(self, lat1, lon1, lat2, lon2):
        self.rectangle_selected.emit(lat1, lon1, lat2, lon2)

    def clear_selection(self):
        script = """
        if (typeof rectangles !== 'undefined') {
            rectangles.forEach(rectangle => map.removeLayer(rectangle));
            rectangles = [];
        }
        """
        self.browser.page().runJavaScript(script)
        self.marker_manager.clear_markers()  # Dodano czyszczenie znaczników