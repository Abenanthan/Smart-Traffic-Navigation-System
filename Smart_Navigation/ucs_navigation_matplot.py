import heapq
import tkinter as tk
from tkinter import ttk, messagebox

import matplotlib
matplotlib.use("TkAgg")
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg

#UCS ALGORITHM

#UCS(Graph, start_node, goal_node):
#1. create an empty priority queue Q (lowest cost comes out first)
#2. create an empty set VISITED
#3. insert (start_node, cost = 0) into Q
#4. while Q is not empty:
#current_node, current_cost ← remove the lowest-cost pair from Q
#     4.1 if current_node == goal_node:
#     return "Goal Found" (cost = current_cost)
#     4.2 if current_node not in VISITED:
#            add current_node to VISITED
#            4.2.1 for each neighbor in Graph.neighbors(current_node):
#                     4.2.1.1 if neighbor not in VISITED:
#                                new_cost ← current_cost + cost(current_node, neighbor)
#                                insert (neighbor, new_cost) into Q
#   return "Goal Not Found"

def ucs(graph, start_node, goal_node):
    """
    Uniform Cost Search (UCS)

    graph: dict of {node: [(neighbor, cost), ...]}
    start_node: starting node
    goal_node: goal node

    Returns (result_string, cost, path)
    """
    Q = []                      # 1. empty priority queue
    VISITED = set()             # 2. empty visited set

    heapq.heappush(Q, (0, start_node, [start_node]))   # 3. insert start

    while Q:                                            # 4. while Q not empty
        current_cost, current_node, path = heapq.heappop(Q)

        if current_node == goal_node:                   # 4.1
            return "Goal Found", current_cost, path

        if current_node not in VISITED:                 # 4.2
            VISITED.add(current_node)

            for neighbor, cost in graph.get(current_node, []):   # 4.2.1
                if neighbor not in VISITED:                       # 4.2.1.1
                    new_cost = current_cost + cost
                    heapq.heappush(Q, (new_cost, neighbor, path + [neighbor]))

    return "Goal Not Found", None, None



# SAMPLE GRAPH

GRAPH = {
    "A": [("B", 4), ("C", 2)],
    "B": [("D", 5)],
    "C": [("B", 1), ("D", 8), ("E", 10)],
    "D": [("E", 2), ("F", 6)],
    "E": [("F", 3)],
    "F": [],
}

NODE_POSITIONS = {
    "A": (0, 2.5),
    "B": (2, 4),
    "C": (2, 1),
    "D": (4.5, 2.5),
    "E": (6.5, 1),
    "F": (6.5, 4),
}


# TKINTER UI + MATPLOTLIB GRAPH VIEW

class UCSApp:
    def __init__(self, root):
        self.root = root
        self.root.title("UCS Navigation System (matplotlib)")

        nodes = list(GRAPH.keys())

        controls = tk.Frame(root)
        controls.pack(side=tk.TOP, fill=tk.X, padx=10, pady=10)

        tk.Label(controls, text="Start Node:").grid(row=0, column=0, padx=5)
        self.start_var = tk.StringVar(value=nodes[0])
        ttk.Combobox(controls, textvariable=self.start_var, values=nodes,
                     state="readonly", width=8).grid(row=0, column=1, padx=5)

        tk.Label(controls, text="Goal Node:").grid(row=0, column=2, padx=5)
        self.goal_var = tk.StringVar(value=nodes[-1])
        ttk.Combobox(controls, textvariable=self.goal_var, values=nodes,
                     state="readonly", width=8).grid(row=0, column=3, padx=5)

        tk.Button(controls, text="Find Path (UCS)",
                  command=self.run_ucs).grid(row=0, column=4, padx=15)

        self.result_label = tk.Label(root, text="Select start and goal, then click 'Find Path'.",
                                      font=("Arial", 11))
        self.result_label.pack(side=tk.TOP, pady=(0, 5))

        
        self.fig, self.ax = plt.subplots(figsize=(7, 4.5))
        self.canvas = FigureCanvasTkAgg(self.fig, master=root)
        self.canvas.get_tk_widget().pack(padx=10, pady=10)

        self.draw_graph()

    def draw_graph(self, highlight_path=None):
        self.ax.clear()
        highlight_path = highlight_path or []
        highlight_edges = set(zip(highlight_path, highlight_path[1:]))

        
        for node, neighbors in GRAPH.items():
            x1, y1 = NODE_POSITIONS[node]
            for neighbor, cost in neighbors:
                x2, y2 = NODE_POSITIONS[neighbor]
                is_path_edge = (node, neighbor) in highlight_edges
                color = "red" if is_path_edge else "gray"
                width = 2.5 if is_path_edge else 1

                self.ax.annotate(
                    "", xy=(x2, y2), xytext=(x1, y1),
                    arrowprops=dict(arrowstyle="->", color=color, lw=width),
                )
                mx, my = (x1 + x2) / 2, (y1 + y2) / 2
                self.ax.text(mx, my, str(cost), color="blue", fontsize=9,
                              ha="center", va="center",
                              bbox=dict(boxstyle="round,pad=0.1", fc="white", ec="none"))

        
        for node, (x, y) in NODE_POSITIONS.items():
            face = "lightgreen" if node in highlight_path else "lightblue"
            self.ax.scatter([x], [y], s=900, color=face, edgecolors="black", zorder=3)
            self.ax.text(x, y, node, fontsize=12, fontweight="bold",
                          ha="center", va="center", zorder=4)

        self.ax.set_xlim(-1.5, 8)
        self.ax.set_ylim(-0.5, 5.5)
        self.ax.axis("off")
        self.ax.set_title("UCS Navigation Graph")
        self.canvas.draw()

    def run_ucs(self):
        start = self.start_var.get()
        goal = self.goal_var.get()

        result, cost, path = ucs(GRAPH, start, goal)

        if result == "Goal Found":
            self.result_label.config(
                text=f"Result: {result}   |   Cost: {cost}   |   Path: {' -> '.join(path)}"
            )
            self.draw_graph(highlight_path=path)
        else:
            self.result_label.config(text=f"Result: {result}")
            self.draw_graph()
            messagebox.showinfo("UCS Result", f"No path found from {start} to {goal}.")


if __name__ == "__main__":
    root = tk.Tk()
    app = UCSApp(root)
    root.mainloop()