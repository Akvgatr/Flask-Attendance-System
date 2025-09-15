from flask import Flask, request, render_template_string, jsonify
import requests

app = Flask(__name__)

@app.route('/')
def home():
    html = '''
    <!DOCTYPE html>
    <html>
    <head>
        <title>Proxy & Location Check</title>
    </head>
    <body>
        <h2>Proxy & Location Check</h2>
        <button onclick="getLocation()">Allow Location Access</button>

        <p id="status">Waiting for location...</p>
        <p>Latitude: <span id="lat">-</span></p>
        <p>Longitude: <span id="lon">-</span></p>

        <script>
        function getLocation() {
            if (navigator.geolocation) {
                navigator.geolocation.getCurrentPosition(
                    function(position) {
                        document.getElementById('lat').textContent = position.coords.latitude;
                        document.getElementById('lon').textContent = position.coords.longitude;
                        document.getElementById('status').textContent = "Location fetched successfully";

                        // Send location to backend
                        fetch('/verify', {
                            method: 'POST',
                            headers: { 'Content-Type': 'application/json' },
                            body: JSON.stringify({
                                latitude: position.coords.latitude,
                                longitude: position.coords.longitude
                            })
                        })
                        .then(response => response.json())
                        .then(data => {
                            alert("Proxy Detected: " + data.proxy + "\\nYour IP: " + data.ip + "\\nIP-Based Location: (" + data.ip_lat + ", " + data.ip_lon + ")");
                        });
                    },
                    function(error) {
                        document.getElementById('status').textContent = "Error: " + error.message;
                    }
                );
            } else {
                document.getElementById('status').textContent = "Geolocation is not supported by this browser.";
            }
        }
        </script>
    </body>
    </html>
    '''
    return render_template_string(html)

@app.route('/verify', methods=['POST'])
def verify():
    data = request.get_json()
    user_lat = data.get('latitude')
    user_lon = data.get('longitude')

    ip_address = requests.get('https://api.ipify.org').text

    url = f'http://ip-api.com/json/{ip_address}?fields=status,proxy,lat,lon'
    response = requests.get(url).json()

    proxy_status = response.get('proxy', False)
    ip_lat = response.get('lat', '-')
    ip_lon = response.get('lon', '-')

    return jsonify({
        'proxy': proxy_status,
        'ip': ip_address,
        'ip_lat': ip_lat,
        'ip_lon': ip_lon,
        'user_lat': user_lat,
        'user_lon': user_lon
    })

if __name__ == '__main__':
    app.run(debug=True)