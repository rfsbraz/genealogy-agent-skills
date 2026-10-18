# Country starter database

Use `assets/countries/index.json` to find a country profile. Each profile is independent JSON; load only the relevant profiles. The database is original suite content built from official entry points, not copied from another skill pack. It contains 14 countries and 31 entry points. It is a seed set, not a country whitelist.

## Read a profile

1. Establish an origin or event location from evidence. Keep alternative origins separate and route an unknown origin through records most likely to name it.
2. Resolve locality, period, historical jurisdiction and record creator. A present-day country label is only a starting index; migration, boundary changes and former administrations may require several profiles.
3. Run `python scripts/country_tools.py show Portugal --place "Santa Maria" --period 1873 --family religious --json`, or read the JSON directly. An ambiguous locality such as Santa Maria still needs disambiguation; the helper does not select a parish or archive for you.
   - `--place`, `--region` and `--period` fill the query templates. They never filter the starter sources. The text output prints the scope and the filled search queries, plus one line saying the sources are not filtered.
   - `--family` is a record family, not a surname: one of `civil`, `household`, `institutional`, `legal`, `migration`, `military`, `press` or `religious`. Sources that list it come first. Any other value fails with the list of valid families. When no source in the profile lists the family, or every source does, the output says the filter had no effect. `genealogy.py sources` takes the same options.
4. Treat each result as a directory, guide, catalogue, custodian, library, civil authority or request service according to its `kind`. Do not treat all websites as archives, and do not confuse a service endpoint with a collection.
5. Follow `first_steps`, native `search_terms` and `query_templates`. Query templates are proposed searches; this offline helper never executes them.
6. Recheck official pages before relying on access arrangements. `verification.method` distinguishes a primary-site indexed result from a page inspected directly. No seed has person-specific holding coverage. A reachable homepage does not establish record survival or image access.
7. Verify actual collection identifiers, coverage, gaps and rights with the custodian. Save these in the private case’s Repository/Holding/portfolio entries; do not place the person’s identity or research facts in the shared country database.
8. When an endpoint fails, use the official directory, the recorded fallback or a verified contact route. Record inaccessible, not no-match. Draft correspondence through genealogy-archive-correspondence; source discovery never grants send or payment authority.

## Extend and maintain

The older `country-profile-template.json` is a working research-profile template; its person-specific portfolio belongs in the private case, not this shared database. For an unlisted country, follow country-discovery.md and create a curated seed profile using `assets/country.schema.json`; add its code/name/aliases/path to the index. Use historical jurisdiction notes and locality language, not copied assumptions about registration dates. Prefer sourced questions over unsupported blanket rules.

Every source entry needs a stable ID, official URL, role, purpose, relevant record families (from the closed list above; `validate` rejects others), observed date, verification method and evidence URL. Leave person-specific coverage as `not_assessed_for_person`. Preserve notices and their dates. Do not include unverified email addresses, credentials, fixed fee tables or guessed APIs.

Revisit a used profile at use time, after failed access or a jurisdiction change. The helper flags a review after 90 days as a maintenance heuristic, not a historical validity rule. It also flags any service notice immediately. Refresh only what was actually checked; never update a date on the basis of a successful DNS/HTTP response alone. A host may schedule these reviews; no timer is installed here.

Validate with `python scripts/country_tools.py validate`. This checks identifiers, aliases, paths, roles, URLs and basic metadata, not service availability. JSON Schema is supplied for host validation. The curated index can be replaced with a separate database using `--database PATH`; no network calls occur.

## Boundaries

Country guides are discovery knowledge, not evidence about an ancestor. They do not complete GPS research coverage. Verify each record's relevance, provenance and citation before extraction. No claim is made that these countries are fully mapped or that there are working adapters to their services.
