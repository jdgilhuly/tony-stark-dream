# Embedded Insurance / Insurance-as-a-Service API Platforms (catalog, as of Sept 2026)

Scope: platforms that let a non-insurer developer sell or embed insurance through an API, usually with the platform acting as licensed agent/MGA/carrier (licensed-entity-as-a-service). Core carrier systems are covered briefly at the end. Research was limited to about 20 searches, so some rows are thin. Anything without a source is in Gaps.

## Q1. Catalog: products, geographies, API capabilities, licensing model, docs, partners

### Takeaway
The clearest "developer can embed without a license" API platforms with public docs are **Boost Insurance** (US; renters, pet, small-business cyber/BOP; REST quote→bind→policy lifecycle; public docs), **Cover Genius XCover** (global; licensed in 60+ countries and all 50 US states; travel, shipping, product warranty and more), **Extend** (US product and shipping protection; public docs plus e-commerce plugins), **Ladder** (US term life; embeddable JS plus Quoter API; public GitHub docs) and **Kanguro** (US renters and pet; REST/OpenAPI plus widgets). Sure, Qover, bolttech, Igloo, INSHUR, Duuo and Kanopi are sales-led B2B2C platforms that share less publicly.

### Cited Findings

**US-focused platforms (MGA/agent-as-a-service)**

