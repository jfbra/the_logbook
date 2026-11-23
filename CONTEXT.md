# The Logbook

A personal application that collects all of one athlete's performance and fitness data in one place, replacing scattered spreadsheets and apps. It starts with climbing and is meant to grow to cover running, hiking and mountaineering.

## Language

**Session**:
One bout of training or activity over one or more days, made of whatever is recorded against it (today, Ascents). It has no activity type, setting or place of its own: one Session can hold climbing and strength work, or a hike and a route, and a trip over several days is one Session. The universal unit of the logbook.
_Avoid_: Workout, entry

**Activity**:
A kind of thing done within a Session, such as climbing, hiking, mountaineering, running or walking. Not a record of its own: a Session's Activities are inferred from what is recorded against it. Later, Activities will be recorded as blocks, such as a tempo run.
_Avoid_: Workout

**Activity type**:
The category of an Activity, such as climbing, running, hiking, mountaineering or walking. Drawn from a fixed list.
_Avoid_: Sport (collides with sport climbing), kind

**Gym**:
An indoor climbing venue that holds Indoor Routes. Has a name, city, country and website.
_Avoid_: Location

**Crag**:
An outdoor climbing area that holds Outdoor Routes. Has a name, location and country. There is no area or sector level below it.
_Avoid_: Location

**Route**:
A specific climb or boulder problem that can be attempted again over time. Either an Indoor Route or an Outdoor Route. Has a name, a grade and a Route type. A Route is a single pitch; multi-pitch is not yet modelled. An Ascent is always an attempt-or-completion of one Route.
_Avoid_: Problem, climb, line

**Indoor Route**:
A Route that belongs to a Gym. Its Route type is top-rope, sport or boulder. Gyms reset routes and reuse names, so an Indoor Route's name is not unique within its Gym; hold colour and date set tell them apart.

**Outdoor Route**:
A Route that belongs to a Crag. Its Route type is sport, trad or boulder and describes how the first ascensionist climbed it. Its name is unique within its Crag.

**Route type**:
What kind of Route it is, which limits the Disciplines an Ascent of it can have. Indoors it is top-rope, sport or boulder; outdoors it is sport, trad or boulder. Locked once the Route has Ascents.
_Avoid_: Style (that is a free-text tag on a Route)

**Ascent**:
A single attempt-or-completion of one Route, with its own date within its Session, a Discipline and a Result. An Indoor Ascent is of an Indoor Route; an Outdoor Ascent is of an Outdoor Route and records who the athlete climbed with.
_Avoid_: Climb, send

**Discipline**:
How an Ascent was climbed. Indoors it is boulder, top-rope or sport; outdoors it is boulder, top-rope, sport, trad or second. The Route type limits it: a trad Route is never led as sport, but a sport Route can be led as trad. Belongs to the Ascent, not the Route, because the same Route can be top-roped one day and led the next. A Session may contain Ascents in several Disciplines.
_Avoid_: Style, type

**Result**:
The outcome of an Ascent, such as onsight, flash, redpoint, dogged, working, attempt or tick. The list of Results depends on the Discipline. A dogged Result can record how many rests were taken. A tick means "completed, cannot recall how".
_Avoid_: Send, outcome
