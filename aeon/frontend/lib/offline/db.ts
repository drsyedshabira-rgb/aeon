import Dexie, { Table } from "dexie";

export interface QueuedReport {
  id?: number;
  localId: string;
  text?: string;
  imageBase64?: string;
  pharmacyId: string;
  createdAt: string;
  synced: boolean;
}

class AeonOfflineDB extends Dexie {
  queuedReports!: Table<QueuedReport, number>;

  constructor() {
    super("aeon_offline");
    this.version(1).stores({
      queuedReports: "++id, localId, synced, createdAt",
    });
  }
}

export const db = new AeonOfflineDB();
