# Indoor and outdoor climbing are separate Route and Ascent tables under a shared Session

Indoor and outdoor climbing are stored in separate tables: `IndoorRoute` (belongs to a Gym) and `OutdoorRoute` (belongs to a Crag), with `IndoorAscent` and `OutdoorAscent` pointing at their own kind of Route through ordinary foreign keys. Each pair inherits from an abstract base model that holds the shared fields and rules (grade, grade system, Route type, Discipline and Result validation, rests only when dogged), so no shared table exists in the database. The Session stays one universal table with no activity type, setting or place of its own: its activities are whatever is recorded against it. We chose the split because the two kinds differ in attributes (hold colour and date set against first ascensionist and aspect), in the Disciplines and Results allowed, and in how the athlete wants to analyse them (mostly separately, to see how indoor training informs outdoor performance). A single table would have filled up with columns that apply to only one kind.

## Considered options

- **One Route table with a nullable Crag and a free-text location:** rejected. It is the smallest change, but the attributes already diverge and will diverge further, and the "only for outdoor" fields would pile up.
- **A shared Route table with an indoor and an outdoor child (multi-table inheritance):** rejected. It keeps a single `Ascent.route` foreign key, but it adds a join to every query and a shared table that the athlete's mostly-separate statistics do not need.
- **Two Route tables with one Ascent table holding two nullable foreign keys and a check constraint:** rejected. Ascents differ in data collected (outdoor records who the athlete climbed with, and the Discipline and Result lists differ), and every place reading the Route would have to branch.
- **A generic foreign key from Ascent to either Route table:** rejected. It gives up foreign-key integrity and makes queries awkward.
- **Splitting Session into indoor and outdoor Sessions:** rejected. The Session is the universal unit across sports (running, hiking and so on will attach to it), and a day can mix indoor and outdoor Ascents.
- **One table per Route type (top-rope, sport, boulder, trad):** rejected. Types within a kind differ by one or two optional fields, not by behaviour, so a Route type column with type-specific fields validated by the model is enough.

## Consequences

- Cross-kind questions (for example the count of sends per grade across indoor and outdoor) need two queries or a union. This is acceptable because the athlete mostly wants the kinds analysed separately, with a comparison of aggregates.
- Every view, form and template that touches Routes or Ascents is either written once against the abstract base or exists once per kind. The two kinds share the logging flow and form logic through the base.
- An Ascent of the wrong kind of Route is unrepresentable, so no check constraint is needed for it.
- Outdoor work is additive: it adds `Crag`, `OutdoorRoute` and `OutdoorAscent` beside the indoor tables without changing them.
- Multi-pitch is deferred. When it arrives, each Route gains one Pitch in a migration, and Ascents move to Pitches.
- Grade is stored per system and validated against a code-defined ordered list, so the later statistics slice has an order for each system. Comparing across systems (V against Font, or Ewbank against French) still needs a mapping that is not part of this decision.
- Gym and Crag are real entities so that places do not drift through typos, and Routes can be matched within a place.
