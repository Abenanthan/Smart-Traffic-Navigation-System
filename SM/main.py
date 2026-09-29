from ucs import ucs


# Weighted graph
graph = {
    "A": [
        ("B", 4),
        ("C", 2)
    ],

    "B": [
        ("A", 4),
        ("D", 5),
        ("E", 10)
    ],

    "C": [
        ("A", 2),
        ("D", 3),
        ("E", 8)
    ],

    "D": [
        ("B", 5),
        ("C", 3),
        ("E", 2)
    ],

    "E": [
        ("B", 10),
        ("C", 8),
        ("D", 2)
    ]
}


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