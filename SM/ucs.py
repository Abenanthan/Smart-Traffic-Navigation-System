import heapq


def ucs(graph, start_node, goal_node):

    Q = []                      #  empty priority queue
    VISITED = set()             #  empty visited set

    heapq.heappush(Q, (0, start_node, [start_node]))  # the starting node is pushed into the queue

    step = 0                  

    while Q:                    # while Q is not empty

        current_cost, current_node, path = heapq.heappop(Q)

        step += 1

        print(f"\nStep {step}")
        print("Selected Node:", current_node)
        print("Current Cost:", current_cost)
        print("Current Path:", " -> ".join(path))

        if current_node == goal_node:

            print("Goal Found!")

            return "Goal Found", current_cost, path

        if current_node not in VISITED:

            VISITED.add(current_node)

            print("Visited:", VISITED)

            for neighbor, cost in graph.get(current_node, []):

                if neighbor not in VISITED:

                    new_cost = current_cost + cost

                    print(
                        f"Adding {neighbor} "
                        f"with cost {new_cost}"
                    )

                    heapq.heappush(
                        Q,
                        (new_cost, neighbor, path + [neighbor])
                    )

    return "Goal Not Found", None, None