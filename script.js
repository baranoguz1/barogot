// Global map değişkenleri
let map;
let directionsService;
let directionsRenderer;

function initMap() {
    const istanbul = { lat: 41.0082, lng: 28.9784 };
    map = new google.maps.Map(document.getElementById("map_canvas"), {
        zoom: 11,
        center: istanbul,
        mapTypeControl: false,
        streetViewControl: false
    });
    new google.maps.TrafficLayer().setMap(map);
    directionsService = new google.maps.DirectionsService();
    directionsRenderer = new google.maps.DirectionsRenderer({ map: map, suppressMarkers: false });

    // Sayfa yüklenirken tema kontrolü yapıp haritayı ayarla
    if (document.body.classList.contains('dark-mode')) {
        setDarkMapStyle();
    }
}

function useCurrentLocation() {
    if (navigator.geolocation) {
        navigator.geolocation.getCurrentPosition(pos => {
            document.getElementById("start_location").value = `${pos.coords.latitude},${pos.coords.longitude}`;
        }, err => alert("Konum alınamadı: " + err.message));
    } else {
        alert("Tarayıcınız konum servisini desteklemiyor.");
    }
}

function calculateAndDisplayRoute() {
    const start = document.getElementById("start_location").value.trim();
    const end = document.getElementById("end_location").value.trim();
    if (!start || !end) {
        alert("Başlangıç ve varış noktalarını girin.");
        return;
    }

    directionsService.route({
        origin: start,
        destination: end,
        travelMode: google.maps.TravelMode.DRIVING,
        drivingOptions: {
            departureTime: new Date(),
            trafficModel: 'bestguess'
        }
    }, (response, status) => {
        if (status === "OK") {
            directionsRenderer.setDirections(response);
            const leg = response.routes[0].legs[0];
            let info = `Mesafe: ${leg.distance.text}, Süre: ${leg.duration.text}`;
            if (leg.duration_in_traffic) {
                info += ` (Trafikle: ${leg.duration_in_traffic.text})`;
            }
            document.getElementById("route-info").innerHTML = info;
        } else {
            alert("Yol tarifi alınamadı: " + status);
        }
    });
}

function setDarkMapStyle() {
    if (map) {
        const darkStyle = [
            { elementType: "geometry", stylers: [{ color: "#242f3e" }] },
            { elementType: "labels.text.stroke", stylers: [{ color: "#242f3e" }] },
            { elementType: "labels.text.fill", stylers: [{ color: "#746855" }] },
            { featureType: "administrative.locality", elementType: "labels.text.fill", stylers: [{ color: "#d59563" }] },
            { featureType: "poi", elementType: "labels.text.fill", stylers: [{ color: "#d59563" }] },
            { featureType: "poi.park", elementType: "geometry", stylers: [{ color: "#263c3f" }] },
            { featureType: "poi.park", elementType: "labels.text.fill", stylers: [{ color: "#6b9a76" }] },
            { featureType: "road", elementType: "geometry", stylers: [{ color: "#38414e" }] },
            { featureType: "road", elementType: "geometry.stroke", stylers: [{ color: "#212a37" }] },
            { featureType: "road", elementType: "labels.text.fill", stylers: [{ color: "#9ca5b3" }] },
            { featureType: "road.highway", elementType: "geometry", stylers: [{ color: "#746855" }] },
            { featureType: "road.highway", elementType: "geometry.stroke", stylers: [{ color: "#1f2835" }] },
            { featureType: "road.highway", elementType: "labels.text.fill", stylers: [{ color: "#f3d19c" }] },
            { featureType: "transit", elementType: "geometry", stylers: [{ color: "#2f3948" }] },
            { featureType: "transit.station", elementType: "labels.text.fill", stylers: [{ color: "#d59563" }] },
            { featureType: "water", elementType: "geometry", stylers: [{ color: "#17263c" }] },
            { featureType: "water", elementType: "labels.text.fill", stylers: [{ color: "#515c6d" }] },
            { featureType: "water", elementType: "labels.text.stroke", stylers: [{ color: "#17263c" }] }
        ];
        map.setOptions({ styles: darkStyle });
    }
}

function setDefaultMapStyle() {
    if (map) {
        map.setOptions({ styles: null });
    }
}

// Tema Değiştirme Mantığı
document.addEventListener("DOMContentLoaded", function () {
    const toggleButton = document.querySelector(".toggle-button");
    const body = document.body;

    if (localStorage.getItem("darkMode") === "enabled") {
        body.classList.add("dark-mode");
        toggleButton.textContent = "☀️";
    } else {
        toggleButton.textContent = "🌙";
    }

    let busy = false;
    function toggleDarkMode(event) {
        event.preventDefault();
        if (busy) return;
        busy = true;

        body.classList.toggle("dark-mode");
        if (body.classList.contains("dark-mode")) {
            localStorage.setItem("darkMode", "enabled");
            toggleButton.textContent = "☀️";
            if (typeof setDarkMapStyle === 'function') setDarkMapStyle();
        } else {
            localStorage.setItem("darkMode", "disabled");
            toggleButton.textContent = "🌙";
            if (typeof setDefaultMapStyle === 'function') setDefaultMapStyle();
        }
        setTimeout(() => { busy = false; }, 200);
    }
    toggleButton.addEventListener("click", toggleDarkMode);
    toggleButton.addEventListener("touchstart", toggleDarkMode, { passive: false });
});