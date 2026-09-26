# Consumer-Permissioned Insurance Policy Data Aggregation APIs ("Plaid for Insurance")

Research date: 2026-09-26. US focus. About 17 tool calls; many vendor pages were read through search snippets or summarizing fetches, so treat exact figures as vendor marketing claims.

Scope note: providers fall into three groups.
(A) **Consumer-permissioned login aggregators.** The end user logs into a carrier account and the API returns their policy data: Canopy Connect, Axle, MeasureOne, Covie, and historically Trellis.
(B) **Third-party data prefill / bureau data.** No user login. Data comes from a contributory or proprietary database keyed on name and address: LexisNexis Auto Data Prefill / Current Carrier, Verisk, TransUnion Prefill, Fenris.
(C) **Document / portal extraction.** Dec-page parsing and carrier-portal scraping, for example Gaya AI, plus the document-upload fallbacks in group A.

---

## Canopy Connect: capabilities, carrier coverage, API docs, pricing tiers

### Takeaway
Canopy Connect is the most mature and most transparent "Plaid for insurance" API. It offers about 400 carrier integrations across personal and commercial P&C, 500+ data fields, webhooks, an SDK and white-label flow, monitoring, and public docs. A free self-serve sandbox is available, but Production and Enterprise API tiers are priced through sales. Separate agency (non-API) plans are publicly priced from $120/month.

