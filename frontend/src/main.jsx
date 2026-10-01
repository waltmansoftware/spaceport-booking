import React, { useEffect, useState } from "react";
import { createRoot } from "react-dom/client";
import { centralISO, clock, dayLabel, isPast, localDate, today } from "./time";
import "./style.css";

async function api(path, options = {}) {
  const response = await fetch(`/api/${path}`, options);
  let data;
  try {
    data = await response.json();
  } catch {
    throw new Error("The server could not be reached. Please try again.");
  }
  if (!response.ok) {
    const message =
      typeof data === "object"
        ? Object.entries(data)
            .map(
              ([key, value]) =>
                `${["detail", "non_field_errors"].includes(key) ? "" : `${key}: `}${[].concat(value).join(" ")}`,
            )
            .join(" ")
        : String(data);
    throw new Error(message || "Request failed. Please try again.");
  }
  return data;
}

function App() {
  const [screen, setScreen] = useState("charter");
  const [ships, setShips] = useState([]);
  const [shipId, setShipId] = useState("");
  const [date, setDate] = useState(today);
  const [start, setStart] = useState("09:00");
  const [end, setEnd] = useState("10:00");
  const [pilot, setPilot] = useState("");
  const [availability, setAvailability] = useState(null);
  const [availabilityError, setAvailabilityError] = useState("");
  const [fleet, setFleet] = useState(null);
  const [fleetError, setFleetError] = useState("");
  const [fleetDate, setFleetDate] = useState("");
  const [message, setMessage] = useState("");
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);
  const [revision, setRevision] = useState(0);
  const [shipError, setShipError] = useState("");

  useEffect(() => {
    let active = true;
    setShipError("");
    api("ships")
      .then((data) => {
        if (active) {
          setShips(data);
          setShipId((current) => current || String(data[0]?.id || ""));
        }
      })
      .catch((e) => {
        if (active) setShipError(e.message);
      });
    return () => {
      active = false;
    };
  }, [revision]);

  useEffect(() => {
    let active = true;
    setAvailability(null);
    setAvailabilityError("");
    if (shipId && date) {
      api(
        `bookings/unavailable?ship_id=${encodeURIComponent(shipId)}&date=${encodeURIComponent(date)}`,
      )
        .then((data) => {
          if (active) setAvailability(data);
        })
        .catch((e) => {
          if (active) setAvailabilityError(e.message);
        });
    }
    return () => {
      active = false;
    };
  }, [shipId, date, revision]);

  useEffect(() => {
    if (screen !== "fleet") return;
    let active = true;
    setFleet(null);
    setFleetError("");
    api("dashboard")
      .then((data) => {
        if (active) setFleet(data);
      })
      .catch((e) => {
        if (active) setFleetError(e.message);
      });
    return () => {
      active = false;
    };
  }, [screen, revision]);

  async function book(event) {
    event.preventDefault();
    setError("");
    setMessage("");
    if (end <= start) {
      setError("End time must be after start time.");
      return;
    }
    if (isPast(date, start)) {
      setError("Bookings cannot start in the past.");
      return;
    }
    setBusy(true);
    try {
      const result = await api("bookings", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          shipId: Number(shipId),
          pilotName: pilot,
          startTime: centralISO(date, start),
          endTime: centralISO(date, end),
        }),
      });
      setMessage(
        `Booking #${result.id} confirmed for ${dayLabel(result.startTime)}, ${clock(result.startTime)}–${clock(result.endTime)} Central.`,
      );
    } catch (e) {
      setError(e.message);
    } finally {
      setBusy(false);
      setRevision((value) => value + 1);
    }
  }

  function openSchedule(booking) {
    setShipId(String(booking.shipId));
    setDate(localDate(booking.startTime));
    setError("");
    setMessage("");
    setScreen("charter");
    setRevision((value) => value + 1);
    window.scrollTo({ top: 0, behavior: "instant" });
  }

  const currentAvailability =
    availability?.shipId === Number(shipId) && availability?.date === date
      ? availability
      : null;
  const selectedShip = ships.find((ship) => ship.id === Number(shipId));

  return (
    <div className="app">
      <header>
        <a
          className="brand"
          href="#"
          onClick={(e) => {
            e.preventDefault();
            setScreen("charter");
          }}
        >
          <span className="brand-mark" aria-hidden="true">
            ✦
          </span>
          <span>
            PACIFIC<span className="brand-sub">SPACEPORT DISPATCH</span>
          </span>
        </a>
        <span className="status">
          <i /> FLEET OPERATIONS
        </span>
      </header>
      <nav aria-label="Main navigation">
        <button
          aria-current={screen === "charter" ? "page" : undefined}
          onClick={() => setScreen("charter")}
        >
          Charter a ship
        </button>
        <button
          aria-current={screen === "fleet" ? "page" : undefined}
          onClick={() => setScreen("fleet")}
        >
          Fleet manager
        </button>
      </nav>
      <main>
        <div className="page-heading">
          <div>
            <p className="eyebrow">
              {screen === "charter"
                ? "PLAN YOUR NEXT DEPARTURE"
                : "THE COMPLETE FLIGHT LOG"}
            </p>
            <h1>
              {screen === "charter"
                ? "Your next frontier awaits."
                : "Fleet manager."}
            </h1>
            <p>
              {screen === "charter"
                ? "Choose your ship. Find an open window. Make it official."
                : "Every charter, organized by ship. All times are Central."}
            </p>
          </div>
          <div className="hours">
            <span>SPACEPORT HOURS</span>
            <strong>06:00 — 22:00</strong>
            <small>Central Time · Every day</small>
          </div>
        </div>
        {shipError && (
          <div className="notice error" role="alert">
            Could not load ships: {shipError}{" "}
            <button onClick={() => setRevision((v) => v + 1)}>Retry</button>
          </div>
        )}
        {screen === "charter" ? (
          <div className="booking-layout">
            <section className="panel">
              <div className="panel-heading">
                <span className="step">01</span>
                <h2>Arrange a charter</h2>
              </div>
              <form onSubmit={book}>
                <fieldset disabled={busy || !ships.length}>
                  <label>
                    Spacecraft
                    <select
                      value={shipId}
                      onChange={(e) => {
                        setShipId(e.target.value);
                        setMessage("");
                        setError("");
                      }}
                      required
                    >
                      {ships.length ? (
                        ships.map((ship) => (
                          <option key={ship.id} value={ship.id}>
                            {ship.name}
                          </option>
                        ))
                      ) : (
                        <option value="">No ships loaded</option>
                      )}
                    </select>
                  </label>
                  <label>
                    Departure date <span className="hint">Central Time</span>
                    <input
                      type="date"
                      min={today()}
                      value={date}
                      onChange={(e) => {
                        setDate(e.target.value);
                        setMessage("");
                        setError("");
                      }}
                      required
                    />
                  </label>
                  <div className="time-inputs">
                    <label>
                      Start time
                      <input
                        type="time"
                        min="06:00"
                        max="21:59"
                        step="60"
                        value={start}
                        onChange={(e) => setStart(e.target.value)}
                        required
                      />
                    </label>
                    <label>
                      End time
                      <input
                        type="time"
                        min="06:01"
                        max="22:00"
                        step="60"
                        value={end}
                        onChange={(e) => setEnd(e.target.value)}
                        required
                      />
                    </label>
                  </div>
                  <label>
                    Pilot name
                    <input
                      value={pilot}
                      maxLength={255}
                      onChange={(e) => setPilot(e.target.value)}
                      placeholder="e.g. Ellen Ripley"
                      required
                    />
                  </label>
                  <p className="form-note">
                    Allow 30 minutes between charters for refueling. Your entire
                    flight must fit within spaceport hours.
                  </p>
                  <button
                    className="primary"
                    disabled={!currentAvailability || busy}
                    type="submit"
                  >
                    {busy ? "Confirming…" : "Confirm charter"}{" "}
                    <span aria-hidden="true">↗</span>
                  </button>
                </fieldset>
              </form>
              {error && (
                <p className="notice error" role="alert">
                  {error}
                </p>
              )}
              {message && (
                <p className="notice success" role="status">
                  {message}
                </p>
              )}
              {!shipError && !ships.length && (
                <p className="form-note">
                  Waiting for fleet data. If the fleet is empty, load the
                  provided seed data.
                </p>
              )}
            </section>
            <section className="panel availability">
              <div className="panel-heading">
                <span className="step">02</span>
                <h2>Check the flight window</h2>
              </div>
              <div className="ship-heading">
                <span className="eyebrow">SELECTED SPACECRAFT</span>
                <h3>{selectedShip?.name || "Select a ship"}</h3>
                <p>
                  {date ? dayLabel(`${date}T12:00:00`) : "Choose a date"} ·
                  Central Time
                </p>
              </div>
              {availabilityError ? (
                <p className="notice error" role="alert">
                  {availabilityError}{" "}
                  <button onClick={() => setRevision((v) => v + 1)}>
                    Retry
                  </button>
                </p>
              ) : !currentAvailability ? (
                <p role="status">
                  {shipId && date
                    ? "Loading availability…"
                    : "Select a ship and date to see availability."}
                </p>
              ) : (
                <>
                  <div className="availability-title">
                    <h3>Unavailable windows</h3>
                    <span className="badge">Includes refueling</span>
                  </div>
                  {currentAvailability.unavailableSlots.length ? (
                    <>
                      <ul className="slots">
                        {currentAvailability.unavailableSlots.map((slot) => (
                          <li key={slot.start}>
                            <span className="slot-dot" />
                            <strong>
                              {clock(slot.start)} — {clock(slot.end)}
                            </strong>
                            <span>Unavailable</span>
                          </li>
                        ))}
                      </ul>
                      <h3 className="schedule-title">Flights and refueling</h3>
                      <ul className="day-schedule" aria-label="Day schedule">
                        {currentAvailability.schedule.map((flight) => (
                          <li key={flight.bookingId}>
                            <strong>
                              {clock(flight.start)} — {clock(flight.end)}
                            </strong>
                            <span>
                              {flight.pilotName} · Booking #{flight.bookingId}
                            </span>
                            <small>
                              {flight.refueling
                                ? `Refueling ${clock(flight.refueling.start)} — ${clock(flight.refueling.end)}`
                                : "Refueling follows after closing."}
                            </small>
                          </li>
                        ))}
                      </ul>
                    </>
                  ) : (
                    <div className="empty">
                      <span aria-hidden="true">✧</span>
                      <h3>Clear for departure.</h3>
                      <p>No bookings or refueling windows on this date.</p>
                      <button className="secondary" onClick={() => setScreen("fleet")}>
                        Browse booked dates
                      </button>
                    </div>
                  )}
                  <div className="availability-footer">
                    Book outside these windows, between{" "}
                    {clock(currentAvailability.opensAt)} and{" "}
                    {clock(currentAvailability.closesAt)}. You may depart when
                    a blocked window ends. Return at least 30 minutes before
                    the next flight to allow your own refueling.
                  </div>
                </>
              )}
            </section>
          </div>
        ) : (
          <section>
            <div className="fleet-toolbar">
              <label>
                Filter by Central date
                <input
                  type="date"
                  value={fleetDate}
                  onChange={(e) => setFleetDate(e.target.value)}
                />
              </label>
              <button className="secondary" onClick={() => setFleetDate("")}>
                Show all dates
              </button>
              <button
                className="secondary"
                onClick={() => setRevision((v) => v + 1)}
              >
                Refresh
              </button>
            </div>
            {fleetError ? (
              <p className="notice error" role="alert">
                {fleetError}
              </p>
            ) : !fleet ? (
              <p role="status">Loading flight log…</p>
            ) : (
              <>
                <p className="log-count">
                  {fleetDate
                    ? `Flights on ${fleetDate}`
                    : "All dates, including seeded history"}{" "}
                  · {fleet.ships.length} ships
                </p>
                {fleet.ships.map((ship) => {
                  const bookings = fleet.bookings.filter(
                    (b) =>
                      b.shipId === ship.id &&
                      (!fleetDate || localDate(b.startTime) === fleetDate),
                  );
                  return (
                    <article className="panel fleet-panel" key={ship.id}>
                      <div className="fleet-heading">
                        <h2>{ship.name}</h2>
                        <span className="badge">
                          {bookings.length} charters
                        </span>
                      </div>
                      {bookings.length ? (
                        <div className="table-scroll">
                          <table>
                            <thead>
                              <tr>
                                <th>Date</th>
                                <th>Pilot</th>
                                <th>Departure</th>
                                <th>Return</th>
                                <th>Booking</th>
                                <th>Schedule</th>
                              </tr>
                            </thead>
                            <tbody>
                              {bookings.map((b) => (
                                <tr key={b.id}>
                                  <td>{dayLabel(b.startTime)}</td>
                                  <td>{b.pilotName}</td>
                                  <td>{clock(b.startTime)}</td>
                                  <td>{clock(b.endTime)}</td>
                                  <td>#{b.id}</td>
                                  <td>
                                    <button
                                      className="secondary"
                                      onClick={() => openSchedule(b)}
                                      aria-label={`Open schedule for booking ${b.id}`}
                                    >
                                      Open schedule
                                    </button>
                                  </td>
                                </tr>
                              ))}
                            </tbody>
                          </table>
                        </div>
                      ) : (
                        <p className="form-note">
                          No charters{fleetDate ? " on this date" : ""}.
                        </p>
                      )}
                    </article>
                  );
                })}
                {!fleet.ships.length && <p>No ships are loaded yet.</p>}
              </>
            )}
          </section>
        )}
      </main>
      <footer>
        <span>PACIFIC SPACEPORT</span>
        <span>
          All schedules use America/Chicago, including daylight saving time.
        </span>
      </footer>
    </div>
  );
}

createRoot(document.getElementById("root")).render(
  <React.StrictMode>
    <App />
  </React.StrictMode>,
);
