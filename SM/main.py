from ucs import ucs
from road_rules import ROAD_RULES, build_graph

# Weighted graph
graph = build_graph(ROAD_RULES)


# Get input
start_node = input("Enter start node: ").upper()
goal_node = input("Enter goal node: ").upper()

if start_node not in graph:
    print("Invalid start node!")

elif goal_node not in graph:
    print("Invalid goal node!")

else:
    status, cost, path = ucs(graph,start_node,goal_node)


# Display result
print("\n----- UCS RESULT -----")

print("Status:", status)

if status == "Goal Found":
    print("Path:", " -> ".join(path))
    print("Total Cost:", cost)

else:
    print("No path exists.")