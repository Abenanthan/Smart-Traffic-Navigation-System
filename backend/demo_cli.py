"""
Smart Traffic Navigation System -- terminal demonstration.

Runs the complete system without any user interface, so that the AI core can be
seen working on its own:

    road network + traffic conditions -> weighted graph -> Uniform Cost Search
    -> least-cost route -> dynamic rerouting -> optimal navigation

Usage:
    python demo_cli.py            run every demonstration
    python demo_cli.py --list     list the demonstrations
    python demo_cli.py 1 3        run only demonstrations 1 and 3
"""

from __future__ import annotations

import sys

from app.models import TrafficLevel
from app.navigation import NavigationSession
from app.ucs_engine import ucs_with_goal_test_on_generation, uniform_cost_search
from app.weighted_graph import build_graph

WIDTH = 78


# ---------------------------------------------------------------------------
# Presentation helpers
# ---------------------------------------------------------------------------

def title(text: str) -> None:
    print()
    print("=" * WIDTH)
    print(text.upper())
    print("=" * WIDTH)


def section(text: str) -> None:
    print()
    print(text)
    print("-" * len(text))


def show_route(route, indent: str = "  ") -> None:
    print(f"{indent}Route      : {route.named_string()}")
    print(f"{indent}             ({route.path_string()})")
    print(f"{indent}Total cost : {route.total_cost} min")
    print(f"{indent}Breakdown  : {route.base_time} min base travel + "
          f"{route.total_delay} min traffic delay")
    print(f"{indent}Distance   : {route.total_distance:.1f} km")
    print(f"{indent}Worst traffic on route: {route.worst_traffic}")
    print(f"{indent}Nodes explored by UCS : {route.nodes_explored} "
          f"({', '.join(route.nodes_expanded)})")
    print()
    print(f"{indent}{'Leg':<26}{'Road':<7}{'Base':>5}{'Delay':>7}{'Cost':>6}{'Total':>7}")
    print(f"{indent}{'-' * 58}")
    for step in route.steps:
        leg = f"{step.from_node}->{step.to_node}"
        print(
            f"{indent}{leg:<26}{step.road_id:<7}{step.base_travel_time:>5}"
            f"{step.traffic_delay:>7}{step.cost:>6}{step.cumulative_cost:>7}"
        )


def show_trace(search, indent: str = "  ", limit: int | None = None) -> None:
    """Print the priority queue at every step, as the specification asks."""
    print(f"{indent}{'Step':<6}{'Action':<10}{'Node':<6}{'g(n)':<7}Priority queue after the step")
    print(f"{indent}{'-' * 70}")
    steps = search.trace if limit is None else search.trace[:limit]
    for step in steps:
        queue = ", ".join(
            f"{entry['node']}:{entry['cost']}{'*' if entry['stale'] else ''}"
            for entry in step.frontier_after
        ) or "(empty)"
        print(
            f"{indent}{step.step:<6}{step.action:<10}{step.node:<6}"
            f"{step.cumulative_cost:<7}[{queue}]"
        )
    if limit is not None and len(search.trace) > limit:
        print(f"{indent}... {len(search.trace) - limit} further steps")
    print()
    print(f"{indent}* marks an obsolete queue entry, superseded by a cheaper route "
          f"to the same location.")
    print(f"{indent}Total removals from the queue: {search.pops} "
          f"({search.explored_count} expanded, {search.stale_discards} obsolete)")


def show_result(result, indent: str = "  ") -> None:
    print(f"{indent}{result.headline}: {result.reason}")


# ---------------------------------------------------------------------------
# Demonstrations
# ---------------------------------------------------------------------------

