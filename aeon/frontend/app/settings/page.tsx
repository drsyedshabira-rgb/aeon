"use client";

import { useState } from "react";

const SUPPORTED_COUNTRIES = [
  { code: "US", label: "United States (FDA — functional)" },
  { code: "GB", label: "United Kingdom (MHRA — draft cartridge, not yet functional)" },
  { code: "EU", label: "European Union (EMA — draft cartridge, not yet functional)" },
  { code: "AU", label: "Australia (TGA — draft cartridge, not yet functional)" },
];

export default function SettingsPage() {
  const [country, setCountry] = useState("US");
  const [pharmacyName, setPharmacyName] = useState("");

  return (
    <div className="p-6 max-w-md">
      <h1 className="text-2xl font-semibold mb-4">Pharmacy Settings</h1>

      <label className="block mb-4">
        <span className="text-sm font-medium">Pharmacy Name</span>
        <input
          className="border rounded w-full p-2 mt-1"
          value={pharmacyName}
          onChange={(e) => setPharmacyName(e.target.value)}
        />
      </label>

      <label className="block mb-4">
        <span className="text-sm font-medium">Country / Regulatory Authority</span>
        <select className="border rounded w-full p-2 mt-1" value={country} onChange={(e) => setCountry(e.target.value)}>
          {SUPPORTED_COUNTRIES.map((c) => (
            <option key={c.code} value={c.code}>{c.label}</option>
          ))}
        </select>
        <span className="text-xs text-gray-500 mt-1 block">
          Only FDA (US) submission is currently functional. Other countries are shown
          for UI completeness but their cartridges are unverified drafts.
        </span>
      </label>

      <button className="bg-blue-600 text-white px-4 py-2 rounded">Save</button>
    </div>
  );
}
