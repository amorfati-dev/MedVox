"""Anästhesie je Zahn im Regel-Extraktor: BEMA 40 (I), 41a (L1), GOZ 0090, 0100.

Die Anzahl gehört zu dem Zahn, mit dem sie diktiert wird: „Infiltrationsanästhesie 18 2x“ und
„38 Ost2, Leitungsanästhesie 2x“ ergeben I*2 an 18 und L1*2 an 38 – nie eine Summe über alle Zähne
der Sitzung. Eine Fundstelle mit mehreren Zähnen („Infiltration 36, 37“) bleibt bei BEMA eine Anästhesie
für diese Zähne (40: im Bereich zweier Nachbarzähne einmal je Sitzung); GOZ 0090 zählt je Zahn. Ohne
Zahnnummer im Satz gilt die zuletzt diktierte (``TextContext.teeth_carried``), sonst je Sitzung im Builder.

Whisper schreibt die Kurzform „i“ als „IP“: „IP“ direkt hinter einer Zahnnummer oder mit Anzahl („IP, X2“)
ist I (BEMA 40), mit Prüfhinweis. „X2“ direkt hinter I/IP ist die Anzahl (I*2), nicht die Extraktion X2 –
ebenfalls mit Hinweis, solange am Zahn keine Zahnentfernung diktiert ist. „X2“ allein bleibt BEMA 44.

Ein zweites Mal je Zahn (BEMA 40 Nr. 3, 41 Nr. 4: bei lang dauernden Eingriffen) nur nach der Praxisregel
im Katalog (``repeat``, KZVB: erst ab Ost1 am selben Zahn), sonst auf 1 mit Hinweis. „lange Dauer“ zählt nie
hoch: bei zwei gezählten Anästhesien steht es in der Begründung, sonst gibt es einen Prüfhinweis. Dieselbe
Anästhesie an einem Zahn noch einmal genannt zählt einmal mit der höchsten diktierten Anzahl – außer die
Kurzform selbst wiederholt („38 l1, l1“, „18 i, i“): das ist die Schreibweise des Behandlers für zwei (höchstens 2,
dann Praxisregel ``repeat``), ob die Zahnnummer davor oder dahinter steht.
"""

from __future__ import annotations

import re
from collections.abc import Iterable

from medvox.extract_catalog import Catalog
from medvox.extract_draft import Draft, Tagged
from medvox.extract_match import Hit
from medvox.extract_rules import REMOVAL
from medvox.extract_text import TextContext

ANESTHESIA = frozenset({("BEMA", "40"), ("BEMA", "41a"), ("GOZ", "0090"), ("GOZ", "0100")})
_LONG = re.compile(
    r"(?<![a-z])(?:lang(?:e|er|en)?\s+(?:dauer|eingriff\w*|behandlung\w*|op)|lang\s*dauernd\w*)(?![a-z])"
)
_SHORT = re.compile(r"(?<![a-z0-9])(ip|i)(?![a-z0-9])")
_SHORT_TWICE = re.compile(r"[\s,]*(?:x\s?2|\*\s?2)(?![a-z0-9])")
_AFTER_TOOTH = re.compile(r"[\s,.]*")
SECOND_UNSAID = "{n}× diktiert – eine zweite Anästhesie nur bei lang dauerndem Eingriff, Begründung prüfen"
LONG_UNCOUNTED = "„{word}“ diktiert, aber nur eine Anästhesie gezählt – zweite Anästhesie prüfen"
REPEATED = "{n}× genannt, ohne Anzahl einmal gezählt – falls eine zweite Anästhesie, Anzahl erhöhen"
NEIGHBOURS = "BEMA 40 an {a} und {b}: Nachbarzähne – im Bereich zweier Nachbarzähne nur einmal je Sitzung, prüfen"
IP_AS_I = "„IP“ als I (Infiltrationsanästhesie) gelesen – prüfen"
X2_AS_COUNT = "„X2“ direkt hinter der Anästhesie als Anzahl gelesen – falls Extraktion X2 (BEMA 44) gemeint, ergänzen"


def aliases(catalog: Catalog, ctx: TextContext, hits: list[Hit]) -> list[Hit]:
    """„IP“/„i“ als I (BEMA 40) an einem Zahn oder mit „X2“; das „X2“ dahinter ist dann keine Extraktion."""
    infiltration = catalog.get("BEMA", "40")
    result = list(hits)
    for m in _SHORT.finditer(ctx.folded):
        twice = _SHORT_TWICE.match(ctx.folded, m.end())
        at_tooth = any(g.start <= m.start() < g.end or (g.end <= m.start() and _AFTER_TOOTH.fullmatch(
            ctx.folded, g.end, m.start())) for g in ctx.groups)
        if not (twice or (m.group(1) == "ip" and at_tooth)):
            continue
        if any(h.start < m.end() and m.start() < h.end for h in result):
            continue
        if twice:
            result = [h for h in result if not (h.start < twice.end() and twice.start() < h.end)]
        result.append(Hit(infiltration, m.start(), m.end(), m.group(1), True))
    return sorted(result, key=lambda h: h.start)