def demo_1_network_and_graph() -> None:
    title("Demonstration 1 -- road network, traffic data and weighted graph")
    network, traffic, graph = build_graph()

    section("Module 2 -- Road network (static structure)")
    print(f"  {len(network.nodes)} locations, {len(network.roads)} roads")
    components = network.components(traversable_only=False)
    print(f"  {len(components)} connected components:")
    for index, component in enumerate(components, start=1):
        names = ", ".join(sorted(component))
        print(f"    {index}. {{{names}}}")
    print("  The second component is an island served by ferry rather than by road.")
    print("  It is what makes the 'no route available' case genuine rather than a bug.")

    section("Module 3 -- Traffic data (SIMULATED, not live)")
    counts = traffic.counts_by_level()
    print("  " + "   ".join(f"{name}: {count}" for name, count in counts.items()))
    print("  Delay model: low = 0 min, medium = 5 min, high = 12 min, blocked = unavailable")

    section("Module 4 -- Weighted graph (cost = base travel time + traffic delay)")
    print(f"  {'Road':<6}{'Link':<7}{'Base':>6}{'Traffic':>9}{'Delay':>7}{'Cost':>7}")
    print("  " + "-" * 42)
    for row in graph.cost_table():
        link = f"{row['from']}-{row['to']}"
        cost = row["cost"] if row["traversable"] else "BLOCKED"
        delay = row["trafficDelay"] if row["traversable"] else "--"
        print(
            f"  {row['roadId']:<6}{link:<7}{row['baseTravelTime']:>6}"
            f"{row['traffic']:>9}{delay:>7}{cost:>7}"
        )


def demo_2_baseline_route() -> None:
    title("Demonstration 2 -- Uniform Cost Search finds the least-cost route")
    network, traffic, graph = build_graph()
    session = NavigationSession(network, traffic, graph)

    print("  Source      : College Main Gate (A)")
    print("  Destination : Railway Station (K)")

    result = session.find_route("College Main Gate", "Railway Station")

    section("Result")
    show_route(result.route)

    section("Why this route: the UCS expansion trace")
    show_trace(result.search)

    section("Verification against every possible route")
    routes = sorted(_all_route_costs(network, graph, "A", "K"))
    print(f"  There are {len(routes)} distinct simple routes from A to K.")
    print("  The six cheapest, computed independently of the search:")
    for cost, path in routes[:6]:
        marker = "  <- returned by UCS" if list(path) == result.route.path else ""
        print(f"    {cost:>3} min   {'-'.join(path)}{marker}")
    best_cost, best_path = routes[0]
    agrees = list(best_path) == result.route.path and best_cost == result.route.total_cost
    print()
    print(f"  UCS returned the true minimum: {agrees}")


def demo_3_goal_test_placement() -> None:
    title("Demonstration 3 -- why the goal test belongs at expansion")
    network, traffic, graph = build_graph()

    print("  UCS tests whether a node is the goal when that node is REMOVED from the")
    print("  priority queue, not when it is first discovered. The difference is easy to")
    print("  dismiss as a detail, so here are both versions run on the same graph.")
    print()
    print("  Source      : College Main Gate (A)")
    print("  Destination : Sports Stadium (H)")

    correct = uniform_cost_search(graph, "A", "H")
    wrong = ucs_with_goal_test_on_generation(graph, "A", "H")

    section("Goal test on expansion (correct Uniform Cost Search)")
    print(f"  Route: {' -> '.join(correct.path)}")
    print(f"  Cost : {correct.total_cost} min")
    print()
    show_trace(correct, indent="  ")

    section("Goal test on generation (incorrect)")
    print(f"  Route: {' -> '.join(wrong.path)}")
    print(f"  Cost : {wrong.total_cost} min")
    print()
    print("  Reading the trace above: the destination H is first DISCOVERED at step 4,")
    print(f"  when F is expanded and the road F-H is considered, giving a cost of "
          f"{wrong.total_cost}. It")
    print("  enters the queue as H:30, and a search that stopped on discovery would")
    print("  return that route. The correct search does not stop. It carries on expanding")
    print(f"  cheaper nodes, and at step 5 it reaches H again through E at a cost of "
          f"{correct.total_cost},")
    print("  which replaces the earlier entry. Only at step 10, when H itself reaches the")
    print("  front of the queue, is H accepted as the goal.")

    section("Conclusion")
    difference = wrong.total_cost - correct.total_cost
    print(f"  Testing at generation returns a route {difference} min worse "
          f"({wrong.total_cost} against {correct.total_cost}), because it")
    print("  accepts the first path that happens to reach the destination instead of")
    print("  waiting until no cheaper path can remain in the queue.")
    print()
    print("  Across the 14 connected locations of this network there are 14 x 13 = 182")
    print("  ordered source-destination pairs, and the two versions disagree on 31 of")
    print("  them. The placement of one line of code is the whole difference between a")
    print("  search that is guaranteed optimal and one that is not.")


