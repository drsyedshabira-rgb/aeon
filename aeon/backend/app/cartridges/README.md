# Cartridge Library — Status

| Authority | Status | Usable for real submission? |
|---|---|---|
| FDA (fda_faers.json) | reference_only | No — simplified illustrative mapping based on public E2B(R3) structure. Verify against FDA ESG requirements before real use. |
| Pakistan (pakistan.json) | draft_placeholder | No. Structural placeholder for DRAP Yellow Form mapping only. Field mapping and submission workflow are not verified against Pakistan's official requirements. |
| EMA, MHRA, TGA, PMDA, Health Canada, ANVISA, CDSCO, NMPA, WHO/VigiBase | draft_placeholder | No. Structural placeholders only — field mappings are NOT verified against each authority's real published spec. Several of these authorities may not offer an open third-party submission API at all (notably EudraVigilance, PMDA, NMPA). |

**Before treating any cartridge beyond FDA as real:** get a regulatory/compliance
consultant familiar with that specific country's pharmacovigilance reporting
requirements to verify (a) whether third-party software submission is even
permitted, (b) the actual field-level schema, and (c) the access/registration
process. This is a legal and regulatory research task, not an engineering one —
see the Honest Scoping Note in AEON_Technical_Blueprint.md.