def anesthesia(builder, t: Tagged) -> bool:
    """Fundstelle mit Zahn: je Zahn (bzw. je Zahngruppe der Fundstelle) mit ihrer eigenen Anzahl; ohne Zahn False."""
    teeth = tuple(dict.fromkeys(tooth.fdi for tooth in t.teeth))
    if not teeth:
        return False
    entry = t.hit.entry
    count = _count(builder.ctx, t) or 1
    if len(teeth) == 1 or builder.catalog.unit(entry) == "tooth":
        for fdi in teeth:
            builder.add(entry, fdi, t, count)
        return True
    draft = builder.add(entry, None, t, count, slot=("anaesthesie", teeth))
    draft.context = teeth
    return True


def annotate(ctx: TextContext, drafts: Iterable[Draft]) -> None:
    """Praxisregel ``repeat``, Begründung und Prüfhinweise („lange Dauer“, IP/X2, Nachbarzähne)."""
    drafts = list(drafts)
    own = [d for d in drafts if d.entry.key in ANESTHESIA]
    starts = sorted(t.hit.start for d in own for t in d.hits)
    for d in own:
        said = [c for t in d.hits if (c := _count(ctx, t))]
        if not said and len({t.hit.start for t in d.hits if t.hit.code_word}) > 1:
            d.count = max(d.count, 2)
        capped = _repeat(d, drafts)
        long = next((m for t in d.hits if (m := _long(ctx, t, starts))), None)
        if d.count >= 2 and long:
            d.detail = f"{d.count}× diktiert, zweite wegen „{long}“"
        elif d.count >= 2:
            _flag(d, SECOND_UNSAID.format(n=d.count))
        elif long and not capped:
            _flag(d, LONG_UNCOUNTED.format(word=long))
        mentions = len({ctx.clause(t.hit.start) for t in d.hits})  # „Infiltrationsanästhesie mit Artikain“ ist eine
        if not said and mentions > 1 and d.count == 1 and not capped:
            _flag(d, REPEATED.format(n=mentions))
        if any(t.hit.keyword == "ip" for t in d.hits):
            _flag(d, IP_AS_I)
        if any(_SHORT_TWICE.match(ctx.folded, t.hit.end) for t in d.hits if t.hit.keyword in ("ip", "i")) and not any(
                o.entry.code in REMOVAL.get(o.entry.system, {}).values() and o.fdi == d.fdi for o in drafts):
            _flag(d, X2_AS_COUNT)
    infiltration = sorted(((d.fdi, d) for d in own if d.entry.key == ("BEMA", "40") and d.fdi and not d.planned),
                          key=lambda x: x[0])
    for (a, da), (b, db) in zip(infiltration, infiltration[1:]):
        if a // 10 == b // 10 and b - a == 1:
            for d in (da, db):
                _flag(d, NEIGHBOURS.format(a=a, b=b))


def _repeat(d: Draft, drafts: list[Draft]) -> bool:
    """Zweites Mal nur neben ``repeat.only_with`` am selben Zahn (ohne Zahn: in der Sitzung), sonst 1 mit Hinweis."""
    rule = d.entry.repeat
    if rule is None or d.count <= 1:
        return False
    teeth = {d.fdi} if d.fdi is not None else set(d.context)
    if any(o.entry.key in rule.only_with and not o.planned and (not teeth or o.fdi in teeth) for o in drafts):
        return False
    d.count = 1
    _flag(d, rule.note)
    return True


def _count(ctx: TextContext, t: Tagged) -> int | None:
    if t.hit.keyword in ("ip", "i") and _SHORT_TWICE.match(ctx.folded, t.hit.end):
        return 2
    return ctx.count_near(t.hit.start, t.hit.end)


def _long(ctx: TextContext, t: Tagged, starts: list[int]) -> str | None:
    """Wortlaut von „lange Dauer“ im Teilsatz der Fundstelle oder dahinter bis zum nächsten Zahn bzw. zur
    nächsten Anästhesie („Infiltrationsanästhesie. 2x. Beim zweiten Mal lange Dauer.“), sonst None."""
    s, e = ctx.clause(t.hit.start)
    m = _LONG.search(ctx.folded, s, e)
    if m is None:
        begin = t.hit.end
        own = next((g for g in ctx.groups if g.start >= begin and not ctx.folded[begin:g.start].strip(" ,.")), None)
        begin = own.end if own else begin
        stops = [g.start for g in ctx.groups if g.start >= begin] + [x for x in starts if x > t.hit.start]
        m = _LONG.search(ctx.folded, begin, min(stops, default=len(ctx.folded)))
    return ctx.original(m.start(), m.end()) if m else None


def _flag(d: Draft, text: str) -> None:
    if text not in d.decide:
        d.decide.append(text)
