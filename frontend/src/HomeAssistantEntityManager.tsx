import { useEffect, useMemo, useState } from "react";
import {
  getHomeAssistantEntities,
  updateHomeAssistantEntity,
  type HomeAssistantEntity,
} from "./api";

const PAGE_SIZE = 15;

export function HomeAssistantEntityManager() {
  const [entities, setEntities] = useState<HomeAssistantEntity[]>([]);
  const [query, setQuery] = useState("");
  const [domain, setDomain] = useState("all");
  const [status, setStatus] = useState("all");
  const [page, setPage] = useState(1);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [notice, setNotice] = useState("");
  const [busy, setBusy] = useState<string | null>(null);
  const [selected, setSelected] = useState<string[]>([]);
  const [bulkBusy, setBulkBusy] = useState(false);
  const [bulkRoom, setBulkRoom] = useState("");
  const [newRoomFor, setNewRoomFor] = useState<string | null>(null);
  const [newRoom, setNewRoom] = useState("");

  async function refresh() {
    setLoading(true);
    setError("");
    try {
      setEntities(await getHomeAssistantEntities());
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : "Could not load entities.");
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    void refresh();
  }, []);

  const domains = useMemo(
    () => [...new Set(entities.map((entity) => entity.domain))].sort(),
    [entities],
  );

  const rooms = useMemo(
    () => [...new Set(entities.map((entity) => entity.room).filter((room): room is string => Boolean(room)))].sort(),
    [entities],
  );

  const enabledCount = entities.filter((entity) => entity.enabled).length;

  const filtered = useMemo(() => {
    const search = query.trim().toLowerCase();
    return entities.filter((entity) => {
      if (domain !== "all" && entity.domain !== domain) return false;
      if (status === "enabled" && !entity.enabled) return false;
      if (status === "disabled" && entity.enabled) return false;
      return (
        entity.name.toLowerCase().includes(search) ||
        entity.entity_id.toLowerCase().includes(search) ||
        (entity.room ?? "").toLowerCase().includes(search)
      );
    });
  }, [entities, query, domain, status]);

  const pageCount = Math.max(1, Math.ceil(filtered.length / PAGE_SIZE));
  const currentPage = Math.min(page, pageCount);
  const visible = filtered.slice((currentPage - 1) * PAGE_SIZE, currentPage * PAGE_SIZE);

  const visibleIds = visible.map((entity) => entity.entity_id);
  const selectedOnPage = visibleIds.filter((id) => selected.includes(id));
  const allPageSelected = visibleIds.length > 0 && selectedOnPage.length === visibleIds.length;

  function togglePageSelection() {
    setSelected((previous) =>
      allPageSelected
        ? previous.filter((id) => !visibleIds.includes(id))
        : [...new Set([...previous, ...visibleIds])],
    );
  }

  async function bulkUpdate(enabled: boolean) {
    const targets = entities.filter((entity) => selected.includes(entity.entity_id));
    if (!targets.length) return;

    setBulkBusy(true);
    setError("");
    setNotice("");

    const succeeded: HomeAssistantEntity[] = [];
    const failures: string[] = [];

    for (const entity of targets) {
      try {
        const updated = await updateHomeAssistantEntity(
          entity.entity_id,
          enabled,
          entity.room,
        );
        succeeded.push(updated);
      } catch {
        failures.push(entity.name);
      }
    }

    const saved = new Map(succeeded.map((entity) => [entity.entity_id, entity]));
    setEntities((previous) =>
      previous.map((entity) => {
        const updated = saved.get(entity.entity_id);
        return updated
          ? { ...entity, enabled: updated.enabled, room: updated.room }
          : entity;
      }),
    );

    setSelected(failures.length
      ? targets.filter((entity) => failures.includes(entity.name)).map((entity) => entity.entity_id)
      : []);

    if (failures.length) {
      setError(`${failures.length} updates failed. Failed entities remain selected for retry.`);
    }
    if (succeeded.length) {
      setNotice(`${succeeded.length} entities updated successfully.`);
    }

    setBulkBusy(false);
  }

  async function assignBulkRoom() {
    if (!selected.length || !bulkRoom.trim()) return;

    const room = bulkRoom.trim();
    const targets = entities.filter((entity) => selected.includes(entity.entity_id));

    setBulkBusy(true);
    setError("");
    setNotice("");

    const succeeded: HomeAssistantEntity[] = [];
    const failedIds: string[] = [];

    for (const entity of targets) {
      try {
        const updated = await updateHomeAssistantEntity(
          entity.entity_id,
          entity.enabled,
          room,
        );
        succeeded.push(updated);
      } catch {
        failedIds.push(entity.entity_id);
      }
    }

    const saved = new Map(succeeded.map((entity) => [entity.entity_id, entity]));

    setEntities((previous) =>
      previous.map((entity) => {
        const updated = saved.get(entity.entity_id);
        return updated
          ? { ...entity, enabled: updated.enabled, room: updated.room }
          : entity;
      }),
    );

    setSelected(failedIds);

    if (failedIds.length) {
      setError(`${failedIds.length} room assignments failed. Those entities remain selected for retry.`);
    }

    if (succeeded.length) {
      setNotice(`${succeeded.length} entities assigned to ${room}.`);
    }

    setBulkBusy(false);
  }

  async function save(entity: HomeAssistantEntity, enabled: boolean, room: string | null) {
    setBusy(entity.entity_id);
    setError("");
    setNotice("");

    try {
      const updated = await updateHomeAssistantEntity(entity.entity_id, enabled, room);
      setEntities((previous) =>
        previous.map((item) =>
          item.entity_id === entity.entity_id
            ? { ...item, enabled: updated.enabled, room: updated.room }
            : item,
        ),
      );
      setNotice(`Saved ${entity.name}.`);
      setNewRoomFor(null);
      setNewRoom("");
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : "Could not save entity preferences.");
    } finally {
      setBusy(null);
    }
  }

  function changeFilters(nextQuery: string, nextDomain: string, nextStatus: string) {
    setQuery(nextQuery);
    setDomain(nextDomain);
    setStatus(nextStatus);
    setPage(1);
  }

  return (
    <section className="ha-manager">
      <header className="ha-manager-header">
        <div>
          <span className="eyebrow">Home Assistant / Settings</span>
          <h1>Entity Manager</h1>
          <p>Choose which Home Assistant entities appear in Nuestra Casita.</p>
        </div>
        <button type="button" className="ha-manager-refresh" onClick={() => void refresh()} disabled={loading || busy !== null}>
          {loading ? "Loading..." : "Refresh entities"}
        </button>
      </header>

      <div className="ha-manager-summary">
        <div><strong>{entities.length}</strong><span>Total entities</span></div>
        <div><strong>{enabledCount}</strong><span>Enabled</span></div>
        <div><strong>{rooms.length}</strong><span>Assigned rooms</span></div>
      </div>

      <div className="ha-manager-filters">
        <label className="ha-manager-search">
          Search
          <input type="search" value={query} placeholder="Name, entity ID, or room"
            onChange={(event) => changeFilters(event.target.value, domain, status)} />
        </label>
        <label>
          Domain
          <select value={domain} onChange={(event) => changeFilters(query, event.target.value, status)}>
            <option value="all">All domains</option>
            {domains.map((item) => <option key={item} value={item}>{item}</option>)}
          </select>
        </label>
        <label>
          Visibility
          <select value={status} onChange={(event) => changeFilters(query, domain, event.target.value)}>
            <option value="all">All entities</option>
            <option value="enabled">Enabled only</option>
            <option value="disabled">Disabled only</option>
          </select>
        </label>
      </div>

      {error && <p className="form-error" role="alert">{error}</p>}
      {notice && <p className="ha-manager-notice" role="status">{notice}</p>}

      <div className="ha-manager-bulk">
        <label className="ha-manager-select-all">
          <input type="checkbox" checked={allPageSelected}
            disabled={bulkBusy || busy !== null || visibleIds.length === 0}
            onChange={togglePageSelection} />
          Select current page
        </label>
        <span>{selected.length} selected</span>
        <button type="button" disabled={!selected.length || bulkBusy || busy !== null}
          onClick={() => void bulkUpdate(true)}>
          {bulkBusy ? "Saving..." : "Enable selected"}
        </button>
        <button type="button" disabled={!selected.length || bulkBusy || busy !== null}
          onClick={() => void bulkUpdate(false)}>
          {bulkBusy ? "Saving..." : "Disable selected"}
        </button>
        <button type="button" disabled={!selected.length || bulkBusy}
          onClick={() => setSelected([])}>
          Clear selection
        </button>
        <div className="ha-manager-bulk-room">
          <input
            type="text"
            aria-label="Room for selected entities"
            placeholder="Room name"
            maxLength={100}
            value={bulkRoom}
            disabled={bulkBusy || busy !== null}
            onChange={(event) => setBulkRoom(event.target.value)}
          />
          <button type="button"
            disabled={!selected.length || !bulkRoom.trim() || bulkBusy || busy !== null}
            onClick={() => void assignBulkRoom()}>
            Assign room
          </button>
        </div>
      </div>

      <div className="ha-manager-list-header">
        <strong>{filtered.length} matching entities</strong>
        <span>Changes save automatically</span>
      </div>

      {loading && entities.length === 0 ? (
        <p className="muted">Loading Home Assistant entities...</p>
      ) : visible.length === 0 ? (
        <div className="ha-manager-empty">No entities match your filters.</div>
      ) : (
        <div className="ha-manager-list">
          {visible.map((entity) => (
            <div className="ha-manager-row" key={entity.entity_id}>
              <label className="ha-manager-row-select" title={`Select ${entity.name}`}>
                <input type="checkbox" aria-label={`Select ${entity.name}`}
                  checked={selected.includes(entity.entity_id)}
                  disabled={bulkBusy || busy !== null}
                  onChange={(event) => setSelected((previous) =>
                    event.target.checked
                      ? [...new Set([...previous, entity.entity_id])]
                      : previous.filter((id) => id !== entity.entity_id),
                  )} />
              </label>
              <div className="ha-manager-identity">
                <strong title={entity.name}>{entity.name}</strong>
                <small title={entity.entity_id}>{entity.entity_id}</small>
                <span className="ha-manager-state">{entity.state}</span>
              </div>
              <div className="ha-manager-room">
                <label htmlFor={`room-${entity.entity_id}`}>Room</label>
                {newRoomFor === entity.entity_id ? (
                  <div className="ha-manager-new-room">
                    <input aria-label={`New room for ${entity.name}`} value={newRoom} maxLength={100}
                      placeholder="New room name" onChange={(event) => setNewRoom(event.target.value)}
                      onKeyDown={(event) => {
                        if (event.key === "Enter" && newRoom.trim()) void save(entity, entity.enabled, newRoom.trim());
                        if (event.key === "Escape") setNewRoomFor(null);
                      }} />
                    <button type="button" disabled={!newRoom.trim() || busy !== null}
                      onClick={() => void save(entity, entity.enabled, newRoom.trim())}>Save</button>
                    <button type="button" onClick={() => setNewRoomFor(null)}>Cancel</button>
                  </div>
                ) : (
                  <select id={`room-${entity.entity_id}`} value={entity.room ?? ""}
                    disabled={busy !== null || bulkBusy}
                    onChange={(event) => {
                      if (event.target.value === "__new__") {
                        setNewRoom("");
                        setNewRoomFor(entity.entity_id);
                      } else {
                        void save(entity, entity.enabled, event.target.value || null);
                      }
                    }}>
                    <option value="">Unassigned</option>
                    {entity.room && !rooms.includes(entity.room) && <option value={entity.room}>{entity.room}</option>}
                    {rooms.map((room) => <option key={room} value={room}>{room}</option>)}
                    <option value="__new__">+ Create new room</option>
                  </select>
                )}
              </div>
              <label className="ha-manager-toggle">
                <input type="checkbox" checked={entity.enabled} disabled={busy !== null || bulkBusy}
                  onChange={(event) => void save(entity, event.target.checked, entity.room)} />
                <span>{busy === entity.entity_id ? "Saving..." : entity.enabled ? "Enabled" : "Disabled"}</span>
              </label>
            </div>
          ))}
        </div>
      )}

      <footer className="ha-manager-pagination">
        <span>Page {currentPage} of {pageCount}</span>
        <div>
          <button type="button" disabled={currentPage <= 1} onClick={() => setPage(currentPage - 1)}>Previous</button>
          <button type="button" disabled={currentPage >= pageCount} onClick={() => setPage(currentPage + 1)}>Next</button>
        </div>
      </footer>
    </section>
  );
}
