from road_rules import ROAD_RULES, build_graph

graph = build_graph(ROAD_RULES)

print("Generated Graph:")

for location, roads in graph.items():
    print(location, ":", roads)