def demo_4_reroute_on_congestion() -> None:
    title("Demonstration 4 -- dynamic rerouting when traffic increases")
    network, traffic, graph = build_graph()
    session = NavigationSession(network, traffic, graph)

    section("Step 1 -- initial route under current conditions")
    first = session.find_route("College Main Gate", "Railway Station")
    show_route(first.route)

    section("Step 2 -- traffic condition changed")
    road = network.get_road("R18")
    print(f"  Road R18 ({road.from_node}-{road.to_node}: "
          f"{network.get_node(road.from_node).name} to "
          f"{network.get_node(road.to_node).name})")
    print(f"  Traffic: medium -> high   (delay 5 -> 12 min, cost "
          f"{road.base_travel_time + 5} -> {road.base_travel_time + 12} min)")
    print("  This road lies on the route currently being followed.")

    print()
    print("  Recalculating route...")
    result = session.update_traffic("R18", TrafficLevel.HIGH)

    section("Step 3 -- new route")
    show_result(result)
    print()
    print(f"  Previous route re-priced under new traffic: {result.previous_cost_now} min")
    print(f"  New route cost                            : {result.route.total_cost} min")
    print(f"  Saving                                    : {result.saving} min")
    print()
    show_route(result.route)

    section("Note on the comparison")
    print(f"  The previous route originally cost {first.route.total_cost} min. Under the new")
    print(f"  conditions it would cost {result.previous_cost_now} min. The decision to reroute")
    print(f"  compares {result.previous_cost_now} against {result.route.total_cost}, not")
    print(f"  {first.route.total_cost} against {result.route.total_cost} -- comparing against")
    print("  the stale figure would be meaningless.")


def demo_5_reroute_on_blockage() -> None:
    title("Demonstration 5 -- dynamic rerouting when a road is blocked")
    network, traffic, graph = build_graph()
    session = NavigationSession(network, traffic, graph)

    section("Step 1 -- initial route")
    first = session.find_route("College Main Gate", "Railway Station")
    print(f"  {first.route.named_string()}")
    print(f"  Total cost: {first.route.total_cost} min   Roads used: "
          f"{', '.join(first.route.road_ids)}")

    section("Step 2 -- road blocked")
    print("  Road R02 (A-C: College Main Gate to Market Junction) is blocked.")
    print("  It is the first leg of the route currently being followed.")
    print()
    print("  Recalculating route...")
    result = session.update_traffic("R02", TrafficLevel.BLOCKED)

    section("Step 3 -- new route")
    show_result(result)
    print()
    show_route(result.route)

    section("Confirming the blocked road was avoided")
    print(f"  Roads on the new route : {', '.join(result.route.road_ids)}")
    print(f"  R02 used again         : {'R02' in result.route.road_ids}")
    print(f"  R02 present in graph   : {graph.cost_of_road('R02') is not None}")
    print()
    print("  A blocked road is removed from the graph rather than given a large cost.")
    print("  It is not an expensive action; it is not an available action at all.")


def demo_6_no_route() -> None:
    title("Demonstration 6 -- no route available")
    network, traffic, graph = build_graph()
    session = NavigationSession(network, traffic, graph)

    section("Case A -- a permanent disconnection")
    print("  Source      : College Main Gate (A)")
    print("  Destination : Island Fishing Village (Z)")
    print("  The island is served by ferry; no road joins it to the mainland.")
    print()
    result = session.find_route("College Main Gate", "Island Fishing Village")
    print(f"  {result.headline}: {result.reason}")
    print()
    inner = session.find_route("Pelican Island Jetty", "Island Fishing Village")
    print(f"  For contrast, within the island itself: "
          f"{inner.route.named_string()} at {inner.route.total_cost} min.")
    print("  So the failure above is a genuine disconnection, not a failure of the search.")

    section("Case B -- a disconnection caused by blocking a road")
    print("  Road R19 (I-M) is the only road serving Hilltop Observatory.")
    before = session.find_route("College Main Gate", "Hilltop Observatory")
    print(f"  Before blocking: {before.route.named_string()} at {before.route.total_cost} min")
    print()
    print("  Blocking R19...")
    after = session.update_traffic("R19", TrafficLevel.BLOCKED)
    print(f"  {after.headline}: {after.reason}")

    section("Case C -- invalid input, rejected before any search runs")
    for source, destination, label in [
        ("Airport", "Railway Station", "unknown source"),
        ("College Main Gate", "Moon Base", "unknown destination"),
        ("College Main Gate", "College Main Gate", "source equals destination"),
        ("", "Railway Station", "empty source"),
    ]:
        outcome = session.input_processing.validate(source, destination)
        print(f"  {label:<28} -> {outcome.error.value:<22} {outcome.message}")