### Cited Findings
- **What it does:** Canopy's Insurance API returns "fully-structured P&C personal and commercial insurance data directly from insurance carriers in seconds." It self-describes as "Plaid for Insurance." — [Canopy API page](https://www.usecanopy.com/api)
- **Carrier count / coverage:** "400 insurance carrier integrations covering 95%+ of the market." Claimed market coverage is 96% for auto, 91% for homeowners and 90% for standard commercial. — [Canopy API page](https://www.usecanopy.com/api)
- **Lines of business:** personal and commercial P&C (auto, home, commercial, including commercial fleets and BOP information). — [Canopy API page](https://www.usecanopy.com/api); [Canopy commercial fleets](https://www.usecanopy.com/solutions/commercial-fleets)
- **Data returned:** 500+ fields, including:
  - policy numbers, dates, premiums, coverages, limits and deductibles
  - contact info, vehicles, drivers and property details
  - declaration pages and ID cards
  - claims, incidents and driving records (7-year history)
  - commercial loss run summaries and property valuations/enrichment

  Sources: [Canopy API plans](https://www.usecanopy.com/api/api-plans); [Canopy API page](https://www.usecanopy.com/api)
- **Capabilities:** real-time updates via webhooks, SDKs for embedding, a white-label solution, account monitoring (continuous verification), and "auto/home policy editing" in Production. — [Canopy API page](https://www.usecanopy.com/api); [Canopy API plans](https://www.usecanopy.com/api/api-plans)
- **Public docs:** https://docs.usecanopy.com/reference/getting-started — [Canopy API page](https://www.usecanopy.com/api)
- **Developer signup:** self-serve developer credentials page. — [Canopy developer account](https://www.usecanopy.com/api/developer-account)
- **API pricing tiers:**
  - **API Sandbox:** free, with all API features including the SDK and white-label, unlimited API keys, and self-serve documentation support.
  - **API Production (Pilot):** contact for pricing. Adds a live environment, unlimited production keys, custom links, personal and commercial P&C, policy editing, property enrichment, account monitoring, and email/chat support.
  - **API Enterprise (Scale):** contact for pricing. Adds volume discounts on pre-committed spend, an MSA with SLA, custom data retention, a dedicated integration engineer, and SSO.

  Source: [Canopy API plans](https://www.usecanopy.com/api/api-plans)
- **Agency (non-API) platform pricing:**
  - $120/month (3 users; $10 per extra user)
  - Elevate: $300/month (5 users)
  - Peak: $600/month (10 users)

  A third-party aggregator reports these prices as last updated Aug 21, 2026. — [Software Finder](https://softwarefinder.com/insurance-software/canopy-connect); official page: [Canopy agency pricing](https://www.usecanopy.com/agencies/agency-pricing)
- **Notable customers named on the site:** Marble Insurance Hub, Covered Insurance, Cox Automotive Ecommerce, Blend Insurance, TSD Mobility. — [Canopy API page](https://www.usecanopy.com/api)
- **Use-case verticals:** insurance agencies (intake and quoting), carriers (sales and servicing), auto finance and loan servicing (insurance verification), commercial fleets. — [Canopy carriers](https://www.usecanopy.com/solutions/insurance-carriers); [Canopy auto finance](https://www.usecanopy.com/solutions/auto-finance); [Canopy loan servicing](https://www.usecanopy.com/solutions/loan-servicing)

### Inferences
- Canopy is the best fit for a developer who wants to try the category without a sales call, because the sandbox is free and self-serve. Real production pull pricing is not public.
- It appears to be the only player that publishes explicit per-line coverage percentages. These are vendor claims and have not been independently verified.

### Gaps
- Per-pull or per-connection production prices were not found on any public page.
- Life and annuity support was not mentioned. Canopy appears to be P&C only.
- It is unclear whether "document parsing" means OCR of uploaded dec pages or only retrieval of carrier-hosted PDFs. The site mentions importing documents, but I did not verify an upload/OCR endpoint.

---

## Other players: catalog (verified)

### Takeaway
Besides Canopy, the active consumer-permissioned players are:
- **Axle:** YC and Gradient Ventures backed. Auto and commercial fleet focus, with verification, monitoring and "policy actions".
- **MeasureOne:** auto and home, aimed at lenders.
- **Covie:** policy access and monitoring for lenders and carriers.

Trellis was acquired by Gen in March 2026. Fenris, LexisNexis, Verisk and TransUnion are not login-based aggregators; they are prefill databases. Gaya AI is document and portal extraction for agents.

### Cited Findings

**Axle (axle.insure)**
- **What it does:** "universal API for insurance data" to "instantly verify insurance and monitor ongoing coverage." — [Axle docs](https://docs.axle.insure/welcome)
- **Products listed in docs:**
  - Ignition: embedded, consent-based connect flow
  - Policy Lookup
  - Monitoring: notices of cancellations and coverage changes
  - Webhooks: Ignition, Account, Policy and Policy Action events
  - Sandbox environment
  - Embeddable widgets
  - Policy Validation: rule templates
  - Policy Actions: act on a policy on the user's behalf
  - Platform/multi-client support

  Source: [Axle llms.txt docs index](https://docs.axle.insure/llms.txt)
- **Data-collection methods:** Axle "verification agents look up the policy directly with the carrier," or the user links their carrier login. As a fallback, the user uploads an ID card or dec page, which Axle's Document AI processes. — [Axle blog](https://www.axle.insure/blog/the-modern-way-to-verify-auto-insurance-a-guide-to-data-apis); [Axle Policy Lookup](https://www.axle.insure/blog/introducing-policy-lookup)
- **Lines of business:** personal auto and commercial fleet through one integration. — [Axle API page](https://www.axle.insure/product/api)
- **Carriers:** "hundreds of carriers." No exact number was found. — [Axle site](https://www.axle.insure/)
- **Positioning:** the homepage now reads "AI Agents to Automate Insurance Workflows," a shift from pure API toward agentic workflows. — [Axle homepage](https://www.axle.insure/)
- **Funding:** $4M seed led by Gradient Ventures (Google), plus Y Combinator. Press coverage calls it the "Plaid for insurance." — [PR Newswire](https://www.prnewswire.com/news-releases/axle-secures-4m-led-by-gradient-ventures-to-reinvent-insurance-verification-301796885.html); [TechCrunch, Apr 2023](https://techcrunch.com/2023/04/10/gradient-ventures-axle-plaid-insurance-verification/)
- **Access:** public docs at docs.axle.insure with a sandbox. Pricing goes through the contact page ("Get Started"). — [Axle llms.txt](https://docs.axle.insure/llms.txt)
- **Competitors:** CB Insights lists Canopy Connect as a top competitor. — [CB Insights](https://www.cbinsights.com/company/axle-1/alternatives-competitors)

**MeasureOne**
- **What it does:** consumer-permissioned data (CPD) platform covering insurance, payroll/VOIE and academic data. The user selects a carrier and logs in within the MeasureOne flow. Consent is captured and managed via the API. — [MeasureOne](https://www.measureone.com/); [MeasureOne insurance verification](https://www.measureone.com/solutions/insurance-verification)
- **Lines of business:** auto and home. Renters verification was listed as "coming soon" on the coverage-details page, but a separate renters verification solution page exists, so the status may be stale. — [MeasureOne coverage details](https://www.measureone.com/solutions/insurance-details-collection); [MeasureOne renters](https://www.measureone.com/solutions/renters-insurance-verification)
- **Data returned:** carrier, policy number, status, effective dates, deductibles, listed vehicles/VINs, insured address, total premium and payment schedule. Reports are configurable. — [MeasureOne lender blog](https://www.measureone.com/blog/api-for-checking-borrower-auto-insurance-a-guide-for-lenders); [MeasureOne coverage details](https://www.measureone.com/solutions/insurance-details-collection)
- **Coverage claims:** "95%+ coverage" and "support for all major insurance providers." No carrier count is given. — [MeasureOne coverage details](https://www.measureone.com/solutions/insurance-details-collection)
- **Capabilities:** Insurance Monitoring product, and a document-upload alternative with authenticity verification. — [MeasureOne monitoring](https://www.measureone.com/solutions/insurance-monitoring); [MeasureOne coverage details](https://www.measureone.com/solutions/insurance-details-collection)
- **Access:** public docs at docs.measureone.com, "Get a Dev Account," and free trial signup. — [MeasureOne API docs](https://docs.measureone.com/overview/api); [MeasureOne coverage details](https://www.measureone.com/solutions/insurance-details-collection)
- **Target customers:** auto lenders and the automotive market. — [MeasureOne automotive](https://www.measureone.com/customers/automotive)

**Covie**
- **What it does:** a "carrier-neutral API" offering policy access ("like Plaid for insurance") and monitoring. Covie Access provides consent-based, real-time policy data (coverages, limits, status), verification against compliance thresholds, and ongoing tracking. — [Catalyit directory](https://catalyit.com/solution-provider-directory/covie-access); [Covie](https://www.covie.com/)
- **Carrier-side products:** carriers use Covie to deliver certificates of insurance programmatically and to embed quoting with distribution partners. — [Covie for carriers](https://www.covie.com/solutions/carriers)
- **Background:** Y Combinator company. — [YC](https://www.ycombinator.com/companies/covie)

**Trellis (trellisconnect)**
- **What it did:** the Trellis Connect API was a consumer-permissioned auto insurance "prefill" API with public docs (v1.2.0). — [Trellis docs](https://docs.trellisconnect.com/)
- **Later products:** in Dec 2021 Trellis launched an end-to-end API for comparing and buying car insurance. — [GlobeNewswire](https://www.globenewswire.com/news-release/2021/12/14/2351792/0/en/Trellis-Launches-Industry-s-First-End-To-End-API-Platform-For-Comparing-And-Purchasing-Car-Insurance.html)
- **Acquisition (March 10, 2026):** Gen (Norton/LifeLock parent) acquired Trellis, the company behind the Savvy insurance marketplace, and is folding it into "Engine by Gen." Terms are undisclosed and described as immaterial. The press release does not mention Trellis Connect API. — [PR Newswire](https://www.prnewswire.com/news-releases/gen-expands-insurance-capabilities-of-engine-gens-secure-financial-wellness-marketplace-302710072.html)
- **Prior investors:** QED, General Catalyst, Nyca, Amex Ventures. — [search summary of PR Newswire/Crunchbase](https://www.crunchbase.com/organization/trellis-eb8c)

**Fenris Digital (prefill, not login-based)**
- **What it does:** Richmond, VA company founded in 2016. It offers SOC2 API products for predictive scoring, data enrichment and prefill across auto, home, life and small commercial. It uses a "proprietary, non-contributory dataset." — [Fenris auto prefill blog](https://fenrisd.com/blog/streamlining-auto-insurance-quoting-with-prefill-apis/); [Fenris docs](https://documentation.fenrisd.com/)
- **Product specifics:**
  - Property prefill: 500+ data points per address.
  - Small Business Prefill API: business name and address as input.
  - Life Insurance Prefill API.

  Sources: [Fenris property](https://fenrisd.com/property-insurance/); [PR Newswire SMB](https://www.prnewswire.com/news-releases/fenris-announces-new-small-business-insurance-prefill-api-301318888.html); [PR Newswire Life](https://www.prnewswire.com/news-releases/fenris-announces-new-life-insurance-prefill-api-301147943.html)
- **Distribution:** integrated into EZLynx for independent agents. — [Fenris/EZLynx](https://fenrisd.com/news/fenris-digital-brings-data-prefill-to-ezlynx-platform-for-independent-insurance-agents/)
- **Public docs:** documentation.fenrisd.com — [Fenris docs](https://documentation.fenrisd.com/)

**LexisNexis Risk Solutions: Auto Data Prefill / Current Carrier (bureau data)**
- **What it does:** returns household drivers, vehicles and prior/current carrier policy information from minimal applicant input, for quoting and underwriting. — [LexisNexis ADP](https://risk.lexisnexis.com/products/auto-data-prefill); [BriteCore ADP](https://help.britecore.com/hc/en-us/articles/8724354229011-LexisNexis-Auto-Data-Prefill-overview)
- **Access caveat:** "To order reports, you must contribute to the LexisNexis Current Carrier database." It is contributory, carrier-only and sales-gated. — [BriteCore ADP](https://help.britecore.com/hc/en-us/articles/54273711508115-LexisNexis-Auto-Data-Prefill)
- **Other products:** Commercial Data Prefill and Claims Datafill. — [LexisNexis commercial prefill](https://risk.lexisnexis.com/products/commercial-data-prefill); [Claims Datafill](https://risk.lexisnexis.com/products/claims-datafill)
- **Distribution:** Guidewire InsuranceNow marketplace and EZLynx rating partners. — [Guidewire](https://marketplace.guidewire.com/product/lexisnexis-auto-data-prefill-for-insurancenow/01t3n00000GfLJhAAN); [EZLynx](https://www.ezlynx.com/partners/rating-pre-fill/)

**Verisk**
- **Products:**
  - QuickFill: prior liability coverage details and other household drivers.
  - Commercial Vehicle Prefill: vehicles registered to a business, looked up by name and address.
  - Coverage Verifier: prior insurance/coverage history.

  Sources: [Verisk prefill blog](https://www.verisk.com/blog/prefill-technology-helps-insurers-gather-reliable-quote-data/); [Verisk Commercial Vehicle Prefill](https://www.verisk.com/products/commercial-vehicle-prefill/)
- **Jornaya:** Verisk acquired Jornaya (consumer-journey/lead-intent data) in 2020. It is a marketing/lead-intelligence product, not policy data. — [Wikipedia: Verisk](https://en.wikipedia.org/wiki/Verisk_Analytics)

**TransUnion**
- **Products:** TransUnion Prefill, part of the TruLookup identity-enrichment family, including insurance prefill with vehicle add-on services. It is enterprise and sales-gated. — [TransUnion Prefill](https://www.transunion.com/solution/trulookup/identity-enrichment/identity-prefill)

**Gaya AI (document / portal extraction)**
- **What it does:** AI copilot for agents ("Super Copy / Super Paste"). It extracts data from carrier portals, agency management systems, dec pages, PDFs, images and ACORD forms, with no data mapping. Structured output is available via public APIs and webhooks. — [Gaya](https://gaya.ai/); [Digital Insurance](https://www.dig-in.com/news/insurance-data-management-startup-finds-its-groove)
- **Coverage:** described as carrier-agnostic across "hundreds of personal, commercial, and specialty carriers." — [Catalyit](https://catalyit.com/solution-provider-directory/gaya-ai)
- **Partners:** HawkSoft API partner and GravityCerts. — [HawkSoft](https://www.hawksoft.com/about/partners/gaya); [GravityCerts](https://gravitycerts.com/latest-updates/how-independent-insurance-agencies-are-using-gravitycerts-gaya-to-cut-quoting-time-by-80/)

**Carpe Data**
- **What it does:** "AI-native decision platform for insurance." It is an alternative/public-data provider for underwriting and claims (for example, a partnership with Harbor.ai for E&S underwriting). It is not consumer-permissioned policy retrieval. — [Carpe press](https://carpe.io/resources/press/); [Carpe/Harbor.ai](https://carpe.io/carpedata-harborai-partnership/)
- **Deal history:** William Blair advised on a Carpe Data transaction with Thomas H. Lee Partners. The date was not confirmed in this research. — [William Blair](https://www.williamblair.com/News/Carpe-Data-and-Thomas-H-Lee-Partners-Transaction)

**Zywave / Mobi**
- No evidence was found of a Zywave–Mobi insurance-data deal or a Zywave consumer-permissioned policy-data API. Zywave's recent news covers an agentic AI strategy (Dec 2025) and the "Zywave Apex" AI platform (2026). — [Insurance Journal Zywave archive](https://www.insurancejournal.com/archive/zywave/); [Zywave acquisitions](https://www.zywave.com/acquisitions/)

### Inferences
- The true peer set for "user connects carrier account" is Canopy Connect, Axle, MeasureOne and Covie. Trellis Connect is likely de-emphasized after the Gen acquisition, since the press release focuses on the Savvy marketplace. This is unconfirmed.
- The bureau/prefill vendors (LexisNexis, Verisk, TransUnion, Fenris) return household or prior-carrier data without the consumer logging in, typically under FCRA/GLBA permissible purpose. They are sold to carriers and agencies, not self-serve developers. LexisNexis also requires contributing data.
- For a personal assistant use case such as JARVIS reading the user's own policies, only the group A login aggregators, or dec-page parsing (Axle Document AI, MeasureOne upload, Gaya), are realistic. Canopy's free sandbox is the lowest-friction starting point.

### Gaps
- **Plaid, Argyle, Pinwheel:** not investigated due to the tool-call budget. I found no source showing Plaid offers an insurance policy data product. Argyle and Pinwheel are payroll/employment aggregators, and I did not verify any insurance offering. Treat these as unverified.
- **Generic document parsers (Sensible, Docsumo, Indico):** not researched. It is unknown whether they ship prebuilt dec-page models.
- Exact carrier counts for Axle, MeasureOne and Covie are not public. They use only phrases like "hundreds" or "all major."
- Canopy is the only provider found with public pricing, and only for agency plans. No API per-pull pricing was found for any provider.
- Covie's access model (sandbox, public docs) was not verified.
- Life and annuity consumer-permissioned aggregation: none of the group A players clearly support it. Fenris offers life prefill, but that is bureau-style data, not policy retrieval.
- Non-US players were not researched.

---

## Public developer docs & sandboxes vs. sales-gated

### Takeaway
Canopy (free self-serve sandbox), Axle (public docs plus sandbox; pricing via contact) and MeasureOne (public docs plus dev account/free trial) are developer-accessible. Fenris and Trellis have public docs, but production access is sales-gated. LexisNexis, Verisk and TransUnion are fully enterprise and sales-gated.

### Cited Findings
- **Canopy:** free API Sandbox, self-serve developer credentials, public docs at docs.usecanopy.com. Production and Enterprise pricing via contact. — [Canopy API plans](https://www.usecanopy.com/api/api-plans); [Canopy developer account](https://www.usecanopy.com/api/developer-account)
- **Axle:** public docs (docs.axle.insure) including a sandbox environment. Pricing via the contact page. — [Axle llms.txt](https://docs.axle.insure/llms.txt)
- **MeasureOne:** public docs (docs.measureone.com), "Get A Dev Account," and free trial. — [MeasureOne API](https://docs.measureone.com/overview/api); [MeasureOne coverage details](https://www.measureone.com/solutions/insurance-details-collection)
- **Fenris:** public docs at documentation.fenrisd.com. — [Fenris docs](https://documentation.fenrisd.com/)
- **Trellis:** public API docs (v1.2.0) still online. — [Trellis docs](https://docs.trellisconnect.com/)
- **LexisNexis ADP:** requires contributing to the Current Carrier database. — [BriteCore](https://help.britecore.com/hc/en-us/articles/54273711508115-LexisNexis-Auto-Data-Prefill)

### Inferences
- Access to Fenris production, Verisk and TransUnion requires a sales contract. This is typical for FCRA-regulated bureau data but was not explicitly confirmed on their pages.

### Gaps
- Whether Trellis docs and the sandbox still work post-acquisition was not verified.
- Covie docs and sandbox availability were not verified.

---

## Shutdowns, acquisitions, changes (2025–2026)

### Takeaway
The notable 2026 event is Gen's acquisition of Trellis (March 10, 2026). Axle has repositioned toward "AI agents" for insurance workflows. No shutdowns of Canopy, Axle or MeasureOne were found.

### Cited Findings
- Gen acquired Trellis (Savvy) on March 10, 2026, to integrate it into Engine by Gen. Terms were undisclosed and immaterial. — [PR Newswire](https://www.prnewswire.com/news-releases/gen-expands-insurance-capabilities-of-engine-gens-secure-financial-wellness-marketplace-302710072.html)
- Axle's homepage tagline is now "AI Agents to Automate Insurance Workflows." Its docs add Policy Actions and Policy Validation. — [Axle](https://www.axle.insure/); [Axle llms.txt](https://docs.axle.insure/llms.txt)
- Canopy agency pricing was reported as current as of Aug 21, 2026 (third-party aggregator). — [Software Finder](https://softwarefinder.com/insurance-software/canopy-connect)
- Zywave: agentic AI strategy (Dec 2025) and the Zywave Apex AI platform (2026). No policy-aggregation API was found. — [Insurance Journal](https://www.insurancejournal.com/archive/zywave/)
- Verisk–Jornaya (2020) and Verisk's sale of its financial services unit to TransUnion ($515M) are older deals, not 2025–2026. — [Wikipedia: Verisk](https://en.wikipedia.org/wiki/Verisk_Analytics)

### Inferences
- The category is consolidating (Trellis into Gen), and players are moving to agentic AI positioning (Axle, Gaya, Zywave).

### Gaps
- Funding rounds after 2023 for Axle, Canopy, MeasureOne and Covie were not found in this pass.
- The date and ownership status of the Carpe Data / THL transaction were not confirmed.
