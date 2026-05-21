# Country Legal Sources Import Agent Template

Use this template for adding a new country to the legal bot in the same style as Thailand.
Replace bracketed placeholders before handing this to another AI agent.

## Mission

Add a practical legal source package for **[COUNTRY_NAME]** using country code **[COUNTRY_CODE]**.

The package must cover:
- core codes and major laws;
- consumer protection and everyday disputes;
- visa/immigration questions for foreigners;
- real estate questions for foreigners, including Russian citizens where relevant;
- tourism, transport, police/loss, hotel/service complaints where relevant;
- statement templates and practical checklists;
- source registry;
- tests proving parser compatibility.

Do not claim that every law in the country is covered unless a complete official legislative catalogue has actually been imported. The expected target is a broad practical package for bot usage.

## Repository Context

Current project patterns:
- legal texts live in `data/codexes/[COUNTRY_CODE]/`;
- source registries use `[COUNTRY_CODE]_sources_registry_2026.txt`;
- practical statement/checklist files use `[COUNTRY_CODE]_statement_templates.txt`;
- country import scripts live in `scripts/import_[country_name]_sources.py`;
- tests live in `tests/test_import_[country_name]_sources.py`;
- `scripts/process_codexes.py` indexes `.txt`, `.md`, `.odt`, `.docx`, `.pdf` and parses text containing `Section N` or the Russian article marker used by existing RU files;
- each generated/imported text file should be normalized to parser-compatible `Section N.` blocks.

Before editing, inspect:
- `scripts/import_thailand_sources.py`
- `tests/test_import_thailand_sources.py`
- `bot/services/legal_scope_service.py`
- `scripts/process_codexes.py`

Do not read unrelated Markdown docs unless needed.

## Source Quality Rules

Use the best available sources in this order:
1. official government legal database / ministry / parliament / immigration / land registry / tax authority;
2. official gazette or consolidated legal database;
3. WIPO Lex, ILO NATLEX, UNODC, Refworld, World Bank, UNCTAD, FAOLEX, ICAO/aviation authority or similar institutional repositories;
4. reputable local legal databases with English translations;
5. law firm or private translations only when no better English source is available.

Every registry entry must include:
- title;
- local file name;
- category;
- number of parsed sections;
- resolved URL;
- note about translation status.

Always include a disclaimer in the registry:
`English translations are reference materials unless the source explicitly says otherwise. For legal force, verify against the official local-language text.`

## Required Legal Coverage

Research and import as many of these as are available for **[COUNTRY_NAME]**:

### Core Codes
- Constitution or constitutional law, if useful for legal Q&A;
- Civil Code / Civil and Commercial Code / Obligations Code;
- Civil Procedure Code;
- Penal / Criminal Code;
- Criminal Procedure Code;
- Administrative Procedure / Administrative Offences Code;
- Labour Code / Employment law;
- Tax / Revenue Code;
- Land Code / property law;
- Family law, if relevant and available.

### Consumer And Digital
- consumer protection law;
- product liability / product quality / goods quality law;
- unfair contract terms;
- advertising law;
- competition / antimonopoly law;
- e-commerce law or decrees;
- electronic transactions law;
- personal data / privacy law;
- cybersecurity / information law;
- food safety / sanitary law where relevant.

### Foreigners, Visa, Immigration
- entry, exit, transit and residence law;
- e-visa rules and official portal guidance;
- visa extension / temporary residence / permanent residence rules;
- work permit / foreign worker rules;
- overstay / administrative penalty rules if available;
- official embassy/consulate pages for Russian citizens if country-specific filing exists.

### Foreign Real Estate
- land ownership restrictions for foreigners;
- condominium/apartment ownership rules;
- real estate business law;
- lease/long-term lease rules;
- property registration / land office guidance;
- foreign funds / source-of-funds rules where available;
- investment/company ownership rules if foreigners commonly structure ownership through companies.

### Tourism, Transport, Police
- tourism law;
- hotel/accommodation law;
- travel agency/tour guide law;
- traffic/transport law;
- aviation/rail/bus/taxi rules where available;
- police report or lost-property channels;
- official complaint portals.

## Required Statement Templates

Create `[COUNTRY_CODE]_statement_templates.txt` with parser-compatible sections.

Minimum template sections:

