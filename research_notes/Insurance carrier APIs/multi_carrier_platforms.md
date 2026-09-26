# Multi-Carrier Insurance APIs: Comparative Raters, Quoting Marketplaces, and Agency Connectivity Platforms (US, as of Sept 2026)

Research budget was about 18 tool calls, so coverage is uneven. Several sources are secondary: API Evangelist GitHub profiles, and vendor-comparison blogs such as QuoteSweep, InsurAItools, Sonant and US Tech Automations, some of which sell competing tools. These are labeled where they are used. Anything that could not be verified is listed under Gaps.

## Catalog: which aggregator platforms exist, and what does each offer (carriers, lines, capabilities, API access, license requirement, docs)?

### Takeaway
The market splits into four groups. (1) Agent-facing comparative raters and connectivity platforms: Applied (EZLynx, Tarmika, Ivans, Ask Kodiak, Indio, Epic), Vertafore (PL Rating, AMS360, Sagitta, QQCatalyst), Zywave/ITC TurboRater, HawkSoft, Semsee, Appulate, Bold Penguin and Relay. These are all partner-gated and assume a licensed agency as the end user. (2) Consumer quoting marketplaces and lead-gen networks: EverQuote, MediaAlpha, SmartFinancial, The Zebra, Insurify, Gabi and Policygenius. These make money from referrals and leads, and a non-licensed publisher can join through affiliate or embed programs. (3) Embedded home and auto marketplaces: Matic. (4) Commercial and E&S digital wholesalers: Pathpoint, CoverWallet and Bold Penguin. Applied Systems has consolidated much of group (1): it owns Ivans, Ask Kodiak (bought 2021), Tarmika (2022), EZLynx and Indio.

### Cited Findings

