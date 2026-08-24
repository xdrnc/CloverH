import { useState, useEffect } from "react";
import { useEventsWebSocket } from "./hooks/useEventsWebSocket";

const API_BASE = "/api";

function PatientSection({ patient }) {
  // Subscribe to this patient's events via WebSocket
  const { eventsByMrn, connected, error } = useEventsWebSocket([patient.mrn]);
  const events = eventsByMrn[patient.mrn] || [];

  const formatTimestamp = (iso) => {
    const d = new Date(iso);
    return d.toLocaleString();
  };

  return (
    <div className="patient-section">
      <div className="patient-header">
        <h2>{patient.first_name} {patient.last_name}</h2>
        <div className="meta">
          MRN: {patient.mrn} | DOB: {patient.date_of_birth} | Gender: {patient.gender}
          <span className={`ws-status ${connected ? "connected" : "disconnected"}`}>
            {connected ? "🟢 Live" : "🔴 Reconnecting..."}
          </span>
          {error && <span className="ws-error">⚠ {error}</span>}
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
  const [page, setPage] = useState(1);
  const [pageSize, setPageSize] = useState(3);
  const [total, setTotal] = useState(0);
  const [totalPages, setTotalPages] = useState(0);

  const fetchPatients = () => {
    setLoading(true);
    fetch(`${API_BASE}/patients2?page=${page}&pageSize=${pageSize}`)
      .then((res) => res.json())
      .then((data) => {
        setPatients(data.patients);
        setTotal(data.total);
        setTotalPages(data.totalPages);
        setLoading(false);
      })
      .catch((err) => {
        console.error("Failed to fetch patients:", err);
        setLoading(false);
      });
  };

  useEffect(() => {
    fetchPatients();
  }, [page, pageSize]);

  const goToPage = (newPage) => {
    if (newPage >= 1 && newPage <= totalPages) {
      setPage(newPage);
    }
  };

  const changePageSize = (newSize) => {
    setPageSize(newSize);
    setPage(1); // Reset to first page when changing page size
  };

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

      {/* Pagination Controls */}
      {!loading && totalPages > 1 && (
        <div className="pagination">
          <div className="pagination-info">
            Page {page} of {totalPages} — {total} total patients
          </div>
          <div className="pagination-controls">
            <select
              value={pageSize}
              onChange={(e) => changePageSize(Number(e.target.value))}
              className="page-size-select"
            >
              <option value={3}>3 per page</option>
              <option value={5}>5 per page</option>
              <option value={10}>10 per page</option>
              <option value={20}>20 per page</option>
            </select>
            <button
              onClick={() => goToPage(page - 1)}
              disabled={page === 1}
              className="page-btn"
            >
              ← Previous
            </button>
            <span className="page-indicator">
              {Array.from({ length: totalPages }, (_, i) => i + 1)
                .map((p) => (
                  <button
                    key={p}
                    onClick={() => goToPage(p)}
                    className={`page-number ${p === page ? "active" : ""}`}
                  >
                    {p}
                  </button>
                ))}
            </span>
            <button
              onClick={() => goToPage(page + 1)}
              disabled={page === totalPages}
              className="page-btn"
            >
              Next →
            </button>
          </div>
        </div>
      )}
    </div>
  );
}

export default App;
