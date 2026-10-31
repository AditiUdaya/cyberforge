"""M1 Map window: reports 6, 8, 30 and 45 days old; areas just inside and outside the radius;
other cities.
Expected: only in-window, in-radius areas, at Appendix B points.

The PRD areas are fixed, so instead of areas exactly 1.9 and 2.1 km away, the scenario picks a
neighbour at distance d and asks with radius d + 0.1 (included) and d - 0.1 (excluded).

Owner: B. Filled in by: B4.
"""

from __future__ import annotations

from contract import Client
from families._shared import area_traffic
from generator import Gen, Outcome, Scenario, area_map, areas, distance_km

EDGE_KM = 0.1


def generate(g: Gen) -> Scenario:
    bengaluru = sorted(p for p, a in areas().items() if a["city"] == "Bengaluru")
    centre = g.rng.choice(bengaluru)
    neighbour = min((p for p in bengaluru if p != centre), key=lambda p: distance_km(centre, p))
    far = g.area(city=g.rng.choice(["Mumbai", "Delhi", "Chennai", "Pune"]))
    d = distance_km(centre, neighbour)
    s = g.scenario(f"{areas()[centre]['locality']} with neighbour {d:.2f} km away")

    scam_type = "job-offer"
    hours = [24 * age + g.rng.uniform(1, 11) for age in (6, 8, 30, 45)]
    area_traffic(g, s, centre, hours, scam_type)
    area_traffic(g, s, neighbour, [24 * 2 + g.rng.uniform(1, 11)], scam_type)
    area_traffic(g, s, far, [24 * 2 + g.rng.uniform(1, 11)], scam_type)

    @s.check("3", "7-day window shows only the 6-day-old report")
    def _check_1(c: Client, o: Outcome) -> None:
        found = {x["pincode"]: x for x in area_map(c, centre, days=7, radius_km=0)}
        if set(found) != {centre} or found[centre]["count"] != 1:
            raise AssertionError(f"got {[(p, x['count']) for p, x in found.items()]}")

    @s.check("3", "31-day window shows 6, 8 and 30 days, not 45")
    def _check_2(c: Client, o: Outcome) -> None:
        found = {x["pincode"]: x for x in area_map(c, centre, days=31, radius_km=0)}
        if found.get(centre, {}).get("count") != 3:
            raise AssertionError(f"got {[(p, x['count']) for p, x in found.items()]}")

    @s.check("3", "neighbour inside the radius is shown, outside is not")
    def _check_3(c: Client, o: Outcome) -> None:
        inside = {x["pincode"] for x in area_map(c, centre, days=7, radius_km=d + EDGE_KM)}
        outside = {x["pincode"] for x in area_map(c, centre, days=7, radius_km=max(d - EDGE_KM, 0))}
        if inside != {centre, neighbour} or outside != {centre}:
            raise AssertionError(f"radius {d:.2f}+-0.1 gave {sorted(inside)} / {sorted(outside)}")

    @s.check("3", "defaults are 7 days and 2 km")
    def _check_4(c: Client, o: Outcome) -> None:
        want = {centre, neighbour} if d <= 2 else {centre}
        got = {x["pincode"] for x in area_map(c, centre)}
        if got != want:
            raise AssertionError(f"default map gave {sorted(got)}, want {sorted(want)}")

    @s.check("4", "clusters sit at Appendix B points, never elsewhere")
    def _check_5(c: Client, o: Outcome) -> None:
        for x in area_map(c, centre, days=60, radius_km=5000):
            point = areas().get(str(x["pincode"]))
            if point is None or (x["lat"], x["lng"]) != (point["lat"], point["lng"]):
                raise AssertionError(f"cluster {x['pincode']} at {x['lat']},{x['lng']}")

    return s