**Bold Penguin (Terminal, Exchange, and DeX ai APIs). Commercial lines.**
- Terminal connects agents to 45+ carriers, including Nationwide, Liberty Mutual, Travelers, Chubb and biBERK, through API partnerships for multi-carrier quoting. This comes from a secondary comparison site. — [InsurAItools](https://www.insuraitools.com/compare/bold-penguin-vs-tarmika)
- Bold Penguin launched DeX ai on Sept 24, 2026:
  - Partners get documented **submission, quote, and bind endpoints**, an **MCP server** that lets partners' AI agents use DeX ai as a tool, and agent-to-agent placement.
  - Over the prior 12 months, $12.45B of premium moved across the exchange on more than 735,000 submissions.
  - Eight of the ten largest US commercial carriers build on the platform.
  - Access is for carriers, brokers and platform partners. The release gives no pricing or sandbox information.
  - Source: [PR Newswire](https://www.prnewswire.com/news-releases/bold-penguin-launches-dex-ai-the-intelligence-running-its-digital-exchange-302889677.html)
- Bold Penguin previously announced a Developer Portal. The announcement page now returns a 404, so its current status is unverified. — [Bold Penguin news (dead link)](https://www.boldpenguin.com/news/introducing-our-developer-portal)
- Capterra lists API access, access controls and user management as features. — [Capterra](https://www.capterra.com/p/10020162/Bold-Penguin/)

**Tarmika (Applied Systems). Small commercial comparative rater.**
- Applied Systems acquired Tarmika in August 2022. Tarmika is integrated with Applied Epic and EZLynx. Applied planned to embed Tarmika commercial quoting natively in its management systems, and Tarmika's panel of carrier products was integrated into the Ivans Distribution Platform (IDP). — [Applied press release](https://www1.appliedsystems.com/en-us/news/press-releases/2022/applied-systems-acquires-tarmika/); [Insurance Journal](https://www.insurancejournal.com/news/national/2022/08/16/680700.htm)

**Ivans (Applied). Download and connectivity, with Ask Kodiak appetite data.**
- The Ivans division of Applied acquired Ask Kodiak on Aug 10, 2021:
  - Ask Kodiak provides commercial lines appetite, eligibility and product search.
  - The platform is API-enabled.
  - Agencies on commercial quoting solutions supported by the Ivans Distribution Platform get Ask Kodiak appetite matching.
  - The release says the business serves more than 20,000 agencies and handles more than 8 million home, auto and package rating transactions per month.
  - Source: [Ivans press release](https://www.ivans.com/news/press-releases/2021/ivans-acquires-ask-kodiak/); [Carrier Management](https://www.carriermanagement.com/news/2021/08/10/224649.htm)
- Ask Kodiak is now sold as an Ivans carrier product. — [Ivans: Ask Kodiak for Carriers](https://www.ivans.com/for-carriers/products/ask-kodiak/)
- Semsee integrated Ask Kodiak appetite and eligibility data into its single smart form. — [PR Newswire](https://www.prnewswire.com/news-releases/semsee-and-ask-kodiak-partner-to-power-agents-new-business-submissions-in-commercial-lines-301224702.html)

**Applied Epic API.**
- The API is a REST developer platform at the Applied Dev Center (devcenter.myappliedproducts.com). It uses OAuth 2.0 and supports reading and writing clients/accounts, policies, contacts, attachments and activities. — [APIs.io / API Evangelist (secondary)](https://apis.io/providers/applied-systems/)
- Access is gated: you register, build against a **sandbox**, then submit a production request that Applied must approve. — [APIs.io / API Evangelist (secondary)](https://apis.io/providers/applied-systems/)
- Applied runs a Certified Integrations ecosystem. — [Applied Certified Integrations](https://www1.appliedsystems.com/en-us/about-us/ecosystem/certified-integrations/)
- One third-party "API report card" gives Applied Epic's API a grade of F. This is an opinion from a vendor that sells integration services. — [Supergood](https://supergood.ai/api-report-card/applied-epic)

**EZLynx (Applied). Personal lines rater and AMS, with a rating API.**
- The API is partner- and enterprise-gated (contact sales, OAuth 2.0). There is no self-serve key. Access is granted per integration and scoped to the agency's own data. — [API Evangelist (secondary)](https://github.com/api-evangelist/ezlynx)
- Enterprise APIs cover applicants, contacts, prospects, policy headers, retrieval of quote results, and high-volume quoting through the **EZLynx Rating Engine and Quoting Automation Services (QAS)**. — [API Evangelist (secondary)](https://github.com/api-evangelist/ezlynx); [CoLab playbook](https://colabcontent.com/playbooks/ezlynx-ai-automation/)
- A comparison site says Epic has the more mature API and more integration partners, while EZLynx has the smaller third-party ecosystem. — [QuoteSweep (competitor blog)](https://www.quotesweep.com/blog/applied-epic-vs-ezlynx)

**Vertafore (AMS360, Sagitta, QQCatalyst, BenefitPoint, ImageRight, PL Rating; Orange Partner Program).**
- Vertafore launched its API Developer Portal and the Orange Partner Program in September 2016. — [Benzinga / PR](https://www.benzinga.com/pressreleases/16/09/p8472001/vertafore-launches-api-developer-portal-and-vertafore-orange-partner-pr)
- The Orange Partner Program is for solutions that integrate with QQCatalyst, AMS360, Sagitta, BenefitPoint or ImageRight. — [Vertafore blog](https://www.vertafore.com/resources/blog/get-know-vertafores-orange-partner-program)
- Access requirements (secondary source):
  - a Vertafore SSO account
  - a **licensed Developer Portal contract**
  - per-API scopes that the agency has contracted for
  - Apps move from Sandbox to Live only after Vertafore approves them.
  - Source: [API Evangelist (secondary)](https://github.com/api-evangelist/vertafore)
- PL Rating is a personal lines comparative rater connected to **more than 300 carriers across 48 states and DC**, with in-rater bind. It integrates with AMS360, Sagitta, QQCatalyst and more than 20 other management systems. The carrier count comes from a secondary source. — [Vertafore PL Rating](https://www.vertafore.com/products/insurance-comparative-rater/pl-rating); [API Evangelist](https://github.com/api-evangelist/vertafore)
- A public "Vertafore Rating API Reference" site exists. My fetch returned only section headings, not the content. — [rating-reference.vertafore.com](https://rating-reference.vertafore.com/)
- QQCatalyst is Vertafore's cloud AMS for personal lines and small commercial. It integrates with AgencyZoom and PL Rating. I found no announcement that it is being sunset. — [Capterra](https://www.capterra.com/compare/36109-158243/QQCatalyst-vs-AgencyZoom); [AgencyZoom support](https://support.agencyzoom.com/en/articles/4961876-qqcatalyst-integration)

**HawkSoft Partner API.**
- The program is open to technology providers serving US independent agents but **not open to competing AMS vendors**. Partners must pass a security risk assessment. — [HawkSoft partner portal](https://partner.hawksoft.app/getting-started/become-a-partner.html); [HawkSoft blog](https://blog.hawksoft.com/partner-api-3.0)
- Partner API v3.0 is designed for HawkSoft 6 (cloud) and remains compatible with HawkSoft 5. — [HawkSoft blog](https://blog.hawksoft.com/partner-api-3.0)
- Launching an integration takes about 11 steps, including business negotiation, a required pilot with a live agency, and co-marketing. Contact: opportunities@hawksoft.com. — [HawkSoft blog](https://blog.hawksoft.com/partner-api-3.0)
- The API has separate terms and conditions. — [HawkSoft API Terms](https://www.hawksoft.com/terms/api/)

**Zywave / ITC TurboRater.**
- Zywave acquired Insurance Technologies Corp. (ITC, maker of TurboRater) from Accel-KKR in November 2020. At the time, ITC served more than 250 insurance companies and more than 9,000 agencies, and TurboRater powered more than 2 million auto and home quotes. — [Zywave](https://www.zywave.com/blog/zywave-acquires-insurtech-frontrunner-itc-becomes-only-provider-to-offer-front-office-solutions-for-independent-insurance-agencies-across-all-lines-of-business/); [TurboRater release](https://www.turborater.com/release/2020/11/24/zywave-acquires-insurtech-frontrunner-itc-becomes-only-provider-to-offer-front-office-solutions-for-independent-insurance-agencies-across-all-lines-of-business)
- Zywave also bought the IBQ comparative rater in July 2021. — [Insurance Journal](https://www.insurancejournal.com/news/national/2021/07/01/620902.htm)

**Semsee. Small commercial SEMCI rater.**
- Semsee connects independent agents to 50+ carriers and MGAs across multiple lines, using **both API and RPA** integrations. — [API Evangelist (secondary)](https://github.com/api-evangelist/semsee); [Semsee carriers page](https://semsee.com/carriers-mgas-semsee)

**Appulate. Submission connectivity for agents, MGAs and carriers.**
- Appulate converts uploaded ACORD forms into structured XML and bridges the data into carrier portals and back-end systems. — [InsurAItools (secondary)](https://www.insuraitools.com/compare/appulate-vs-semsee); [Appulate for Carriers help](https://help.appulate.com/en/knowledge/appulate-for-carriers)

**Relay Platform. Broker-to-carrier multi-line quoting.**
- Relay describes itself as a single-entry, multi-carrier comparative rater for all P&C lines. It supports both instant API quoting and email quoting, and carriers include Cowbell Cyber and Measured for cyber. — [Cowbell PR](https://cowbell.insure/news-events/pr/instant-api-quoting-for-cyber/); [Insurance Business](https://www.insurancebusinessmag.com/us/news/breaking-news/relay-platform-rolls-out-new-digital-quoting-solution-436408.aspx); [Relay blog](https://blog.relayplatform.com/measured-insurance-joins-forces-with-relay-platform-to-provide-brokers-with-additional-cyber-capacity)
- Relay says it facilitated more than $1.2B in coverage after launching in April 2020. Its LinkedIn page is on the Canadian domain, which suggests Canadian roots and US reach that I could not confirm. — [Coverager](https://coverager.com/relay-partners-with-insurercore/); [LinkedIn](https://ca.linkedin.com/company/relayplatform)

**Pathpoint. Digital E&S wholesaler for small commercial.**
- Retail agents get bindable small commercial E&S quotes from multiple A-rated carriers in minutes. — [Pathpoint](https://www.pathpoint.com/)
- Pathpoint has raised about $49.4M; the latest round was a $12.5M Series A in January 2023. — [Tracxn](https://tracxn.com/d/companies/pathpoint/__Fg5SYAxj_WziFyNs53192Z6L1c_gb2MLtFBMYDmCGhs); [Beinsure](https://beinsure.com/news/pathpoint-raised-12-mm-for-es-insurtech-platform/)

**CoverWallet (Aon). Small business insurance marketplace.**
- Aon completed the acquisition in January 2019. — [Aon](https://aon.mediaroom.com/2019-01-07-Aon-completes-acquisition-of-CoverWallet-the-leading-digital-insurance-platform-for-small-and-medium-sized-businesses)
- A REST API for quoting, binding and managing multi-carrier small business policies is described by third parties. It covers GL, BOP, professional liability and more. — [API Evangelist (secondary)](https://github.com/api-evangelist/coverwallet); [FintegrationFS](https://www.fintegrationfs.com/fintechapis/cover-wallet-api)
- CoverWallet partnered with Cover Whale on trucking insurance. — [FF News](https://ffnews.com/newsarticle/insurtech/cover-whale-and-aons-coverwallet-to-expand-comprehensive-trucking-insurance-access/)

**Federato.**
- Federato is an AI-native **underwriting platform for insurers**. It is not a distribution aggregator. — [Federato](https://www.federato.ai/platform-overview)

**Ignyte.**
- Ignyte Insurance launched in April 2025 after NSM's US commercial business was sold to New Mountain. It is a **specialty MGA/brand platform**, with brands such as collector car and travel medical and more than $650M of premium, not a multi-carrier API marketplace. — [PR Newswire](https://www.prnewswire.com/news-releases/introducing-ignyte-insurance-a-bold-new-platform-powering-growth-in-specialty-insurance-302431186.html); [Insurance Journal](https://www.insurancejournal.com/news/national/2025/04/22/820766.htm)
- It acquired the travel marketplace InsureMyTrip in September 2026. — [The Insurer](https://www.theinsurer.com/ti/news/ignyte-insurance-acquires-travel-marketplace-insuremytrip-2026-09-02/)

**Matic. Embedded home and auto marketplace.**
- Matic's marketplace covers **70+ carriers in all 50 states**, with instant quotes from about 45 A-rated carriers. — [Matic partners](https://matic.com/partners/)
- Matic built custom APIs to its carriers. — [Basis Theory case study](https://blog.basistheory.com/customer-story/matic)
- Matic has 100+ lender, servicer and bank partners, which it says handle 20% of US home loans. Named embed partners include Floify (June 2025) and PRMG. — [Matic](https://matic.com/partners/); [GlobeNewswire](https://www.globenewswire.com/news-release/2025/06/11/3097747/0/en/Matic-Launches-Strategic-Partnership-With-Floify-Bringing-Insurance-Into-the-Digital-Loan-Experience.html)

**Consumer and lead-gen marketplaces.**
- **MediaAlpha** offers an "Embedded Quote Experience": a customizable, turnkey monetization product that returns rates and side-by-side comparisons in real time. It also has publisher APIs and call integrations. — [MediaAlpha Embedded Quote](https://mediaalpha.com/embedded-quote-experience/); [MediaAlpha publishers](https://mediaalpha.com/publishers/)
- **SmartFinancial** supports pay-per-lead, pay-per-call and pay-per-click models, plus hosted forms, JS embeds, ping-post and API setups. This comes from a secondary affiliate-marketing blog. — [Refgrow](https://refgrow.com/blog/auto-insurance-affiliate-programs)
- **EverQuote** has a partners program with call integrations and APIs. — [EverQuote Partners](https://www.everquote.com/partners/)
- **The Zebra** works with more than 50 auto carriers. It has a partners page, but I found no public partner API documentation. — [The Zebra partners](https://www.thezebra.com/about/partners/); [CB Insights](https://www.cbinsights.com/company/insurance-zebra)
- **Gabi** was acquired by Experian for $320M in November 2021. It still operates as a home and auto comparison platform. — [Coverager](https://coverager.com/experian-acquires-gabi-for-320-million/)
- **Policygenius** was acquired by Zinnia in 2023. It is strongest in life and disability. — [Blake Insurance Group (secondary)](https://blakeinsurancegroup.com/the-zebra-vs-policygenius/)

**ACORD Next-Generation Digital Standards (NGDS).**
- The standards are written in JSON and YAML but remain compatible with ACORD XML, and they are designed for microservices and REST APIs. Version 1.0 appeared as a candidate release in February 2020 and v1.1 in July 2020. — [ACORD NGDS 2020 announcement](https://www.acord.org/ACORD-about/acord-news/2020/02/10/introducing-acord-next-generation-digital-standards); [PR Newswire](https://www.prnewswire.com/news-releases/first-update-to-acord-next-generation-digital-standards-developed-in-collaboration-with-leading-insurance-organizations-301100982.html)
- The current version is **Final Release v1-13-0**, according to search snippets. — [ACORD NGDS page](https://www.acord.org/standards-architecture/acord-data-standards/next-generation-digital-standards)

### Inferences
- In practice, almost every multi-carrier **quote-and-bind** API reaches carriers through the carrier appointments of a **licensed agency**. That agency is either the platform's customer (Applied, Vertafore, HawkSoft, Semsee, Tarmika, Bold Penguin Terminal) or the platform itself acting as agency or wholesaler (Matic, CoverWallet, Pathpoint, Policygenius, Gabi).
- For ACORD XML and AL3 download data, the practical route is Ivans download into an AMS (Epic, AMS360, HawkSoft, and so on), followed by that AMS's partner API. A developer does not connect to Ivans directly. This is inferred from Ivans' role in the Applied ecosystem; I did not verify an Ivans developer API.
- The Applied roll-up (Ivans, Ask Kodiak, Tarmika, EZLynx, Indio, Epic) means one partner relationship with Applied covers a large share of independent-agency rating and connectivity.

### Gaps
- **Unverified or not researched for lack of budget:** Planck acquisition by Applied (only a PrivSource listing title was seen: [PrivSource](https://www.privsource.com/acquisitions/deal/applied-systems-acquires-planck-2VSdD4)), Indio API, Insurify partner API, Covered, Young Alfred, Goosehead, Simply Business US API, Federato funding, and ACORD AL3 specifics.
- **Pricing:** no public pricing was found for any platform. Vertafore requires a "licensed Developer Portal contract", with cost unknown.
- **Carrier and developer details:** exact current carrier counts for Tarmika, Appulate, CoverWallet and Pathpoint are missing. Bold Penguin's developer portal URL is currently a 404, and I could not confirm whether a sandbox exists.
- **Discontinuations:** I did not verify whether any named products (for example QQCatalyst or IBQ) have been discontinued.

## Which options are best for a small developer with no agency license?

### Takeaway
A small developer without a license cannot legally sell, solicit or bind insurance, and the agent-facing APIs (Applied, Vertafore, HawkSoft, EZLynx, Tarmika, Semsee, Bold Penguin) are partner-gated for software built for licensed agencies. The realistic unlicensed options are **referral, lead-gen and embed partnerships** where the platform's own licensed agency handles quoting and binding: MediaAlpha Embedded Quote, EverQuote and SmartFinancial affiliate or API programs, and Matic's embedded partner program for home and auto. A second option is to build *software for agencies* through the HawkSoft Partner API, the Applied Dev Center sandbox or the Vertafore Orange Partner Program, where the licensed agency is the end user.

### Cited Findings
- MediaAlpha's Embedded Quote Experience is a turnkey way for publishers to show real-time rates and comparisons. — [MediaAlpha](https://mediaalpha.com/embedded-quote-experience/)
- SmartFinancial supports JS embeds, hosted forms and API or ping-post lead delivery. — [Refgrow (secondary)](https://refgrow.com/blog/auto-insurance-affiliate-programs)
- EverQuote has a partner and affiliate program with APIs. — [EverQuote Partners](https://www.everquote.com/partners/)
- Matic embeds a 70+ carrier marketplace into partners' flows, such as the Floify loan platform. — [Matic](https://matic.com/partners/); [GlobeNewswire](https://www.globenewswire.com/news-release/2025/06/11/3097747/0/en/Matic-Launches-Strategic-Partnership-With-Floify-Bringing-Insurance-Into-the-Digital-Loan-Experience.html)
- The Applied Dev Center offers sandbox registration before an approval gate. — [APIs.io (secondary)](https://apis.io/providers/applied-systems/)
- The HawkSoft Partner API is open to tech vendors (not competing AMS vendors), with a security assessment and a live-agency pilot. — [HawkSoft](https://partner.hawksoft.app/getting-started/become-a-partner.html)
- Vertafore requires a Developer Portal contract, and the agency must hold the API scopes. — [API Evangelist (secondary)](https://github.com/api-evangelist/vertafore)
- Bold Penguin's new DeX ai APIs and MCP server are aimed at carriers, brokers and platform partners. — [PR Newswire](https://www.prnewswire.com/news-releases/bold-penguin-launches-dex-ai-the-intelligence-running-its-digital-exchange-302889677.html)

### Inferences
- **For a personal assistant app like JARVIS:** the lowest-friction route is to deep-link or embed a licensed marketplace (MediaAlpha, EverQuote, SmartFinancial, or a Matic partnership) rather than calling carrier rating APIs directly.
- **For real multi-carrier quote data to feed back into an app:** this requires either becoming or partnering with a licensed agency and then using EZLynx, PL Rating or TurboRater through that agency, or winning a platform-partner deal with Bold Penguin.
- **Commercial lines:** Bold Penguin's MCP server is the most "AI-agent-native" option found. It is aimed at brokers and platforms, so a license is still effectively required to place risk.

### Gaps
- None of the lead-gen or embed programs publish revenue share or minimum volume terms that I could find.
- I found no source stating explicit license requirements for publisher APIs; lead-gen partners generally need no license, but state rules on paid referral fees vary. I did not confirm this with a legal source.
- Whether The Zebra, Insurify or Policygenius currently run a public partner API is unverified.