1. Consumer complaint to competent consumer authority.
2. Tourism product/service complaint.
3. Police report for theft, fraud, assault, loss of documents.
4. Tour agency / guide / hotel complaint.
5. Transport complaint.
6. Visa application checklist for a Russian citizen or foreign applicant.
7. Visa extension / stay issue checklist.
8. Re-entry / exit-entry permit checklist if applicable.
9. Address registration / residence reporting checklist if applicable.
10. Residence certificate / proof of address request if applicable.
11. Foreign real-estate purchase due-diligence checklist.
12. Foreign lease / long-term rental / villa / house-on-land checklist.
13. Complaint or demand letter to real-estate agent, developer, landlord, or seller.
14. Work permit / foreign worker checklist if applicable.
15. Overstay or immigration-error explanation letter if applicable.

For Russian citizens, include country-specific fields:
- Russian passport details;
- place of application: Russia / local embassy / e-visa portal / in-country office;
- translation/legalization/apostille/consular legalization needs if relevant;
- payment route/source-of-funds risk where relevant;
- sanctions/bank-transfer constraints only when relevant and source-supported;
- warning to verify current embassy and immigration requirements before filing.

Each template should include:
- `Use for`;
- `Recipient`;
- `Source basis`;
- `Template fields`;
- `Draft wording` where useful;
- `Risk flags` where useful.

## Import Script Requirements

Create `scripts/import_[country_name]_sources.py`.

The script should:
- define a `Source` dataclass with `filename`, `title`, `url`, `category`, `note`, `alt_urls`;
- download HTML and PDF sources;
- use `httpx` with redirects and a browser-like user agent;
- support fallback URLs;
- strip HTML safely;
- extract PDF text with `pypdf`;
- normalize whitespace;
- split source text into sections using `Section`, `Article`, or local-language article markers if possible;
- if no section markers exist, chunk meaningful paragraphs into sequential `Section N` blocks;
- write files to `data/codexes/[COUNTRY_CODE]/`;
- write `[COUNTRY_CODE]_sources_registry_2026.txt`;
- write `[COUNTRY_CODE]_statement_templates.txt`;
- report imported and failed sources;
- finish with `failed=0` whenever possible, replacing dead sources with stable alternatives.

All generated legal files must be parser-compatible:

```text
Section 1. Original section/article: [original]. Source: [source title].
[body]
```

## Bot Scope Updates

Update `bot/services/legal_scope_service.py` only when needed:
- add country name and patterns if the country is not already supported;
- add normalization keywords when new source families need stable routing, for example `revenue -> tax`, `procedure -> procedural`, `immigration -> immigration` if the project has such key, or leave as `law` if no key exists.

If adding a new country, check `scripts/process_codexes.py` for `supported_countries` and country mapping.

## Tests

Create `tests/test_import_[country_name]_sources.py`.

At minimum test:
- section splitting accepts normal `Section N`, `Article N`, and suffixes like `bis`, `ter`, `12/1` if relevant;
- generated text is parsed by `parse_codex_file`;
- parsed country is `[COUNTRY_CODE]`;
- registry includes imported and failed sources;
- statement templates parse into the expected number of sections;
- key templates include visa and foreign real-estate sections;
- codex normalization works for new names, for example revenue/tax or procedure.

Run:

```powershell
$env:PYTEST_DISABLE_PLUGIN_AUTOLOAD='1'; pytest -q
```

Also run a parser count:

```powershell
python -c "from pathlib import Path; from scripts.process_codexes import parse_codex_file; base=Path('data/codexes'); total=0; rows=[]; country='[COUNTRY_CODE]'; 
for p in sorted((base/country).glob('*.txt')):
    if 'registry' in p.name: continue
    n=len(parse_codex_file(p, base)); total+=n; rows.append((p.name,n))
print('files', len(rows), 'total', total)
for name,n in rows: print(name, n)"
```

## Git Workflow

After implementation:
1. run tests;
2. run parser count;
3. inspect `git status --short --branch`;
4. stage only relevant files;
5. commit with message like:
   `Add [Country] legal sources and templates`
6. push if requested by the user.

Never push if tests were not run, unless the user explicitly accepts that risk.

## Final Report Format

Report briefly:
- number of imported sources;
- number of failed sources, must be zero or explained;
- number of `.txt` files;
- total parser sections;
- list of major covered domains;
- tests result;
- commit hash and push status if applicable.

Example:

```text
Added [COUNTRY_NAME] legal source package.

Coverage: core codes, consumer, visa/immigration, foreign real estate, labour, tax, tourism, transport, digital/privacy, complaint templates.

Import: [N] sources, failed=0.
Parser: [N] files, [N] sections.
Tests: pytest -q -> [N] passed.
Commit: [hash] [message].
Push: origin/main.
```

## Honesty Clause

Use this wording if needed:

`This is a broad practical legal package for bot use, not a complete import of every law in [COUNTRY_NAME]. Complete national coverage would require importing the full official legislative catalogue and verifying update status for every act.`
