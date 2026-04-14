import { useState, useEffect } from 'react';
import { MapContainer, TileLayer, CircleMarker, Popup } from 'react-leaflet';
import 'leaflet/dist/leaflet.css';
import { getAreaStatus } from '../api';

// Bangalore center coordinates
const BANGALORE_CENTER = [12.9716, 77.5946];
const ZOOM = 12;

const STATUS_COLORS = {
  outage: '#b53333',
  warning: '#c96442',
  normal: '#4a7c59',
};

const STATUS_RADIUS = {
  outage: 14,
  warning: 11,
  normal: 8,
};

export default function LiveHeatmap() {
  const [areas, setAreas] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    loadAreas();
    const interval = setInterval(loadAreas, 60000);
    return () => clearInterval(interval);
  }, []);

  async function loadAreas() {
    try {
      const data = await getAreaStatus();
      setAreas(data);
    } catch (err) {
      console.error('Failed to load area status:', err);
    } finally {
      setLoading(false);
    }
  }

  // Filter out areas without coordinates
  const mappableAreas = areas.filter(
    (a) => a.latitude && a.longitude
  );

  return (
    <div className="panel">
      <div className="panel-header">
        <div className="panel-title">
          <span className="panel-icon">M</span>
          Live Outage Map
        </div>
        <div style={{ display: 'flex', gap: '12px', alignItems: 'center' }}>
          <span style={{ display: 'flex', alignItems: 'center', gap: '4px', fontSize: '12px', color: 'var(--stone-gray)' }}>
            <span style={{ width: 8, height: 8, borderRadius: '50%', background: STATUS_COLORS.normal, display: 'inline-block' }} />
            Normal
          </span>
          <span style={{ display: 'flex', alignItems: 'center', gap: '4px', fontSize: '12px', color: 'var(--stone-gray)' }}>
            <span style={{ width: 8, height: 8, borderRadius: '50%', background: STATUS_COLORS.warning, display: 'inline-block' }} />
            Warning
          </span>
          <span style={{ display: 'flex', alignItems: 'center', gap: '4px', fontSize: '12px', color: 'var(--stone-gray)' }}>
            <span style={{ width: 8, height: 8, borderRadius: '50%', background: STATUS_COLORS.outage, display: 'inline-block' }} />
            Outage
          </span>
        </div>
      </div>

      <div className="map-container">
        {loading ? (
          <div className="empty-state" style={{ height: '100%', display: 'flex', flexDirection: 'column', justifyContent: 'center' }}>
            <p>Loading map data...</p>
          </div>
        ) : (
          <MapContainer
            center={BANGALORE_CENTER}
            zoom={ZOOM}
            scrollWheelZoom={true}
            style={{ height: '100%', width: '100%' }}
          >
            <TileLayer
              attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OSM</a>'
              url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
            />
            {mappableAreas.map((area) => (
              <CircleMarker
                key={area.id || area.name}
                center={[area.latitude, area.longitude]}
                radius={STATUS_RADIUS[area.status] || 8}
                fillColor={STATUS_COLORS[area.status] || STATUS_COLORS.normal}
                fillOpacity={area.status === 'outage' ? 0.7 : 0.5}
                color={STATUS_COLORS[area.status] || STATUS_COLORS.normal}
                weight={2}
              >
                <Popup>
                  <div>
                    <strong style={{ fontSize: '14px' }}>{area.name}</strong>
                    <br />
                    <span style={{ fontSize: '12px', color: '#5e5d59' }}>
                      {area.zone} Zone &middot; {area.pincode}
                    </span>
                    <br />
                    <span style={{
                      fontSize: '12px',
                      fontWeight: 600,
                      color: STATUS_COLORS[area.status],
                      textTransform: 'uppercase',
                    }}>
                      {area.status}
                    </span>
                    {area.active_outage_count > 0 && (
                      <span style={{ fontSize: '12px', color: '#5e5d59' }}>
                        {' '}&middot; {area.active_outage_count} active
                      </span>
                    )}
                  </div>
                </Popup>
              </CircleMarker>
            ))}
          </MapContainer>
        )}
      </div>
    </div>
  );
}