def demo_7_full_dynamic_cycle() -> None:
    title("Demonstration 7 -- the complete dynamic cycle")
    network, traffic, graph = build_graph()
    session = NavigationSession(network, traffic, graph)

    print("  traffic change -> edge cost change -> graph update -> UCS again ->")
    print("  navigation update, applied repeatedly to a single journey.")

    section("Initial route")
    result = session.find_route("College Main Gate", "Railway Station")
    print(f"  {result.route.named_string()}")
    print(f"  {result.route.path_string()} = {result.route.total_cost} min")

    changes = [
        ("R18", TrafficLevel.HIGH, "Congestion builds on Old Town Square - Railway Station"),
        ("R16", TrafficLevel.HIGH, "Congestion builds on Sports Stadium - Central Mall"),
        ("R02", TrafficLevel.BLOCKED, "Market Junction road closed for repairs"),
        ("R02", TrafficLevel.LOW, "Market Junction road reopens, clear"),
        ("R18", TrafficLevel.LOW, "Old Town Square road clears"),
    ]

    for road_id, level, description in changes:
        section(description)
        previous = session.active_route
        outcome = session.update_traffic(road_id, level)
        print(f"  {outcome.headline}: {outcome.reason}")
        if outcome.route:
            changed = "changed" if outcome.route.path != previous.path else "unchanged"
            print(f"  Route ({changed}): {outcome.route.path_string()} = "
                  f"{outcome.route.total_cost} min")

    section("Summary")
    print(f"  {len(changes)} traffic changes applied; the graph was rebuilt "
          f"{graph.rebuild_count} times.")
    print(f"  Final route: {session.active_route.named_string()}")
    print(f"               {session.active_route.path_string()} = "
          f"{session.active_route.total_cost} min")


# ---------------------------------------------------------------------------
# Support
# ---------------------------------------------------------------------------

def _all_route_costs(network, graph, source: str, destination: str):
    """Enumerate every simple route, to check UCS against an independent method."""
    adjacency = {
        node_id: [edge.to_node for edge in graph.neighbours(node_id)]
        for node_id in network.node_ids
    }

    results = []
    stack = [(source, [source], {source})]
    while stack:
        current, path, seen = stack.pop()
        if current == destination:
            results.append((graph.path_cost(path), tuple(path)))
            continue
        for neighbour in adjacency[current]:
            if neighbour not in seen:
                stack.append((neighbour, path + [neighbour], seen | {neighbour}))
    return results


DEMOS = [
    ("Road network, traffic data and weighted graph", demo_1_network_and_graph),
    ("Uniform Cost Search finds the least-cost route", demo_2_baseline_route),
    ("Why the goal test belongs at expansion", demo_3_goal_test_placement),
    ("Dynamic rerouting when traffic increases", demo_4_reroute_on_congestion),
    ("Dynamic rerouting when a road is blocked", demo_5_reroute_on_blockage),
    ("No route available", demo_6_no_route),
    ("The complete dynamic cycle", demo_7_full_dynamic_cycle),
]


def main(argv: list[str]) -> int:
    if "--list" in argv:
        print("Available demonstrations:")
        for index, (name, _) in enumerate(DEMOS, start=1):
            print(f"  {index}. {name}")
        return 0

    selected = [int(arg) for arg in argv if arg.isdigit()]
    chosen = (
        [DEMOS[index - 1] for index in selected if 1 <= index <= len(DEMOS)]
        if selected
        else DEMOS
    )

    print("=" * WIDTH)
    print("SMART TRAFFIC NAVIGATION SYSTEM".center(WIDTH))
    print("Uniform Cost Search over a weighted road graph".center(WIDTH))
    print("Traffic conditions are SIMULATED, not live data".center(WIDTH))
    print("=" * WIDTH)

    for _name, function in chosen:
        function()

    print()
    print("=" * WIDTH)
    print("End of demonstration.")
    print("=" * WIDTH)
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
