# Personal-Lines Carriers and MGAs with Developer / Partner APIs (US, as of Sept 2026)

Scope note: about 25 search/fetch calls. Several carrier portals (lemonade.com/api, developer.nationwide.com) returned HTTP 403 to automated fetch, so some details come from search snippets or third-party profiles (API Evangelist GitHub profiles, apis.io). Treat those as secondary sources. Nothing below comes from memory without a label. Commission figures were not public for any carrier checked.

## 1. Which personal-lines carriers and MGAs have a real developer or partner API, and what does each offer?

### Takeaway
There are real, documented personal-lines APIs, but almost all are gated partner programs, not self-serve public APIs. The strongest cases with published docs are Branch (public GraphQL docs plus a staging sandbox), Steadily (public ReDoc), Ladder (public GitHub-hosted docs), Neptune Flood (published Quick Quote v4 docs), Progressive (developer portal plus an embedded-integrations onboarding site) and Lemonade (public API doc portal). Everyone else (Root, Clearcover, Hippo, Openly, Ethos, Bestow, Trupanion, Assurant, Obie, Jetty) gives access only through a partnership agreement.

### Cited Findings

**Auto**
- **Progressive**: runs a developer portal at developer.progressive.com with the "Embedded Direct" auto-quoting API. Partners also get Commercial Auto Quoting and a Certificate of Insurance API. — [apis.io Progressive](https://providers.apis.io/providers/progressive/); [Progressive Developer Portal – EmbeddedDirectAPIDoc](https://developer.progressive.com/s/embeddeddirectapidoc)
  - An onboarding site (integrations.progressive.com) lists three embedded products. The first is **Auto** ("embedded auto insurance rate estimate in your car shopping platform"). The second is **Digital Mortgage / Homeowners** ("embedding home insurance into the mortgage process"). The third is **Renters** ("renters insurance into your lease platform"). — [Progressive Embedded Integrations](https://integrations.progressive.com/)
  - The auto product returns an *estimated* rate from vehicle and consumer data. It can be delivered as an SDK or a headless API, and it covers all 50 states. Partners get flexibility in how the rate is displayed, and the consumer finishes the purchase online, typically on Progressive's side. — [Progressive Auto Integration](https://integrations.progressive.com/auto/) (via search snippet); [Embedded Direct API onboarding PDF 2022](https://developer.progressive.com/cms/delivery/media/MCZANTULJTYVHILN6ZEELMHZTJXE)
  - The onboarding pages do not mention partner-side bind, commission terms or state details. — [Progressive Embedded Integrations](https://integrations.progressive.com/)
- **Root Insurance**: its tech stack is built around APIs for embedded auto with partners such as Carvana and Hyundai Capital America. The partner APIs are gated and have no public docs. — [apis.io Root Insurance](https://apis.io/providers/root-insurance/)
  - With Carvana, customers quote and bind a Root policy inside the Carvana checkout ("Carvana Insurance Built with Root", launched in 2022). The program passed 200,000 policies in April 2026 and the agreement was extended in September 2026. — [Carvana IR, Apr 14 2026](https://investors.carvana.com/news-releases/2026/04-14-2026-140928073); [GlobeNewswire, Sep 1 2026](https://www.globenewswire.com/news-release/2026/09/01/3354591/22064/en/root-insurance-and-carvana-extend-embedded-insurance-agreement.html)
  - A former Carvana insider credits Root's "45-second quote API" and its willingness to write all risks as the reason it won the Carvana deal. — [In Practise interview](https://inpractise.com/articles/carvana-root-and-embedded-insurance-moat)
  - Root also has an embedded deal with Hyundai Capital America (April 2025). — [Carrier Management](https://www.carriermanagement.com/news/2025/04/04/273836.htm)
- **Clearcover**: runs an embedded strategy that includes partners such as Experian, offering bindable quotes to consumers shopping for auto. No public API docs were found. — [IIReporter](https://iireporter.com/embedded-insurance-approaches-tipping-point/)

**Home / Auto / Umbrella bundles**
- **Branch Insurance**: offers a public "Quote to Bind" GraphQL API with docs at docs.v2.api.ourbranch.com. — [Branch API Docs](https://docs.v2.api.ourbranch.com/)
  - Main calls:
    - `requestQuoteV2` starts a quote.
    - `recalculateQuoteV2`, `addCar` and `addDriver` customize the offer.
    - `requestBind` purchases the policy.
    - After bind, partners can retrieve the policy and its documents.
  - Access and environments:
    - Authentication is an API key in the Authorization header, plus an `x-affinity-code` header for partners that use several affinity codes.
    - A staging sandbox runs at staging.v2.api.ourbranch.com, with test users and test payment methods.
    - Calls prefixed "Enhanced" and `retrieveOfferData` return PII-level data (DOB, license numbers), and access to them is granted per partner.
  - Partners can hand the customer off to Branch at any step (customize, review, checkout, signing) using a URL of the form `ourbranch.com/offer/{offerId}?redirect={step}`, and attribution is kept.
  - Branch can send webhooks for bind and signing events, or scheduled reports instead. Setup goes through api@ourbranch.com.
  - — [Branch API Docs](https://docs.v2.api.ourbranch.com/)
  - Lines covered are home, auto, renters and umbrella. Target partners are mortgage originators, lenders and aggregators. Branch operates as the Branch Insurance Exchange, a reciprocal insurer. — [API Evangelist: branch](https://github.com/api-evangelist/branch); [API Evangelist: branch-insurance](https://github.com/api-evangelist/branch-insurance)

**Home (HO / condo / renters)**
- **Lemonade**: publishes a "Lemonade Insurance API" so websites and apps can offer renters and homeowners insurance, with partners earning revenue share or "passive revenue". A doc portal exists at api-doc-portal.lemonade.com. The pages returned 403 to automated fetch, so capabilities, sandbox status and commission could not be verified. — [Lemonade API page](https://www.lemonade.com/api); [Lemonade API doc portal](https://api-doc-portal.lemonade.com/); [Lemonade blog: Introducing the Lemonade Insurance API](https://www.lemonade.com/blog/introducing-lemonade-insurance-api/)
  - Name-collision warning: "Lemonade Server" (lemonade-server.ai, a local-LLM tool) and "Lemonade Payments" (docs.mylemonade.io) have nothing to do with the insurer. — [Lemonade Server docs](https://lemonade-server.ai/docs/api/lemonade/); [Lemonade Payments](https://docs.mylemonade.io/)
- **Openly**: offers REST APIs for homeowners quote, bind, endorsements and renewals. Access is partner-only for appointed independent agencies, so it is an agency-channel API rather than an embedded or public one. — [API Evangelist: openly](https://github.com/api-evangelist/openly) (third-party profile)
- **Hippo**: sells homeowners insurance, with landlord, flood, pet and auto available through 70+ carrier partners. Its embedded channel runs through the Hippo Builders Program (Lennar since 2019), which puts insurance into mortgage and title closings. Other partners include ADT. No public API docs were found. — [API Evangelist: hippo-insurance](https://github.com/api-evangelist/hippo-insurance); [Hippo blog: new home closings](https://www.hippo.com/blog/streamlining-new-home-closings-with-embedded-insurance); [BusinessWire 2021 builders program](https://www.businesswire.com/news/home/20210915005400/en/Hippo-Partners-with-Leading-U.S.-Home-Builders-to-Introduce-First-of-its-Kind-Program-Making-Home-Insurance-Purchases-Simpler-and-Faster)
- **Nationwide**: runs a partner portal at developer.nationwide.com. It includes a "Personal Lines Servicing" API product and the Insurance Verification Digital Product (2021), which lets a verified user confirm whether a customer holds a Nationwide homeowners, condo or renters policy and verify its details in real time. Assurant is a named user. — [Nationwide newsroom](https://news.nationwide.com/new-solution-makes-verifying-homeowners-insurance-seamless/); [Nationwide portal: Personal Lines Servicing](https://developer.nationwide.com/api-product/Personal%20Lines%20Servicing); [Nationwide product catalog](https://developer.nationwide.com/product-catalog)
  - Nationwide sold renters insurance through the Sure platform in the past (quote, purchase and premium payment in the Sure app). — [Retail Dive](https://www.retaildive.com/ex/mobilecommercedaily/nationwide-brings-renters-insurance-to-millennials-on-the-go)

**Landlord / investor property**
- **Steadily**: its Partner API has three tiers:
  1. co-branded no-code widgets;
  2. an embedded quote *estimate* (prefill or address only);
  3. a full REST API for licensed partners, covering real-time quotes, **binding** and policy status.
  - It also offers a tracking and data feed covering bound policies, mortgagee and additional-insured listings, and cancellation notifications.
  - Public docs are at https://api.steadily.com/redoc.
  - The agency is licensed in all 50 states plus DC. Commission is not published.
  - — [Steadily Partner API](https://www.steadily.com/api)
- **Obie**: offers "developer-friendly APIs" for landlord and investment-property insurance (single-family and multifamily). It is licensed in 50 states, DC and some territories. Access is by request only, and neither docs nor commission terms are public. — [Obie API](https://www.obieinsurance.com/api); [Obie Embedded](https://www.obieinsurance.com/embedded-insurance)

**Flood**
- **Neptune Flood**: publishes the "Quick Quote v4" API docs at latest-apidocs.neptuneflood.com. The page content could not be extracted. — [Neptune API docs](https://latest-apidocs.neptuneflood.com/)
  - The Quick Quote API is meant to be embedded in outside quoting systems. It returns a quick qualification and quote plus a deep link into the Neptune Agent Portal, where the user is authenticated automatically and finishes the application and bind in under 2 minutes. Bind therefore happens in Neptune's portal, not through the API. — [Neptune S-1 (SEC)](https://www.sec.gov/Archives/edgar/data/2067129/000162828026033573/neptuneflood-sx1.htm) (via search snippet)
  - Scale reported in the S-1 through March 31, 2026:
    - more than 20,000 quotes per day from distribution partners;
    - about 34.4M lifetime quotes and 1.4M binds;
    - 96.8% of policies in force came through partnerships;
    - more than 25,000 agency codes have bound a policy.
  - Plymouth Rock connects to Neptune through an API link into its AI engine.
  - — [Neptune S-1](https://www.sec.gov/Archives/edgar/data/2067129/000162828026033573/neptuneflood-sx1.htm)
  - In March 2026 Neptune launched a quoting app inside ChatGPT. — [FinTech Global](https://fintech.global/2026/03/13/neptune-flood-launches-insurance-quoting-app-in-chatgpt/)

**Renters / deposit alternatives**
- **Assurant**: runs APEX (Assurant Product Experience Exchange), which offers embedded APIs for renters enrollment, policy management and claims inside property-management platforms. Its developer portals run on Azure API Management, at housing-apis.developer.assurant.com and api-prod.portal.assurant.com. — [Assurant APEX Global Housing](https://www.assurant.com/partner-with-us/apex/global-housing); [Assurant housing dev portal](https://housing-apis.developer.assurant.com/); [Assurant dev portal](https://api-prod.portal.assurant.com/)
- **Jetty**: integrates by API with Yardi, RealPage and Entrata at lease signing. It is a PMS integration, not a public developer API. — [CB Insights / search snippet](https://www.cbinsights.com/company/jetty/alternatives-competitors)
- **LeaseLock**: has no public API, developer portal, OpenAPI description or SDKs. PMS integration is set up as a managed engagement. — [API Evangelist: leaselock](https://github.com/api-evangelist/leaselock)
- **Rhino, Jetty, LeaseLock**: Yardi has partnered with all three (and with ResidentShield) over the years. — [Coverager](https://coverager.com/yardi-partners-with-obligo/)

**Life**
- **Ladder**: offers an embedded term-life API with public docs on GitHub Pages at ladderlife.github.io/api. It is mainly a client-side JS integration:
  1. the partner loads Ladder's v3 bundle;
  2. the partner's backend mints a user auth token;
  3. a Ladder flow is mounted in the partner's page.
  - Integration depth runs from simple promotion to a fully embedded white-label experience. The underwriting carriers are Amica Life, Fidelity Security Life and S.USA Life / Prosperity. — [Ladder API reference](https://ladderlife.github.io/api/); [Ladder Embedded API: application](https://ladderlife.github.io/api/application); [Ladder API page](https://www.ladderlife.com/api); [API Evangelist: ladder](https://github.com/api-evangelist/ladder)
- **Ethos**: its partnership APIs cover customized quotes, the interview, instant underwriting, collecting policy and billing information, and generating signed policy documents, so a full quote-to-issue flow. Products include term, whole life, IUL, final expense and guaranteed issue. Access is by request only, with no public docs or compensation terms. — [Ethos API](https://www.ethos.com/api/); [Ethos engineering blog](https://www.ethos.com/tech-and-ethos/partnership-apis-at-ethos/)
  - Liberty Mutual partnered with Ethos in April 2026. — [FinTech Global](https://fintech.global/2026/04/27/liberty-mutual-partners-ethos-to-expand-digital-life-insurance-offering/)
- **Bestow**: the Protect API ranges from coverage estimates to a fully hosted end-to-end term-life purchase. It collects underwriting data, returns an instant decision and issues the policy inside the partner's app. Access comes through partnership agreements, and a no-code "Protect Web" can launch in a day. Bestow now also sells SaaS to life carriers (new business, policy admin, TPA services). — [Bestow Protect API press release](https://www.prnewswire.com/news-releases/bestow-launches-protect-api-bringing-100-digital-life-insurance-to-partners-301168094.html); [Bestow API partners](https://www.bestow.com/api-partners/); [API Evangelist: bestow](https://github.com/api-evangelist/bestow)
- **Haven Life (MassMutual)**: **discontinued**. It stopped taking applications on Jan 12, 2024 and stopped issuing policies on Mar 31, 2024. MassMutual reintegrated Haven Technologies. — [Policygenius](https://www.policygenius.com/life-insurance/reviews/haven-life/); [Coverager](https://coverager.com/massmutual-to-shut-down-haven-life-by-the-end-of-the-year/); [Insurance Business](https://www.insurancebusinessmag.com/us/news/breaking-news/massmutual-to-reintegrate-haven-technologies-cut-65-jobs-511570.aspx)

**Pet**
- **Trupanion**: runs a partner developer portal on Azure API Management with Partner APIs for Quotes, Enrollments and Offers. It also offers a Vet Portal / VetDirectPay integration used by practice-management systems (ezyVet, IDEXX, DaySmart Vet).
  - Access requires approval through the Partner Program. Approved partners get OAuth client credentials plus a subscription key.
  - There is no public API reference and no metered pricing.
  - — [API Evangelist: trupanion](https://github.com/api-evangelist/trupanion) (third-party profile)
- **Embrace and Fetch**: no partner API information was found.

**Discontinued or stale**
- **Toggle (Farmers)**: Farmers is shutting down the Toggle renters brand. — [NerdWallet](https://www.nerdwallet.com/insurance/renters/toggle-renters-insurance-review)
- **Haven Life**: discontinued in 2024 (see Life above).

### Inferences
- **Access tiers.** Partner access falls into three tiers:
  - *Documented, sandbox-able APIs:* Branch, Steadily, Ladder, Neptune, Progressive, Lemonade, probably Assurant.
  - *Gated embedded partnerships:* Root, Clearcover, Hippo, Ethos, Bestow, Obie, Trupanion.
  - *PMS or agency integrations only:* Jetty, LeaseLock, Openly.
- **Where bind happens.** Direct API bind is confirmed only for Branch, Steadily (licensed partners), Ethos and Bestow (issue), and Root through its Carvana checkout. Progressive and Neptune return an estimate or quote, then hand the user off (deep link or redirect) to finish the purchase.
- **Access model.** Embedded and affinity programs usually make the partner a licensed referral agent or pay a marketing fee. The exact model and commission were not published by any carrier checked.

### Gaps
- No public commission or revenue-share figures were found for any carrier.
- Lemonade API capabilities (bind, webhooks, sandbox, states) could not be verified because the pages returned 403.
- Nationwide's product catalog could not be fetched because it returned 403.
- Neptune's docs content could not be extracted.
- Kin, Swyfft, Sure (platform status in 2026), Embrace and Fetch: no API evidence found in this pass.

## 2. Which major and legacy carriers have no public API, or are reachable only through comparative raters or agency channels?

### Takeaway
No public developer API was found in this research for GEICO, State Farm, Allstate, Safeco (Liberty Mutual), Travelers personal lines, Mercury, National General, Foremost, Plymouth Rock, Dairyland, Bristol West, Stillwater or Universal Property. For these carriers, programmatic access in personal lines usually goes through agency comparative raters and ACORD / IVANS-style connectivity, not an open API.

### Cited Findings
- Personal-lines carriers have offered API access to agencies for more than a decade through ACORD XML and IVANS. Comparative raters typically connect to 15–40 carriers per state, but how many connect by real-time API versus a "bridge" varies by state and carrier. — [Fern blog](https://buildwithfern.com/post/insurance-carriers-build-api-partner-portals) (vendor blog; secondary)
- Aggregator APIs, such as Zywave's Personal Lines Quoting API and Bindable's API, are a way to reach many carriers without a direct connection to each one. — [Zywave Personal Lines Quoting API](https://www.zywave.com/personal-lines/sales-cloud/personal-lines-quoting-api/); [Bindable API](https://api.bindable.com/)
- The Herald Insurance API Index lists 86 carriers and MGAs with 228 API products, all **commercial** lines, and no personal-lines entries. It is not a useful source for personal lines. — [Herald Insurance API Index](https://www.heraldai.com/insurance-api-index)
- A search for Allstate, Safeco or Travelers embedded or partner APIs returned only consumer comparison pages and rater-vendor listings, such as the NASA rating integration partners page. — [NASA Rating Integration Partners](https://www.nasasoft.com/integrations/rating-integration-partners)
- Plymouth Rock uses Neptune's API for flood. This is Plymouth Rock consuming a partner API, not exposing one. — [Neptune S-1](https://www.sec.gov/Archives/edgar/data/2067129/000162828026033573/neptuneflood-sx1.htm)

### Inferences
- GEICO, State Farm and Allstate are captive or direct carriers. The absence of any developer-portal evidence fits the expectation that they have no public quoting API. Unconfirmed: there is no primary statement that says so.
- Safeco, Travelers, Mercury, National General, Foremost, Dairyland, Bristol West and Stillwater are agency-channel carriers. Their integration path is most likely a comparative rater (EZLynx, PL Rating / Vertafore, ITC TurboRater, Zywave) under an agency appointment. That is rater access, not a true public API.

### Gaps
- No primary confirmation was found either way for GEICO, State Farm, Allstate, Mercury, National General, Foremost, Dairyland, Bristol West, Stillwater or Universal Property. It is also unknown whether Allstate or Travelers have private embedded APIs, such as for auto OEMs or dealers.
- Not investigated because of the budget: Kin, Swyfft, Sure, Embrace, Fetch, and other insurtechs such as Openly-for-agents details, Kin's partner channel, and Hippo's agent API.
