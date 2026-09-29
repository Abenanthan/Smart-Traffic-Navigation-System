# Road rules: (Start, End, Travel Cost)

ROAD_RULES = [
    ("A", "B", 4),
    ("A", "C", 2),
    ("B", "D", 5),
    ("B", "E", 10),
    ("C", "D", 3),
    ("C", "E", 8),
    ("D", "E", 2)
]
def build_graph(road_rules):
    graph = {}

    for start, end, cost in road_rules:

        if start not in graph:
            graph[start] = []

        if end not in graph:
            graph[end] = []

        graph[start].append((end, cost))
        graph[end].append((start, cost))

    return graph