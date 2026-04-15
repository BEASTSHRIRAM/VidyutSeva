import { useState, useEffect, Fragment } from 'react';
import { MapContainer, TileLayer, CircleMarker, Popup } from 'react-leaflet';
import 'leaflet/dist/leaflet.css';
import { getAreaStatus, getLiveOutages } from '../api';

// Bangalore center coordinates
const BANGALORE_CENTER = [12.9716, 77.5946];
const ZOOM = 12;

const STATUS_COLORS = {
  outage: '#f87171', // Brighter red for dark mode
  warning: '#fbbf24', // Amber
  normal: '#10b981', // Emerald
  report: '#60a5fa', // Bright Blue
};

const STATUS_RADIUS = {
  outage: 14,
  warning: 11,
  normal: 8,
};

export default function LiveHeatmap() {
  const [areas, setAreas] = useState([]);
  const [reports, setReports] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    loadAreas();
    const interval = setInterval(loadAreas, 60000);
    return () => clearInterval(interval);
  }, []);

  async function loadAreas() {
    try {
      const [areasData, liveData] = await Promise.all([
        getAreaStatus(),
        getLiveOutages()
      ]);
      setAreas(areasData);
      setReports(liveData.crowd_reports || []);
    } catch (err) {
      console.error('Failed to load map data:', err);
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
      </div>

      <div className="map-container">
        {/* Map Legend Overlay */}
        <div className="map-legend-glass">
          <div className="legend-item">
            <span className="legend-dot" style={{ background: STATUS_COLORS.normal }} />
            Normal
          </div>
          <div className="legend-item">
            <span className="legend-dot" style={{ background: STATUS_COLORS.warning }} />
            Warning
          </div>
          <div className="legend-item">
            <span className="legend-dot" style={{ background: STATUS_COLORS.outage }} />
            Outage
          </div>
          <div className="legend-item">
            <span className="legend-dot" style={{ background: STATUS_COLORS.report }} />
            X Reports
          </div>
        </div>

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
              attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OSM</a> &copy; <a href="https://carto.com/attributions">CARTO</a>'
              url="https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png"
            />
            {mappableAreas.map((area) => (
              <Fragment key={area.id || area.name}>
                {/* Heat Glow Layer (only for active outages) */}
                {area.status === 'outage' && (
                  <CircleMarker
                    center={[area.latitude, area.longitude]}
                    radius={STATUS_RADIUS.outage * 2}
                    fillColor={STATUS_COLORS.outage}
                    fillOpacity={0.15}
                    stroke={false}
                    pathOptions={{ interactive: false }}
                  />
                )}
                <CircleMarker
                  center={[area.latitude, area.longitude]}
                  radius={STATUS_RADIUS[area.status] || 8}
                  fillColor={STATUS_COLORS[area.status] || STATUS_COLORS.normal}
                  fillOpacity={area.status === 'outage' ? 0.8 : 0.6}
                  color={area.status === 'outage' ? '#ffffff' : (STATUS_COLORS[area.status] || STATUS_COLORS.normal)}
                  weight={area.status === 'outage' ? 2 : 1}
                  pathOptions={{ className: area.status === 'outage' ? 'outage-marker-pulse' : '' }}
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
                </Fragment>
            ))}

            {/* Render Crowd Reports (Twitter) as small glowing markers offset slightly */}
            {reports.map((report, idx) => {
              const matchedArea = mappableAreas.find(a => a.name.toLowerCase() === report.area_name.toLowerCase());
              if (!matchedArea) return null;
              
              // Slight offset so they don't exactly overlap the main area marker
              const lat = matchedArea.latitude + (Math.random() * 0.006 - 0.003);
              const lng = matchedArea.longitude + (Math.random() * 0.006 - 0.003);
              
              return (
                <CircleMarker
                  key={`report-${idx}`}
                  center={[lat, lng]}
                  radius={5}
                  fillColor={STATUS_COLORS.report}
                  fillOpacity={0.8}
                  color="#ffffff"
                  weight={1}
                  pathOptions={{ className: 'report-marker-pulse' }}
                >
                  <Popup>
                    <div>
                      <strong style={{ fontSize: '13px', color: STATUS_COLORS.report }}>
                        X/Twitter Report ({report.area_name})
                      </strong>
                      <br />
                      <span style={{ fontSize: '12px', color: '#5e5d59' }}>
                        {report.description}
                      </span>
                    </div>
                  </Popup>
                </CircleMarker>
              );
            })}
          </MapContainer>
        )}
      </div>
    </div>
  );
}
