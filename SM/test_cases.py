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
    ("E", "A")
]

for start, goal in test_cases:
    status, cost, path = ucs(graph, start, goal)

    print("\n--------------------")
    print("Start:", start)
    print("Goal:", goal)
    print("Status:", status)

    if status == "Goal Found":
        print("Path:", " -> ".join(path))
        print("Total Cost:", cost)
    else:
        print("No path exists.")