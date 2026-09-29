from ucs import ucs

graph = {
    "A": [("B", 4), ("C", 2)],
    "B": [("A", 4), ("D", 5), ("E", 10)],
    "C": [("A", 2), ("D", 3), ("E", 8)],
    "D": [("B", 5), ("C", 3), ("E", 2)],
    "E": [("B", 10), ("C", 8), ("D", 2)]
}

test_cases = [
    ("A", "E"),
    ("A", "B"),
    ("A", "D"),
    ("A", "A"),
    ("E", "A"),
    ("Z", "E")
]



for start, goal in test_cases:
    print("\n--------------------")
    print("Start:", start)
    print("Goal:", goal)

    if start not in graph:
        print("Invalid start node!")
        continue

    if goal not in graph:
        print("Invalid goal node!")
        continue

    status, cost, path = ucs(graph, start, goal)

    print("Status:", status)

    if status == "Goal Found":
        print("Path:", " -> ".join(path))
        print("Total Cost:", cost)
    else:
        print("No path exists.")

'''disconnected_graph = {
    "A": [("B", 4)],
    "B": [("A", 4)],
    "C": [("D", 3)],
    "D": [("C", 3)]
}

status, cost, path = ucs(disconnected_graph, "A", "D")

print("Status:", status)
print("Cost:", cost)
print("Path:", path)'''