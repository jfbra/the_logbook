# The Logbook

A personal application that collects all of one athlete's performance and fitness data in one place, replacing scattered spreadsheets and apps. It starts with climbing and is meant to grow to cover running, hiking and mountaineering.

## Language

**Session**:
One bout of training or activity on a given day, whatever the sport. The universal unit of the logbook.
_Avoid_: Workout, activity, entry

**Activity type**:
The category of a Session, such as climbing, running, hiking or mountaineering. Drawn from a fixed list.
_Avoid_: Sport (collides with sport climbing), kind

**Route**:
A specific climb or boulder problem that can be attempted again over time, such as a named gym route or an outdoor line. Has a name, a grade and a type (boulder or roped). An Ascent is always an attempt-or-completion of one Route. Indoor Routes are identified by name within a location.
_Avoid_: Problem, climb, line

**Ascent**:
A single attempt-or-completion of one Route during a climbing Session, with a Discipline and a result such as onsight, flash, redpoint, dogged or fell. The result list depends on the Discipline.
_Avoid_: Climb, send, tick

**Discipline**:
The style an Ascent was done in. It depends on the Session's setting: indoors it is boulder, top-rope or sport; outdoors it follows theCrag's styles. Belongs to the Ascent, not the Route, because the same roped Route can be top-roped one day and led the next. A Session may contain Ascents in several Disciplines.
_Avoid_: Style, type
