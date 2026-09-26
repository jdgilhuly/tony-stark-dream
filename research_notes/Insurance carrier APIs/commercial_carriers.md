# Commercial / Small-Business Insurance Carriers and MGAs with Quote/Bind/Issue APIs (US, as of Sept 2026)

Method note: About 18 search/fetch calls. Primary sources were carrier docs and pages (Coterie, Coalition, Cowbell, At-Bay, Pie, Nationwide, Travelers, Chubb, biBERK). There were also two aggregator "API indexes" (Herald, CoverForce), which are the densest cross-carrier sources available. Several facts come from API Evangelist GitHub profiles. These are independent **third-party** summaries, not carrier docs, and are flagged where used. Some pages (thimble.com/api, coverager.com, docs.coterieinsurance.com body, developer.travelers.com) returned 403 or had JS-only content and could not be read in full.

## Q1: Coterie Insurance API details

### Takeaway
Coterie has one of the most open, well-documented commercial small-business APIs. It is a public REST docs site with an OpenAPI spec and Postman collection, and covers BOP/GL/PL/WC. A full embedded quote-to-bind needs only two calls: bindable quote, then bind. Access is limited to appointed agents and digital partners.

### Cited Findings
- Public docs site: "Coterie Commercial Insurance API" at docs.coterieinsurance.com — [Coterie Docs](https://docs.coterieinsurance.com/)
- The REST API lets "appointed agents and digital partners" generate bindable quotes, bind and issue policies, look up industry/NAICS classifications, retrieve policy documents, and subscribe to webhooks — [Coterie Docs / search snippet](https://docs.coterieinsurance.com/); [API Evangelist Coterie profile (third-party)](https://github.com/api-evangelist/coterie)
- The simplest embedded flow is 2 calls, Bindable Quote and then Bind Policy. The partner owns the whole quote-to-bind UX — [Coterie Quick Start blog](https://coterieinsurance.com/blog/quick-start-quote-bind-small-business-insurance-with-coterie/)
- API surface per the third-party profile: base URL `https://api.coterieinsurance.com/v1`. Quotes API (rated bindable quotes plus UW questions), Policies API (bind/issue, accepts **Stripe payment tokens**), Applications API, Industry/NAICS API, Documents API (policy docs, proposals, PDFs), Webhooks API (issuance, cancellation, premium-update events). OpenAPI spec, Postman collection, and rate-limit docs are published — [API Evangelist Coterie (third-party)](https://github.com/api-evangelist/coterie)
- Lines: BOP, GL, Professional Liability, Workers' Comp — [API Evangelist (third-party)](https://github.com/api-evangelist/coterie). The Herald index lists Coterie BOP, GL, PL — [Herald Insurance API Index](https://www.heraldai.com/insurance-api-index)
- Coterie's 2025 recap says the API has a 92% success rate on bindable BOP and GL quotes and expanded access to Cyber, Workplace Violence, and EPL coverages. A full partner integration was completed in 3 weeks — [Coterie "Caps 2025" press release](https://coterieinsurance.com/newsroom/press-releases/coterie-insurance-caps-2025/)
- Coterie markets quote/bind "in all 50 states" in its agent guide — [Coterie agent guide](https://coterieinsurance.com/blog/quote-bind-small-business-insurance-in-all-50-states-agent-guide/)
- Partner program page — [Coterie Partners](https://coterieinsurance.com/partners/)

### Inferences
- Coterie is the reference example of an "open" small-commercial carrier API: public docs, a published spec, payments inside the bind call, and webhooks. It is probably the easiest direct-carrier integration for a tech partner. A tech partner still needs a licensed entity (its own agency license or a Coterie-arranged model) to receive commission.

### Gaps
- Commission rates, sandbox URL, and auth method could not be read from the docs site (JS-rendered). Certificate-of-insurance and endorsement endpoints were not confirmed.

## Q2: AmTrust API (workers' comp, BOP, GL)

### Takeaway
AmTrust runs a Commercial Lines API for appetite, quote, and bind across WC, BOP, GL, and package. It has a developer portal with OAuth 2.0. It is mainly consumed by agents and through comparative raters and aggregators (Appulate, Semsee, Tarmika, IBQ, CoverForce, Herald).

### Cited Findings
- AmTrust "Commercial Lines API" lets agents, brokers, and tech partners review appetite, generate quotes, and bind commercial policies. Lines: WC, BOP, GL, Commercial Package. 300+ bind-online-eligible class codes. Developer portal `utapiportal.amtrustgroup.com`, info/sign-up at amtrustfinancial.com/api. OAuth 2.0 with 4-hour tokens. Integration partners: Semsee, Appulate, Tarmika, IBQ Systems. No documents, payments, or COI endpoints were documented — [API Evangelist AmTrust profile (third-party)](https://github.com/api-evangelist/amtrust-financial-services)
- The Appulate partnership (2020) lets retail agents upload ACORD data from their management system to AmTrust's API, get an instant WC quote, and bind online — [AmTrust blog](https://amtrustfinancial.com/blog/small-business/amtrust-partners-with-appulate-workers-comp-quotes); [BusinessWire](https://www.businesswire.com/news/home/20200730005009/en/Appulate-Digitizes-Workers-Compensation-Policies-with-AmTrust)
- Semsee added AmTrust to its quoting platform — [Semsee](https://semsee.com/press-releases/semsee-adds-amtrust-to-its-quoting-platform)
- Herald index: AmTrust API products are BOP, Cyber, WC, plus binding-authority GL/Property and 3 other BA LOBs — [Herald Index](https://www.heraldai.com/insurance-api-index). CoverForce lists AmTrust as "Live on CoverForce" for BOP, Cyber, WC, GL — [CoverForce API Index](https://www.coverforce.com/carriers/api-index)

### Inferences
- Access is normally agency-based. An agency appointment with AmTrust, or going through an appointed aggregator, is the practical route.

### Gaps
- The volume and SLA figures (12M daily calls, 99.68% uptime) come only from the third-party profile, so treat them as unverified. Public commission terms were not found.

## Q3: Full catalog of other carriers/MGAs with commercial-lines APIs

### Takeaway
There are dozens of API-enabled commercial carriers. Herald's index claims 86 carriers/MGAs, 228 API products, and 25 LOBs. Almost all are **agent/broker-distribution APIs**: the caller must be a licensed producer, either appointed directly or through an aggregator. Truly open, self-serve public docs are rare (Coterie, At-Bay, Nationwide's partner portal, Travelers' portal, Chubb Studio). Embedded "tech-partner" programs (NEXT Connect, Chubb Studio, Thimble, Cowbell, Coalition) exist but are gated by partner agreements.

### Cited Findings — Direct carrier / MGA APIs (primary sources)

**Cyber / management liability**
- **Coalition** (MGA plus Coalition Insurance Co.): Active Cyber (SME and enterprise), AI coverage, Executive Risks (D&O, EPL), Tech E&O, Misc PL. "Rate, quote, bind, and manage renewals entirely through APIs", with customizable limits and retentions and generation of all documents. For licensed brokers and digital platforms. Sandbox accounts, QA test plans, and a dedicated implementation manager are provided. Average integration is 2–4 weeks, 200,000+ companies have been quoted via API, and uptime is 99.9%. Products are "may not be available in all states" — [Coalition Broker API](https://www.coalitioninc.com/brokers/api); [Coalition Exec Risks API announcement](https://www.coalitioninc.com/announcements/coalition-introduces-new-apis-to-power-executive-risks-insurance)
- **At-Bay**: public docs at developers.at-bay.com. REST API with quote-to-bind-to-renew for Surplus Cyber, Surplus Tech E&O, and Surplus MPL. JWT bearer auth. Demo env `https://api-demo.at-bay.com/v2`, prod `https://api.at-bay.com/v2`. Async flow: POST /quotes, then poll GET /quotes/{id}; P90 quote readiness is 40s. Production submissions go through **Broker-of-Record clearance**, which blocks duplicate domains or addresses within 60 days. Open to brokers, tech companies, and partners, who apply through At-Bay — [At-Bay API Quickstart](https://developers.at-bay.com/docs/getting-started); [At-Bay Partnerships & API](https://www.at-bay.com/about/partnerships/); [At-Bay help: Does At-Bay offer an API?](http://help.at-bay.com/en/articles/3578645-does-at-bay-offer-an-api)
- **Cowbell**: Cowbell Prime cyber, with instant bindable quotes via API ("rate, quote, bind") and a co-branded storefront option. Dev portal at developers.cowbellcyber.ai. 12+ API partners, including AmWins, Bold Penguin, and Herald — [Cowbell API-Based Quoting](https://cowbell.insure/api-quoting/)
- **Corvus**: Herald lists Cyber and Tech E&O APIs — [Herald Index](https://www.heraldai.com/insurance-api-index). Corvus is now part of Travelers — [Seedpod comparison](https://seedpodcyber.com/cyber-insurance-carrier-comparison/)

**Workers' comp**
- **Pie Insurance**: WC-focused. REST API with appetite checker, price indication, quote request, submission document upload, bindable quote retrieval, and quote status tracking. Swagger docs and an integration doc are provided. Credentials are issued on request and API Terms of Use apply. Aimed at agencies and partners. "Not available in all states." Other lines (commercial auto, BOP, GL, PL) come via third-party underwriters — [Pie Agency API page](https://www.pieinsurance.com/agency/api). Partner API launched Nov 2020, with integrations with Bold Penguin, Tarmika, and Talage — [PR Newswire](https://www.prnewswire.com/news-releases/pie-insurance-launches-partner-api-301169212.html); [Coverager](https://coverager.com/pie-insurance-launches-partner-api/)
- **EMPLOYERS**: WC API on Herald. Herald reports that EMPLOYERS generates over 50% of submission and quote volume via API — [Herald API Index](https://www.heraldai.com/insurance-api-index); [Herald blog](https://www.heraldai.com/blog/introducing-the-insurance-api-index)
- Other WC APIs per the aggregators: Accident Fund and BerkleyNet ("Live on CoverForce"), Attune (WC) — [CoverForce API Index](https://www.coverforce.com/carriers/api-index). State Auto, WCF, Cincinnati, CNA, Liberty Mutual, Hartford Steam Boiler, Great American, Westfield, Main Street America, Nationwide, Markel, Acuity — [Herald Index](https://www.heraldai.com/insurance-api-index)

**Small-business multiline (BOP/GL/PL)**
- **ERGO NEXT (formerly NEXT Insurance)**: runs the NEXT Connect partner program. Partner REST API for quote, bind, policy data, premium audits, and COI retrieval, plus embeddable quote flows used by Gusto and Square. Aggregates 15+ carriers. **No public developer portal, OpenAPI spec, sandbox, or SDK**. Access is only through the partner program with bilateral pricing. Lines: GL, WC, BOP, PL, commercial auto, commercial property, tools & equipment, cyber, EPLI, liquor, product liability — [Supergood API Report Card (third-party)](https://supergood.ai/api-report-card/next-insurance); [API Evangelist NEXT (third-party)](https://github.com/api-evangelist/next-insurance); partner page [ERGO NEXT Partner With Us](https://www.nextinsurance.com/become-a-partner/)
- **Hiscox**: Herald lists BOP, Cyber (2), GL, PL, Tech E&O API products — [Herald Index](https://www.heraldai.com/insurance-api-index). Hiscox distributes Crime via API through ClarionDoor — [Digital Insurance](https://www.dig-in.com/news/hiscox-clariondoor-partner-on-second-api-hosted-coverage-offering). A June 2025 Cargo API (quote/bind small cargo and stock throughput up to $5M) is broker-distributed, with Price Forbes as the first partner. It is London/Group-level, not a US small-commercial product — [Hiscox Group PR](https://www.hiscoxgroup.com/news/press-releases/2025/30-06-25). In Aug 2025 Hiscox agreed to acquire Vouch's MGA (Corix Insurance Services) and Vouch Insurance Company. Vouch stays an independent broker with a multi-year Hiscox distribution deal — [Hiscox Group PR](https://www.hiscoxgroup.com/news/press-releases/2025/06-08-25-1); [Coverager](https://coverager.com/hiscox-to-acquire-mga-and-carrier-operations-from-vouch/)
- **Thimble**: on-demand GL / inland marine / PL (by the hour, month, or year). The Thimble API offers embedded policies and real-time certificates — [Thimble API page (search snippet; page 403)](https://www.thimble.com/api); [Thimble Partner](https://www.thimble.com/partner). Herald lists GL, Inland Marine, PL — [Herald Index](https://www.heraldai.com/insurance-api-index)
- **biBERK (Berkshire Hathaway Direct)**: no public API found. It does **not appoint individual retail agents**. It distributes through select wholesaler partners (e.g., London Underwriters), which can quote, bind, and issue on the biBERK platform — [biBERK Become a Partner](https://www.biberk.com/become-a-biberk-partner); [London Underwriters](https://www.londonuw.com/insurtech/biberk-agent-login)
- **Chubb**: *Chubb Studio* is a B2B2C developer portal (launched Nov 2023) with digital insurance APIs, mobile SDKs, and microsites for banks, fintech, e-commerce, and similar partners, mainly for embedded consumer and SME propositions — [Chubb press release](https://news.chubb.com/2023-11-14-Chubb-Studio-Expands-its-Digital-Integration-Capabilities-with-New-B2B2C-Developer-Portal); [Chubb Studio](https://www.chubb.com/us-en/partners/technology.html). *Chubb Marketplace* (2018) is the independent-agent small commercial quote/bind/service platform with API-enabled assets — [Insurance Journal](https://www.insurancejournal.com/news/national/2019/02/13/517524.htm). Herald lists Chubb BOP, Cyber, MPL, D&O, EPLI, Fiduciary, Crime, K&R — [Herald Index](https://www.heraldai.com/insurance-api-index)
- **Travelers**: developer portal at developer.travelers.com, with APIs for BI claim reporting, org & claims extract, commercial quoting, and policy management — [Travelers API Portal](https://developer.travelers.com/s/); [API Evangelist Travelers (third-party)](https://github.com/api-evangelist/travelers). For small commercial, the APIs return indications or fully bindable quotes for WC and other products. For middle market, agents send multiline submissions from their own systems. Travelers says its APIs connect to "virtually every major AMS and distribution platform" — [Travelers Sustainability Report](https://sustainability.travelers.com/drivers-of-sustained-value/customer-experience/supporting-our-agents-brokers)
- **Nationwide**: Nationwide Partnership Portal at developer.nationwide.com. It includes a "Commercial Quote" API (create, update, and retrieve quotes in the ExpressConnect2 contract app, JSON premium responses), a "Wholesale Express Protect Quote" API, and personal lines servicing APIs — [Commercial Quote API product](https://developer.nationwide.com/api-product/Commercial%20Quote); [Wholesale Express Protect Quote](https://developer.nationwide.com/api-product/Wholesale%20Express%20Protect%20Quote); [Product catalog](https://developer.nationwide.com/product-catalog). Herald lists Nationwide BOP, Commercial Auto, GL, Umbrella, WC, BA GL/Property — [Herald Index](https://www.heraldai.com/insurance-api-index)
- **The Hartford**: Spectrum BOP is for small accounts rated and bound without underwriter touch. CyberChoice First Response is embedded in the BOP (Dec 2025). No public developer portal was found; digital quote/bind is agent-facing — [IA Magazine](https://www.iamagazine.com/2025/12/08/the-hartford-bolsters-cyber-insurance-for-small-businesses/); [Hartford Specialty Digital](https://www.thehartford.com/commercial-insurance-agents/global-specialty-digital)

### Cited Findings — Aggregator index roster (carriers with API-enabled products)
Herald's index (86 carriers/MGAs, 228 products, 25 LOBs) — [Herald Insurance API Index](https://www.heraldai.com/insurance-api-index):
- Acuity (BOP, Comm Auto, GL, Package, Property, WC); Amlin (PL); AmTrust; Arch (BOP, Crime, Cyber, D&O, EPLI, Fiduciary, K&R, PL, Surety); At-Bay; Ategrity (BA GL/Prop); Atlantic Casualty (GL, IM, Package, Property); Axis (Cyber, PL, Tech E&O); **BTIS** (GL; BTIS is Liberty Mutual-affiliated); Beazley (Cyber, PL); Berkley (Crime, Cyber, D&O, EPLI, Fiduciary); Brit (Cyber); Blitz (GL, Property, Special Events); Burlington/IFG; Canopius (Cyber); CapSpecialty; Catlin XL (Cyber, BA); CBIC/RLI (BOP, GL); Century Surety; CFC (Cyber, D&O, PL, Tech E&O, Transactional); Chubb; Cincinnati (BOP, GL, WC); CNA (BOP, GL, WC); Coaction Specialty; Coalition (Cyber, D&O, EPLI, Tech E&O); Colony; Convex (MPL); Corvus; Coterie; Counterpart (Crime, D&O, EPLI, Fiduciary, PL); Cowbell; Crum & Forster (Cyber, BA); Elpha Secure (Cyber); EMPLOYERS (WC); General Star; Great American (BOP, WC, BA); Great Lakes; Hallmark; Hartford Steam Boiler (BOP, GL, WC); Hiscox; Homesite (GL); Hudson; IAT; James River; Liberty Mutual (BOP, GL, WC); Main Street America (BOP, Comm Auto, Package, Umbrella, WC); **Markel** (Contractors Pollution, Excess, GL, Special Events, PL, RIA E&O, WC, BA GL/Prop/IM); MUSIC; Nationwide; Nautilus; Northfield; Pathpoint (Cyber, Excess, GL, Package, Property); Pie (WC); Pouch (Comm Auto); RSUI; Seneca; **Sompo** (Cyber); StarStone; State Auto (WC); Thimble; USLI (BOP, GL, Umbrella, BA); WCF (WC); Western World/AIG (BA GL/Prop); Westfield (BOP, Comm Auto, GL, WC); Zip Bonds (Surety).
- CoverForce 2026 index (partial view): Accident Fund (WC, live), Acuity, AmTrust (live), Arch, At-Bay, Ategrity (BOP, GL, Property), Atlantic Casualty, **Attune (WC)**, Axis, Beazley, Berkley Mgmt Protection, BerkleyNet (WC, live) — [CoverForce API Index](https://www.coverforce.com/carriers/api-index)
- CoverWallet (Aon) offers its own API for embedding business insurance. Its 2018 carrier panel included Liberty Mutual, CNA, Starr, Chubb, Blackboard (AIG), Guard, Markel, Employers, Travelers, Progressive, Hiscox, and Atlas — [Insurance Journal 2018](https://www.insurancejournal.com/news/national/2018/06/27/493386.htm) (stale; Blackboard was shut down by AIG in 2020 — verify panel currency)

### Cited Findings — Status changes / stale offerings
- **Vouch**: sold its MGA (Corix) and carrier to Hiscox (announced Aug 2025) and is now a broker only — [Hiscox PR](https://www.hiscoxgroup.com/news/press-releases/2025/06-08-25-1)
- **Attune**: acquired by Coalition — [Coverager "Coalition acquires Attune"](https://coverager.com/coalition-acquires-attune/) (page 403; date and API continuity not verified)
- **Corvus**: now inside Travelers — [Seedpod](https://seedpodcyber.com/cyber-insurance-carrier-comparison/)
- **NEXT Insurance** rebranded as ERGO NEXT (ERGO/Munich Re ownership) — [API Evangelist (third-party)](https://github.com/api-evangelist/next-insurance)

### Inferences
- Rough ordering of access openness:
  - Most open: public docs plus a sandbox (Coterie, At-Bay, Coalition sandbox, Nationwide portal, Travelers portal, Chubb Studio).
  - Next: credentialed partner API with docs on request (Pie, AmTrust, Cowbell, Hiscox).
  - Next: partner-program only with no public docs (ERGO NEXT Connect, Thimble).
  - Least open: no direct API, access only via wholesalers or aggregators (biBERK, most regional carriers).
- For carriers that are "API-enabled" only via Herald or CoverForce, the practical integration path for a non-agency developer is to go through a licensed aggregator (Herald, CoverForce, Bold Penguin, Semsee, Tarmika, Appulate) rather than each carrier directly.

### Gaps
- Could not verify API programs for: Guard (Berkshire), Hanover, Kinsale, Zurich, AIG (direct), Simply Business, Society/Sompo (beyond Sompo cyber on Herald), Steadily, Obie, Openly (commercial), Employers' Cerity (direct-to-consumer, likely discontinued/folded — unverified), Markel Digital (formerly State National/Markel direct portal), Embroker (no partner API found). No reliable sources were found in this pass.
- The Herald list returned 65 of the claimed 86 carriers, so the page may be truncated. The CoverForce list was truncated at 12 ("Show more").
- The Travelers portal is JS-rendered, so its catalog of commercial quote APIs could not be enumerated.

## Q4: Which require agency appointment/producer license vs. open to tech partners?

### Takeaway
Selling or binding insurance for compensation in the US requires a producer license. Every carrier API reviewed assumes the caller is a licensed, usually appointed, agency/broker **or** a contracted partner under a partner agreement. None is open to anonymous developers for production binding. Some publish docs and sandboxes openly.

### Cited Findings
- Coterie: "appointed agents and digital partners" — [Coterie docs (via search) / API Evangelist](https://github.com/api-evangelist/coterie)
- Coalition: licensed brokers and digital platforms, with sandbox provided — [Coalition](https://www.coalitioninc.com/brokers/api)
- At-Bay: brokers, tech companies, and partners, with production BOR clearance. Public docs and demo env — [At-Bay docs](https://developers.at-bay.com/docs/getting-started)
- Pie: credentials on request and API Terms of Use — [Pie](https://www.pieinsurance.com/agency/api)
- ERGO NEXT: partner program only, bilateral pricing, no public docs or sandbox — [Supergood (third-party)](https://supergood.ai/api-report-card/next-insurance)
- biBERK: no retail appointments. Wholesalers only — [biBERK](https://www.biberk.com/become-a-biberk-partner)
- Chubb Studio: B2B2C partners (banks, fintech, retail). Marketplace: appointed independent agents — [Chubb](https://news.chubb.com/2023-11-14-Chubb-Studio-Expands-its-Digital-Integration-Capabilities-with-New-B2B2C-Developer-Portal); [Insurance Journal](https://www.insurancejournal.com/news/national/2019/02/13/517524.htm)

### Inferences
- A non-licensed tech company (e.g., a JARVIS-like assistant) would need one of three routes: (a) its own agency license, (b) an embedded partner or referral agreement with a carrier (NEXT Connect, Chubb Studio, Thimble, Coterie partner), or (c) a licensed aggregator/API platform that holds the appointments.

### Gaps
- Public commission or revenue-share figures were not found for any carrier. All appear to be negotiated under partner or agency agreements.