- **Boost Insurance (US)**
  - Describes itself as an insurance-as-a-service platform that bundles compliance, capital and technology into a turnkey, white-labeled program behind a RESTful API. — [API Evangelist profile](https://github.com/api-evangelist/boost-insurance)
  - Products listed in its API docs: Pet, Small Business Cyber, Renters and partner-specific programs. A quote is made by POSTing applicant and coverage data to `/quotes`. Binding and issuing is a POST of the Quote ID to `/policies`. Boost generates the policy and manages the lifecycle through cancellation. — [Boost docs (learn.boostinsurance.com/docs)](https://learn.boostinsurance.com/docs/renters)
  - Renters is an admitted product filed in 47 states plus DC; it is not available in RI, KY or AK. It is modular, with endorsements, limits and deductibles that partners choose. — [Boost Renters docs](https://learn.boostinsurance.com/docs/renters)
  - **Revenue model:** Boost invoices the partner monthly for earned premium (monthly policies) or installment premium (1/12 of written premium on annual policies), less the partner's commission. This means the partner earns a commission and Boost handles the carrier-side mechanics. — [Boost Renters docs](https://learn.boostinsurance.com/docs/renters)
  - **Status:** received a major investment from BHMS Investments in July 2024 (Crunchbase lists it as an acquisition). — [BusinessWire](https://www.businesswire.com/news/home/20240731052202/en/Boost-Insurance-Secures-Major-Investment-from-BHMS); [Crunchbase](https://www.crunchbase.com/acquisition/bhms-invests-acquires-boost-insurance--85bbcb9a)
  - Since then it has leaned toward MGAs and brokers. In May 2026 it launched **Boost Atlas**, an AI broker/MGA portal to rate, quote, bind and endorse BOP, Cyber and Management Liability. — [BusinessWire 2026](https://www.businesswire.com/news/home/20260526320786/en/Boost-Insurance-Launches-Boost-Atlas-The-AI-Driven-Partner-Portal-Built-for-Specialty-Commercial-Brokers-MGAs); [Boost MGA infrastructure](https://boostinsurance.com/platform/mga-infrastructure/)
- **Sure (sureapp.com, US)**
  - Embedded-insurance SaaS used by Fortune 500 brands and carriers. Programs for Tesla, Toyota, Mastercard and Intuit. More than $1B of premium a year flows through the platform. — [Digital Insurance](https://www.dig-in.com/news/meet-the-insurtech-sure); [PMF Show](https://www.pmf.show/blog/10-years-to-build-a-550m-insurtech-how-sures-wayne-slavin-pivoted-from-flight-insurance-to-embedded-insurance-for-tesla-and-toyota/)
  - Has raised more than $123M at a reported $550M valuation. — [PMF Show](https://www.pmf.show/blog/10-years-to-build-a-550m-insurtech-how-sures-wayne-slavin-pivoted-from-flight-insurance-to-embedded-insurance-for-tesla-and-toyota/)
  - Lines include embedded auto and renters. In Feb 2025 it launched **Sure Verify**, AI-based checking of renters-insurance compliance for property managers. — [Sure auto post](https://www.sureapp.com/post/embedded-auto-insurance-driving-the-future-of-coverage-for-drivers); [PR Newswire](https://www.prnewswire.com/news-releases/sure-launches-sure-verify-to-transform-insurance-coverage-verification-for-property-management-industry-302375365.html)
  - **Status:** cut about 70 staff in Feb 2025 while trying to raise money. — [The Insurer](https://www.theinsurer.com/ti/news/embedded-insurtech-sure-slashes-headcount-by-around-70-amid-latest-fundraising-2025-02-03/)
- **Extend (extend.com / helloextend, US)**
  - Product protection (repair or replace, including accidental damage) and shipping protection (lost, stolen or damaged packages). Offered through APIs or prebuilt apps for Shopify, Magento/Adobe Commerce, Salesforce Commerce Cloud and BigCommerce. — [Extend docs](https://docs.extend.com/docs/product-protection-6); [Adobe Marketplace](https://commercemarketplace.adobe.com/helloextend-integration.html); [Shopify App Store](https://apps.shopify.com/extend-protection)
  - Open-source plugins are on GitHub, for example WooCommerce. — [GitHub](https://github.com/helloextend/extend-for-woocommerce)
  - Uses an ML "decision engine" to optimize offers. — [Adobe Marketplace](https://commercemarketplace.adobe.com/helloextend-integration.html)
- **Clyde (US product protection)**
  - **Acquired by Cover Genius, not by Mulberry.** Cover Genius bought Clyde's assets on March 15, 2023. Clyde's merchants included Skullcandy, Movado, Dyson, SharkNinja and Tuft & Needle. — [GlobeNewswire](https://www.globenewswire.com/news-release/2023/03/15/2627874/0/en/Cover-Genius-Acquires-Clyde-Deepening-Footprint-in-121B-Global-Warranty-Industry.html); [Coverager](https://coverager.com/cover-genius-acquires-the-assets-of-clyde/)
- **Mulberry (getmulberry.com, US)**
  - Product protection and warranty for DTC brands. Last priced round was a $22M Series B in Oct 2021; about $38.9M raised in total. — [Mulberry](https://www.getmulberry.com/news/series-b); [Tracxn](https://tracxn.com/d/companies/mulberry/__sY_BQLjBv2-v2g7WQGR0s7t2uNHN226-gQ1hjEB4-Kk)
  - Still active in 2025, with new partners Glowforge (Apr 2025) and Appliance.io (Jun 2025). — [GlobeNewswire](https://www.globenewswire.com/news-release/2025/04/29/3070379/0/en/Glowforge-Selects-Mulberry-to-Redefine-Product-Protection-for-Creators.html)
  - Search results about "Mulberry raises $27M" refer to the UK fashion brand Mulberry and are unrelated. — [Fashion Dive](https://www.fashiondive.com/news/mulberry-fundraising-round-frasers-challice/752707/)
- **Kanguro (kanguroseguro.com, US, Hispanic-market focus)**
  - Offers no-code embeddable widgets plus a REST API (OpenAPI 3.0). — [Kanguro LLM info](https://www.kanguroseguro.com/llm); [Kanguro embed portal](https://embedd.kanguroseguro.com/)
  - Coverage: renters in FL, TX and GA; pet in 28+ states. Support in English and Spanish. — [Kanguro LLM info](https://www.kanguroseguro.com/llm)
  - Launched Florida renters in March 2025. — [The Insurer](https://www.theinsurer.com/ti/news/insurtech-kanguro-launches-renters-insurance-in-florida-2025-03-04/)
- **Ladder (ladderlife.com, US term life)**
  - Term life up to $3M with no medical exam, 10–30 year terms. — [API Evangelist](https://github.com/api-evangelist/ladder)
  - Embedded APIs: the Embeddable API (a white-labeled application flow in about 10 lines of JS), Quoter API, Connector (prefill), Calculator (coverage-needs tool) and Account Manager. — [API Evangelist](https://github.com/api-evangelist/ladder)
  - Public docs are at [ladderlife.github.io/api](https://ladderlife.github.io/api/), with a product page at [ladderlife.com/api](https://www.ladderlife.com/api).
  - Partners include SoFi (since 2018) and SafeButler. Partnerships are now Ladder's largest distribution channel. — [Insurance Business](https://www.insurancebusinessmag.com/us/news/technology/case-study-ladder-loves-embedding-for-maximum-distribution-414153.aspx); [PR Newswire](https://www.prnewswire.com/news-releases/safebutler-and-ladder-partner-to-offer-fast-and-simple-life-insurance-301177277.html)
- **Bestow (US life)**
  - Now a SaaS provider of life and annuity technology (origination, underwriting, administration) for carriers. It is no longer mainly a partner-embed API for developers. — [CB Insights](https://www.cbinsights.com/compare/bestow-vs-ethos-technologies); [Coverager](https://coverager.com/bestow-is-preparing-the-groundwork-for-working-with-agents/)
  - An aggregator blog claims a "$400M valuation in 2025". This is a low-quality source and is unverified. — [ellty](https://www.ellty.com/blog/life-insurance-investors)
- **Ethos (US life)**
  - Direct-to-consumer and agent-led term life, issued through carriers such as Banner Life, Protective and Ameritas. — [ellty (low quality)](https://www.ellty.com/blog/life-insurance-investors)
- **Assurance IQ (US)**
  - **Shut down.** Prudential decided to wind it down in 2024 (announced May 1, 2024) after $2.14B in goodwill write-downs. It stopped selling new policies, with Seattle layoffs from July 2024. — [Insurance Journal](https://www.insurancejournal.com/news/national/2024/05/01/772359.htm); [GeekWire](https://www.geekwire.com/2024/prudential-to-shut-down-assurance-the-insurance-tech-startup-it-acquired-for-2-35b-in-2019/)
  - Prudential later settled with the FTC for $100M over the unit's healthcare marketing (Aug 2025). — [Claims Journal](https://www.claimsjournal.com/news/national/2025/08/08/332269.htm)
- **Lemonade API (US)**
  - Launched in 2017. It supported quote, policy creation and payment for renters, homeowners and condo insurance in NY, CA, TX, IL, NJ and RI. — [Lemonade blog](https://www.lemonade.com/blog/introducing-lemonade-insurance-api/); [PR Newswire](https://www.prnewswire.com/news-releases/lemonade-launches-insurance-api-650210233.html)
  - Two integration modes: a one-line embed of the "Maya" bot, or a full API that controls every step. — [Lemonade blog](https://www.lemonade.com/blog/introducing-lemonade-insurance-api/)
  - Lemonade said adopters did not need an insurance license. — [Insurance Journal 2017](https://www.insurancejournal.com/news/national/2017/12/11/473629.htm)
  - **Stale:** these sources are from 2017, and I found nothing current on the API's availability.
- **INSHUR (US/UK/NL, commercial auto for gig drivers)**
  - Embedded, API-integrated programs for Uber, Amazon Flex, Bolt and Turo, from onboarding through claims. — [INSHUR](https://inshur.com/about-us)
  - Raised $35M in July 2025. — [AlleyWatch](https://alleywatch.com/2025/07/inshur-on-demand-economy-insurance-embedded-commercial-auto-rideshare-delivery-autonomous-dan-bratshpis/)
  - Launched with Uber in Arizona for livery drivers. — [INSHUR news](https://inshur.com/news/inshur-uber-arizona-livery-insurance-launch)
  - Sold its 1 millionth UK policy. Has an on-demand product for Uber Eats riders in the Netherlands. — [INSHUR](https://inshur.com/about-us)
- **Embroker (US business insurance)**
  - Its API work is partner distribution: an API-linked Cowbell cyber plus Embroker LPL bundle (with Dashlane), and an API product for Excess Tech E&O/Cyber through Millennial Shift (July 2024). — [BusinessWire 2023](https://www.businesswire.com/news/home/20230725526581/en/Embroker-Partners-with-Dashlane-and-Cowbell-to-Continue-Building-Single-Destination-Risk-Mitigation-Solution); [Insurance Edge](https://insurance-edge.net/2024/07/11/embroker-teams-up-with-mshift-on-policy-distribution/)
- **Openly (US homeowners carrier)**
  - Sells only through independent agents; no direct sales. It is not a developer-embed platform. — [Openly agents](https://openly.com/agents)
- **Covie (US policy-data API)**
  - A consent-based API for retrieving policy data (coverages, limits, status) from carriers, used for verification. — [Catalyit](https://catalyit.com/solution-provider-directory/covie-access)
  - **Acquired by TheGuarantors in March 2025.** — [Tracxn/Crunchbase via search](https://tracxn.com/d/companies/covie/__0cJHNS7gN9_ej2ePGOZh4jr0R9tvEMhZoIaSVZLYZKw)
  - Pricing is usage-based. — [Covie pricing](https://www.covie.com/pricing)
  - Canopy Connect is an alternative in this category. — [Canopy Connect](https://www.usecanopy.com/solutions/embedded-insurance)

**Global platforms**

- **Cover Genius / XCover (global, HQ Sydney/NY)**
  - Licensed or authorized in 60+ countries and all 50 US states; works in any language and currency. — [XCover](https://covergenius.com/platform/xcover/)
  - Scale: 200+ partners and 50+ carriers. Revenue grew 50% year on year in 2025, with more than $3B in cumulative gross written sales. — [FinTech Global, Jul 2026](https://fintech.global/2026/07/15/cover-genius-lands-100m-to-power-ai-embedded-protection/)
  - Raised $100M in July 2026 at a $1.9B valuation. — [FinTech Global, Jul 2026](https://fintech.global/2026/07/15/cover-genius-lands-100m-to-power-ai-embedded-protection/)
  - Partners: Booking Holdings, Intuit, Hopper, Ryanair, Turkish Airlines, Klarna, Revolut, Priceline, Agoda, Uber, Amazon, eBay, Wayfair, Flipkart and Shopee. Added a Tongcheng Travel partnership in April 2026. — [FinTech Global](https://fintech.global/2026/07/15/cover-genius-lands-100m-to-power-ai-embedded-protection/); [FinTech Global Apr 2026](https://fintech.global/2026/04/17/cover-genius-partners-tongcheng-travel-to-expand-embedded-travel-insurance/)
  - Lines: travel, product warranty (including the former Clyde business), shipping and others.
- **Qover (EU, Brussels)**
  - Operates in 32+ countries with 15M people protected. Fintech partners include Monzo, Revolut and ING. — [TAMradar](https://www.tamradar.com/funding-rounds/qover-growth-financing-12m)
  - Raised $12M of growth funding in March 2026, bringing its total above $100M. — [TAMradar](https://www.tamradar.com/funding-rounds/qover-growth-financing-12m)
  - Platform overview: [qover.com/platform-overview](https://www.qover.com/platform-overview)
- **bolttech (Asia/global, Singapore)**
  - Closed a $147M Series C in June 2025 at a $2.1B valuation, with a Sumitomo partnership for Asia. Reports about $65B in annualized quoted premiums. — [TechCrunch](https://techcrunch.com/2025/06/04/singapore-based-insurtech-bolttech-closes-147m-series-c-at-a-2-1b-valuation/)
  - Platform site: [bolttech.io](https://bolttech.io/)
- **wefox (EU)**
  - Once valued at $4.5B. Restructured, with Joachim Mueller (ex-Allianz) as CEO from Sept 2024. — [Coverager](https://coverager.com/wefox-appoints-new-ceo/); [CB Insights](https://www.cbinsights.com/company/financefox)
  - Its board rejected a sale to Ardonagh. In May 2025 it sold its Italian units (wefox MGA S.r.l. and Services Italy, mainly affinity motor) to J.C. Flowers and said its restructuring was complete. — [Insurance Journal](https://www.insurancejournal.com/news/international/2025/05/14/823700.htm); [Reinsurance News](https://www.reinsurancene.ws/wefox-sells-italian-entities-to-j-c-flowers-co-completes-restructure/)
- **Igloo (Southeast Asia, Singapore)**
  - Full-stack insurtech; 75+ brands and insurers use its technology. — [Igloo press](https://iglooinsure.com/press/igloo-launches-igloo-tech-solutions/)
  - 2025 partners: Shopee, Salmon and Skyro (Philippines); Kredivo, DANA and Akulaku (Indonesia); TrueMoney and Lazada (Thailand). — [ANTARA](https://en.antaranews.com/news/346057/igloo-kicks-off-2025-with-multi-market-partnership-wins-and-chief-distribution-officer-appointment)
  - In June 2025 it launched Igloo Tech Solutions, including an AI claims agent, fraud detection and the no-code "Turbo" platform. — [FinTech Global](https://fintech.global/2025/06/03/igloo-unveils-igloo-tech-solutions-to-transform-insurance-across-southeast-asia/)
  - Tokio Marine holds a minority stake. — [Insurance Business](https://www.insurancebusinessmag.com/asia/news/technology/tokio-marine-buys-minority-stake-in-singapore-insurtech-igloo-563467.aspx)
  - Expanded its Philippines strategy in April 2026. — [TNGlobal](https://technode.global/2026/04/15/insurtech-igloo-expands-philippines-strategy-as-insurance-market-hits-8-4b/)
- **Duuo by Co-operators (Canada)**
  - Launched an embedded insurance platform and API in 2023. — [Open Banking Expo](https://www.openbankingexpo.com/news/canadas-duuo-by-co-operators-launches-embedded-insurance-api/); [Co-operators](https://www.cooperators.ca/en/about-us/newsroom/2023-08-04)
  - Published an Embedded Insurance Report 2025 based on a survey of 1,200+ Canadians. — [Duuo](https://duuo.ca/embedded-insurance-report/)
- **Kanopi (Australia)**
  - Embedded platform with modular APIs connecting insurers to digital platforms and marketplaces, including carrier routing. — [Kanopi platform](https://kanopicover.com/platform/)
- **Getsafe (Germany)**
  - About 500,000 contracts (liability, contents, pet health, product) moved to **andsafe**, the Provinzial Group's digital insurer. BaFin approved on Oct 27, 2025 and the deal closed around Nov 10, 2025. — [Hengeler Mueller](https://hengeler-news.com/en/articles/hengeler-mueller-advises-andsafe-the-digital-insurer-of-provinzial-group-on-the-acquisition-of-the-insurance-portfolio-of-getsafe-insurance); [Clyde & Co](https://www.clydeco.com/en/news/2025/11/clyde-co-advises-getsafe-on-the-transfer-of-its-in)
  - Getsafe continues as an underwriting agent.
- **Setoo (France)**
  - Merged with Pattern, and the combined company operates under the Pattern brand for e-commerce insurance. — [CB Insights](https://www.cbinsights.com/company/setoo)
- **hepster (Germany)**
  - Embedded insurance for mobility and e-commerce. Raised $11M in 2023. — [Insurtech Insights](https://www.insurtechinsights.com/german-insurtech-hepster-secures-us11-million-in-funding-round/)

**Core carrier systems (brief)**

- These are platforms carriers use to build and expose products, not license-as-a-service for developers. Main vendors: Socotra, Duck Creek, Guidewire, Majesco, EIS and Sapiens. — [Socotra](https://www.socotra.com/); [Duck Creek](https://www.duckcreek.com/); [SelectHub](https://www.selecthub.com/insurance-software/duck-creek-vs-socotra-insurance/)
- Duck Creek bought Send Technology Solutions in July 2026. — [Insurance Edge](https://insurance-edge.net/2026/07/08/deals-duck-creek-buys-send-technology-solutions/)
- Openkoda publishes its own "best insurtech platforms" list (vendor content). — [Openkoda](https://openkoda.com/best-insurtech-platforms/)

### Inferences
- For a developer who wants to sell insurance without a license, the model with the least friction is a platform that is itself the licensed agent/MGA and pays the developer a commission or referral fee. Boost's invoice-minus-commission setup is the clearest documented example. In the US, being paid per bound policy usually requires the developer to hold at least a limited or producer license, unless the payment is a flat marketing or referral fee. This is general regulatory knowledge and should be confirmed per state.
- Public docs plus self-serve integration tends to go with narrower lines: Boost (renters, pet, cyber), Extend (product protection), Ladder (term life) and Kanguro. Global platforms such as XCover, Qover, bolttech and Sure are sales-led, and sandbox access comes after a partnership agreement.
- For a personal assistant like JARVIS, the realistic integrations are either read-only policy data (a Covie/Canopy-style API) or affiliate/referral embeds, not binding coverage directly.

### Gaps
- **Sandbox availability** was not verified for any vendor. My understanding (unverified) is that Boost, Sure, XCover and Extend give sandbox keys after onboarding.
- **Docs URLs for Sure, XCover, Qover and bolttech** were not confirmed. From memory and unverified: docs.sureapp.com and xcover.com/en/developers.
- **Revenue-share percentages** were not public for any vendor.
- **Webhooks, claims and SDK details** were not confirmed except for Boost (quote/bind/policy), Ladder (JS embed), Extend (plugins) and Kanguro (widgets and OpenAPI).
- **No data found** on:
  - Marshmallow (UK car insurer; I found no embedded API program)
  - ottonova (German private health insurer; not an embedded API platform as far as I know, unverified)
  - Gainsco (nonstandard auto carrier; no embedded API found)
- **Current status unknown** for:
  - hepster (possible 2024–25 distress, unverified)
  - the Lemonade API (likely deprioritized)
  - Ethos (possible IPO activity, unverified)
- **Extend's 2025–26 corporate status** (funding, layoffs, M&A) was not found.

## Q2. Status changes 2023–2026 (shutdowns and acquisitions)

### Takeaway
There has been significant consolidation. Clyde went to Cover Genius (2023), Assurance IQ was shut down (2024), Boost took BHMS investment (2024), Covie went to TheGuarantors (2025), Getsafe's book moved to andsafe (2025), wefox sold its Italian units (2025), Setoo merged into Pattern, and Sure cut staff (2025). The winners raising large rounds are Cover Genius ($100M at $1.9B, Jul 2026), bolttech ($147M at $2.1B, Jun 2025), Qover ($12M, Mar 2026) and INSHUR ($35M, Jul 2025).

### Cited Findings
Each event is sourced in Q1:

| Company | Event | Date |
|---|---|---|
| Clyde | Assets acquired by Cover Genius | Mar 2023 |
| Assurance IQ | Wound down by Prudential | May 2024 |
| Boost | Major investment from BHMS | Jul 2024 |
| Sure | About 70 staff cut | Feb 2025 |
| Covie | Acquired by TheGuarantors | Mar 2025 |
| wefox | Italian units sold to J.C. Flowers | May 2025 |
| Getsafe | Portfolio moved to andsafe | Oct/Nov 2025 |
| Setoo | Merged into Pattern | date not captured |
| Cover Genius | $100M raise | Jul 2026 |
| bolttech | $147M Series C | Jun 2025 |

### Inferences
- Pure-play embedded platforms are consolidating into carrier-backed owners (Provinzial, Tokio Marine's stake in Igloo, Co-operators' Duuo, Sumitomo with bolttech) or PE owners (BHMS, J.C. Flowers). Developers should weigh counterparty stability when choosing a partner.

### Gaps
- The date of the Setoo–Pattern merger and whether Pattern is still operating were not confirmed.
- No 2026 status was found for Mulberry, Extend, hepster, Kanopi or Duuo beyond what is listed above.
