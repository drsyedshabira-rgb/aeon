# AEON — Adverse Event Orchestration Nexus
## Investor Pitch — Updated with MVP Traction

### Slide 1 — Title
**AEON — Adverse Event Orchestration Nexus**
AI-powered adverse drug reaction reporting, for any pharmacy, in any country.

### Slide 2 — The Problem
- Pharmacovigilance reporting is manual, slow, and inconsistent across countries
- Under-reporting of ADRs is a well-documented global patient-safety gap
- Every country has a different authority, form, and submission format

### Slide 3 — The Solution
AEON turns a photo or a spoken/typed note into a correctly formatted, submitted ADR report — automatically routed to the right national authority.

### Slide 4 — How It Works
1. Pharmacist snaps a photo or types a quick note
2. NLP extracts drug, reaction, and patient details
3. Regulatory Cartridge Engine maps it to the correct country's format
4. Report is submitted (or queued offline) with full audit trail

### Slide 5 — MVP Validation *(new)*
- Working vertical-slice engine: text → NLP extraction → FDA FAERS-formatted XML → simulated submission with status tracking
- Example extraction output (from live test run):
  - Input: *"68 year old male patient developed a rash after starting amoxicillin"*
  - Correctly extracted: drug (Amoxicillin), reaction (rash), age (68), sex (male), confidence 1.0
- Generated XML validated against the FAERS-style structure; async status transition (pending → submitted) confirmed
- **Honest framing for investors:** the MVP proves the extraction → mapping → submission *pipeline* works end-to-end for one country (US/FDA) with a simplified reference mapping. It does not yet prove regulatory-grade accuracy at scale, nor submission access to any authority's real production system — both are the next milestone, not a solved problem.

### Slide 6 — Why Now
- Global regulatory push for real-world safety data (post-market surveillance)
- Mature open biomedical NLP models make extraction accuracy production-viable
- Independent pharmacies are digitizing rapidly but pharmacovigilance tooling hasn't kept pace

### Slide 7 — Market
- WHO estimates over 150 countries have some form of national pharmacovigilance program
- Target: independent + chain pharmacies, starting in markets with clear, accessible regulatory APIs/sandboxes

### Slide 8 — Business Model
- SaaS subscription tiered by report volume
- Multi-currency billing (USD/EUR/GBP/JPY/INR) via Stripe
- Enterprise API tier for chains integrating directly into existing PMS

### Slide 9 — Roadmap
- **Phase 1 (funded by this round):** Regulatory/legal validation of the FDA submission path + 1–2 additional countries with confirmed open APIs; move from reference-mapping to a certified integration
- **Phase 2:** Expand cartridge library via partner regulatory consultants, country by country
- **Phase 3:** Enterprise API + chain integrations
- *(Sales-cycle note: a working MVP shortens early discovery calls, but the gating step for any pilot customer is still regulatory sign-off per country — that timeline hasn't changed with the MVP.)*

### Slide 10 — Team & The Ask
- Founder background in clinical pharmacy, pharmacovigilance (ICH E2B), and pharmacoepidemiology
- Engineering built via AI-augmented development
- **Ask: $300k seed** — regulatory/compliance validation per target market, core engineering, first cartridge partnerships
