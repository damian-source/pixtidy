from flask import Flask, render_template, request, jsonify
import folium

app = Flask(__name__)

pins = []

@app.route('/')
def index():
    start_coords = (52.22977, 21.01178)
    mapa = folium.Map(location=start_coords, zoom_start=10)
    for pin in pins:
        folium.Marker(location=pin).add_to(mapa)
    mapa.get_root().html.add_child(folium.Element("""
        <script>
            function addPin(lat, lon) {
                $.post('/add_pin', {lat: lat, lon: lon}, function(data) {
                    location.reload();
                });
            }
            function removePins() {
                $.post('/remove_pins', function(data) {
                    location.reload();
                });
            }
            function printBounds(bounds) {
                var sw = bounds.getSouthWest();
                var ne = bounds.getNorthEast();
                console.log('SW:', sw.lat, sw.lng, 'NE:', ne.lat, ne.lng);
            }
        </script>
    """))
    mapa.save('templates/map.html')
    return render_template('index.html')

@app.route('/add_pin', methods=['POST'])
def add_pin():
    lat = float(request.form['lat'])
    lon = float(request.form['lon'])
    pins.append((lat, lon))
    return jsonify(success=True)

@app.route('/remove_pins', methods=['POST'])
def remove_pins():
    pins.clear()
    return jsonify(success=True)

if __name__ == '__main__':
    app.run(debug=True)
