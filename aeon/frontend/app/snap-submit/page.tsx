"use client";

import { useRef, useState } from "react";
import Webcam from "react-webcam";
import { submitReport } from "@/lib/api-client";

export default function SnapSubmitPage() {
  const webcamRef = useRef<Webcam>(null);
  const [captured, setCaptured] = useState<string | null>(null);
  const [extracted, setExtracted] = useState<any>(null);
  const [status, setStatus] = useState<string>("idle");
  const [editableFields, setEditableFields] = useState<any>(null);

  const capture = () => {
    const imageSrc = webcamRef.current?.getScreenshot();
    if (imageSrc) setCaptured(imageSrc);
  };

  const handlePreview = async () => {
    if (!captured) return;
    setStatus("extracting");
    const base64 = captured.split(",")[1];
    const result = await submitReport({ imageBase64: base64, pharmacyId: "demo" });
    setExtracted(result.extracted);
    setEditableFields(result.extracted);
    setStatus(result.status);
  };

  const handleConfirmSubmit = async () => {
    // In production this PATCHes the report with pharmacist-edited fields
    // before final submission — stubbed here since the backend endpoint
    // for edit-before-submit isn't in this vertical slice yet.
    setStatus("submitted_pending_confirmation");
  };

  return (
    <div className="p-6 max-w-lg mx-auto">
      <h1 className="text-2xl font-semibold mb-4">Snap & Submit</h1>

      {!captured && (
        <>
          <Webcam ref={webcamRef} screenshotFormat="image/jpeg" className="rounded mb-4" />
          <button onClick={capture} className="bg-blue-600 text-white px-4 py-2 rounded">
            Capture
          </button>
        </>
      )}

      {captured && !extracted && (
        <>
          <img src={captured} alt="captured" className="rounded mb-4" />
          <button onClick={handlePreview} className="bg-blue-600 text-white px-4 py-2 rounded" disabled={status === "extracting"}>
            {status === "extracting" ? "Extracting…" : "Extract Details"}
          </button>
        </>
      )}

      {extracted && (
        <div className="mt-4 space-y-3">
          <h2 className="font-medium">Review extracted details before submitting:</h2>
          <label className="block text-sm">
            Drug
            <input
              className="border rounded w-full p-2 mt-1"
              value={editableFields?.suspect_drugs?.[0]?.drug_name ?? ""}
              onChange={(e) =>
                setEditableFields({
                  ...editableFields,
                  suspect_drugs: [{ ...editableFields.suspect_drugs?.[0], drug_name: e.target.value }],
                })
              }
            />
          </label>
          <label className="block text-sm">
            Reaction
            <input
              className="border rounded w-full p-2 mt-1"
              value={editableFields?.reaction?.meddra_term ?? ""}
              onChange={(e) =>
                setEditableFields({ ...editableFields, reaction: { ...editableFields.reaction, meddra_term: e.target.value } })
              }
            />
          </label>
          <p className="text-sm text-gray-500">Extraction confidence: {extracted.confidence}</p>
          <button onClick={handleConfirmSubmit} className="bg-green-600 text-white px-4 py-2 rounded">
            Confirm & Submit
          </button>
        </div>
      )}

      {status === "queued_offline" && (
        <p className="text-sm text-orange-600 mt-2">
          You're offline — this report is queued and will submit automatically once you're back online.
        </p>
      )}
    </div>
  );
}
