import { db, QueuedReport } from "./offline/db";

const API_BASE = process.env.NEXT_PUBLIC_API_BASE || "/api/v1";

function isOnline(): boolean {
  return typeof navigator !== "undefined" ? navigator.onLine : true;
}

export async function submitReport(payload: { text?: string; imageBase64?: string; pharmacyId: string }) {
  if (isOnline()) {
    try {
      const res = await fetch(`${API_BASE}/reports`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          text: payload.text,
          image_base64: payload.imageBase64,
          pharmacy_id: payload.pharmacyId,
        }),
      });
      if (!res.ok) throw new Error(`API error: ${res.status}`);
      return await res.json();
    } catch (err) {
      // Network flaked mid-request — fall through to offline queue rather than losing the report
      return queueOffline(payload);
    }
  }
  return queueOffline(payload);
}

async function queueOffline(payload: { text?: string; imageBase64?: string; pharmacyId: string }) {
  const localId = crypto.randomUUID();
  const record: QueuedReport = {
    localId,
    text: payload.text,
    imageBase64: payload.imageBase64,
    pharmacyId: payload.pharmacyId,
    createdAt: new Date().toISOString(),
    synced: false,
  };
  await db.queuedReports.add(record);

  if ("serviceWorker" in navigator && "SyncManager" in window) {
    const registration = await navigator.serviceWorker.ready;
    // @ts-ignore — Background Sync API typing gap in lib.dom
    await registration.sync.register("aeon-sync-reports");
  }

  return { report_id: localId, status: "queued_offline", extracted: null };
}

export async function syncQueuedReports() {
  const unsynced = await db.queuedReports.where("synced").equals(0 as any).toArray();

  for (const record of unsynced) {
    try {
      const res = await fetch(`${API_BASE}/reports`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          text: record.text,
          image_base64: record.imageBase64,
          pharmacy_id: record.pharmacyId,
        }),
      });
      if (res.ok && record.id !== undefined) {
        await db.queuedReports.update(record.id, { synced: true });
      }
    } catch {
      // still offline or API unreachable — leave queued, will retry next sync event
    }
  }
}

export async function getReport(reportId: string) {
  const res = await fetch(`${API_BASE}/reports/${reportId}`);
  if (!res.ok) throw new Error(`API error: ${res.status}`);
  return res.json();
}
