# Signalpost source policy

The competition rewards useful discovery only when the resulting evidence is lawful, reproducible and attributable to the exact company.

## Preferred sources

### Official Norwegian records

- Brønnøysundregistrene Enhetsregisteret bulk data and entity API for identity, legal form, address, industry and registered employee count
- Regnskapsregisteret API and annual-account copies for filed financial data and history
- Official roles endpoints for management and board roles
- Official subunit records for registered workplaces

Official data is the identity anchor. It does not, by itself, identify the public brand or website.

### Company-owned sources

- Verified official website
- Sitemap, news, investor, careers, location and contact pages
- Structured data embedded by the company
- Social or video profiles linked by the verified company site, subject to the destination platform's access terms

### External sources

- Official or licensed platform APIs
- Search APIs used to discover candidates
- Public pages whose terms and robots policy permit the submitted access pattern
- Licensed news, review, jobs, traffic or company-data feeds

## Publication rules

- Search results generate candidates; they are not claim evidence.
- A profile or domain must resolve to the exact legal entity before its facts are published.
- Group, parent, subsidiary, franchise and public-brand relationships must be labelled, not collapsed.
- Every claim records source URL or source identifier, retrieval time, effective/reporting date where relevant, content hash and extraction method.
- Missing, blocked and ambiguous are explicit states.
- Company-owned promotional copy may describe the business but cannot provide an independent sentiment claim.

## Restricted platforms and unofficial crawlers

Do not scrape a platform when its terms, robots policy or applicable law prohibit the submitted method. This includes treating unofficial LinkedIn, Meta, Glassdoor, Indeed or Google clients as automatically acceptable simply because code exists on GitHub.

An unofficial connector may be tested privately as a candidate-discovery experiment. For competition scoring, the entrant must declare the connector, demonstrate permitted access and independently verify any published claim from a durable permitted source.

## Evidence beats volume

The competition does not reward request count, pages downloaded or raw posts collected. It rewards exact-company, decision-useful coverage with valid evidence and reproducible refresh behavior.
