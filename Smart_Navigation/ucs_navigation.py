import heapq


def ucs(graph, start_node, goal_node):
    """
    Uniform Cost Search (UCS)

    graph: dict of {node: [(neighbor, cost), ...]}
    start_node: starting node
    goal_node: goal node

    Returns (result_string, cost, path)
    """
    # 1. create an empty priority queue Q (lowest cost comes out first)
    Q = []

    # 2. create an empty set VISITED
    VISITED = set()

    # 3. insert (start_node, cost = 0) into Q
    # we also track the path taken so far for reporting purposes
    heapq.heappush(Q, (0, start_node, [start_node]))

    # 4. while Q is not empty
    while Q:
        # current_node, current_cost <- remove the lowest-cost pair from Q
        current_cost, current_node, path = heapq.heappop(Q)

        # 4.1 if current_node == goal_node
        if current_node == goal_node:
            return "Goal Found", current_cost, path

        # 4.2 if current_node not in VISITED
        if current_node not in VISITED:
            # add current_node to VISITED
            VISITED.add(current_node)

            # 4.2.1 for each neighbor in Graph.neighbors(current_node)
            for neighbor, cost in graph.get(current_node, []):
                # 4.2.1.1 if neighbor not in VISITED
                if neighbor not in VISITED:
                    new_cost = current_cost + cost
                    heapq.heappush(Q, (new_cost, neighbor, path + [neighbor]))

    return "Goal Not Found", None, None


if __name__ == "__main__":
    # Sample navigation graph: node -> list of (neighbor, cost)
    graph = {
        "A": [("B", 4), ("C", 2)],
        "B": [("D", 5)],
        "C": [("B", 1), ("D", 8), ("E", 10)],
        "D": [("E", 2), ("F", 6)],
        "E": [("F", 3)],
        "F": [],
    }

    start = "A"
    goal = "F"

    result, cost, path = ucs(graph, start, goal)

    print(f"Start Node : {start}")
    print(f"Goal Node  : {goal}")
    print(f"Result     : {result}")

    if result == "Goal Found":
        print(f"Total Cost : {cost}")
        print(f"Path       : {' -> '.join(path)}")