import { useState, useEffect } from "react";

const API_BASE = "/api";

function PatientSection({ patient }) {
  const [events, setEvents] = useState([]);

  const fetchEvents = () => {
    fetch(`${API_BASE}/patients/${patient.mrn}/events`)
      .then((res) => res.json())
      .then((data) => setEvents(data));
  };

  useEffect(() => {
    fetchEvents();
    const interval = setInterval(fetchEvents, 5000);
    return () => clearInterval(interval);
  }, [patient.mrn]);

  const formatTimestamp = (iso) => {
    const d = new Date(iso);
    return d.toLocaleString();
  };

  return (
    <div className="patient-section">
      <div className="patient-header">
        <h2>
          {patient.first_name} {patient.last_name}
        </h2>
        <div className="meta">
          MRN: {patient.mrn} | DOB: {patient.date_of_birth} | Gender:{" "}
          {patient.gender}
        </div>
      </div>

      {events.length === 0 ? (
        <div className="empty-state">No ADT events found for this patient.</div>
      ) : (
        <table className="events-table">
          <thead>
            <tr>
              <th>Event</th>
              <th>Description</th>
              <th>Timestamp</th>
              <th>Location</th>
              <th>Facility</th>
            </tr>
          </thead>
          <tbody>
            {events.map((e) => (
              <tr key={e.id}>
                <td>
                  <span className={`event-type ${e.event_type}`}>
                    {e.event_type}
                  </span>
                </td>
                <td>{e.event_description}</td>
                <td>{formatTimestamp(e.event_timestamp)}</td>
                <td>{e.patient_location || "—"}</td>
                <td>{e.sending_facility || "—"}</td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
    </div>
  );
}

function App() {
  const [patients, setPatients] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetch(`${API_BASE}/patients`)
      .then((res) => res.json())
      .then((data) => {
        setPatients(data);
        setLoading(false);
      });
  }, []);

  return (
    <div className="app">
      <h1>ADT Feed Viewer</h1>

      {loading && <div className="loading">Loading patients...</div>}

      {!loading && patients.length === 0 && (
        <div className="empty-state">No patients found. Run the ingestion script to load data.</div>
      )}

      {patients.map((p) => (
        <PatientSection key={p.mrn} patient={p} />
      ))}
    </div>
  );
}

export default App;
