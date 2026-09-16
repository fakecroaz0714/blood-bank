// BloodConnect Leaflet Interactive Map Module

let mapInstance = null;
let donorMarkersLayer = null;

function initDonorMap(elementId = 'donorMap', bloodGroup = '', city = '') {
    const mapElement = document.getElementById(elementId);
    if (!mapElement) return;

    // Center defaults around India (or Chennai/Bangalore)
    const defaultCenter = [13.0827, 80.2707];
    const defaultZoom = 6;

    if (!mapInstance) {
        mapInstance = L.map(elementId).setView(defaultCenter, defaultZoom);

        // OpenStreetMap Tile Layer
        L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
            attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors',
            maxZoom: 18
        }).addTo(mapInstance);

        donorMarkersLayer = L.layerGroup().addTo(mapInstance);
    } else {
        donorMarkersLayer.clearLayers();
    }

    // Fetch donor locations via API
    const url = `/api/donors/locations?blood_group=${encodeURIComponent(bloodGroup)}&city=${encodeURIComponent(city)}`;

    fetch(url)
        .then(res => res.json())
        .then(donors => {
            if (!donors || donors.length === 0) {
                console.log("No donor coordinates returned for map.");
                return;
            }

            const bounds = [];

            donors.forEach(donor => {
                if (!donor.latitude || !donor.longitude) return;

                const lat = parseFloat(donor.latitude);
                const lng = parseFloat(donor.longitude);
                bounds.push([lat, lng]);

                // Create custom blood drop marker
                const customIcon = L.divIcon({
                    className: 'custom-map-pin',
                    html: `
                        <div style="
                            background: ${donor.is_available ? '#dc2626' : '#64748b'};
                            color: white;
                            font-weight: 800;
                            font-size: 11px;
                            width: 32px;
                            height: 32px;
                            border-radius: 50% 50% 50% 0;
                            transform: rotate(-45deg);
                            display: flex;
                            align-items: center;
                            justify-content: center;
                            box-shadow: 0 3px 8px rgba(0,0,0,0.3);
                            border: 2px solid white;
                        ">
                            <span style="transform: rotate(45deg); display: block;">${donor.blood_group}</span>
                        </div>
                    `,
                    iconSize: [32, 32],
                    iconAnchor: [16, 32],
                    popupAnchor: [0, -30]
                });

                const marker = L.marker([lat, lng], { icon: customIcon });

                const popupContent = `
                    <div style="font-family: inherit; min-width: 180px;">
                        <div style="display: flex; align-items: center; gap: 8px; margin-bottom: 6px;">
                            <span style="background: #dc2626; color: white; padding: 2px 8px; border-radius: 6px; font-weight: bold; font-size: 12px;">${donor.blood_group}</span>
                            <strong style="font-size: 14px;">${donor.name}</strong>
                        </div>
                        <div style="font-size: 12px; color: #475569; margin-bottom: 4px;">
                            <i class="bi bi-geo-alt"></i> ${donor.city}${donor.address ? ', ' + donor.address : ''}
                        </div>
                        <div style="font-size: 12px; margin-bottom: 8px;">
                            Status: <span style="font-weight: 600; color: ${donor.is_available ? '#16a34a' : '#64748b'};">${donor.is_available ? 'Available' : 'Unavailable'}</span>
                        </div>
                        <a href="tel:${donor.phone}" class="btn btn-sm btn-danger text-white w-100 py-1" style="font-size: 11px; text-decoration: none;">
                            <i class="bi bi-telephone"></i> Call ${donor.phone}
                        </a>
                    </div>
                `;

                marker.bindPopup(popupContent);
                donorMarkersLayer.addLayer(marker);
            });

            // Adjust view to fit returned donors
            if (bounds.length > 0) {
                mapInstance.fitBounds(bounds, { padding: [40, 40], maxZoom: 13 });
            }
        })
        .catch(err => console.error("Error loading donor map markers:", err));
}

// Distance Calculation using Haversine formula (km)
function calculateHaversineDistance(lat1, lon1, lat2, lon2) {
    const R = 6371; // Earth radius in km
    const dLat = (lat2 - lat1) * Math.PI / 180;
    const dLon = (lon2 - lon1) * Math.PI / 180;
    const a = 
        Math.sin(dLat/2) * Math.sin(dLat/2) +
        Math.cos(lat1 * Math.PI / 180) * Math.cos(lat2 * Math.PI / 180) * 
        Math.sin(dLon/2) * Math.sin(dLon/2);
    const c = 2 * Math.atan2(Math.sqrt(a), Math.sqrt(1-a));
    return (R * c).toFixed(1);
}
