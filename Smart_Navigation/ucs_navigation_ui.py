import heapq
import tkinter as tk
from tkinter import ttk, messagebox

def ucs(graph, start_node, goal_node):
   
    Q = []                      #  empty priority queue
    VISITED = set()             #  empty visited set

    heapq.heappush(Q, (0, start_node, [start_node]))    # the starting node is pushed into the queue

    while Q:                                            # while Q is not empty
        current_cost, current_node, path = heapq.heappop(Q)

        if current_node == goal_node:                   
            return "Goal Found", current_cost, path

        if current_node not in VISITED:                
            VISITED.add(current_node)

            for neighbor, cost in graph.get(current_node, []):   
                if neighbor not in VISITED:          #ignoring the visited nodes             
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
    "A": (80, 250),
    "B": (250, 100),
    "C": (250, 400),
    "D": (450, 250),
    "E": (620, 400),
    "F": (620, 100),
}


# ---------------------------------------------------------
# MINIMAL TKINTER UI
# ---------------------------------------------------------
class UCSApp:
    def __init__(self, root):
        self.root = root
        self.root.title("UCS Navigation System")

        nodes = list(GRAPH.keys())

        # --- Controls frame ---
        controls = tk.Frame(root)
        controls.pack(side=tk.TOP, fill=tk.X, padx=10, pady=10)

        tk.Label(controls, text="Start Node:").grid(row=0, column=0, padx=5)
        self.start_var = tk.StringVar(value=nodes[0])
        self.start_menu = ttk.Combobox(
            controls, textvariable=self.start_var, values=nodes, state="readonly", width=8
        )
        self.start_menu.grid(row=0, column=1, padx=5)

        tk.Label(controls, text="Goal Node:").grid(row=0, column=2, padx=5)
        self.goal_var = tk.StringVar(value=nodes[-1])
        self.goal_menu = ttk.Combobox(
            controls, textvariable=self.goal_var, values=nodes, state="readonly", width=8
        )
        self.goal_menu.grid(row=0, column=3, padx=5)

        run_btn = tk.Button(controls, text="Find Path (UCS)", command=self.run_ucs)
        run_btn.grid(row=0, column=4, padx=15)

        self.result_label = tk.Label(root, text="Select start and goal, then click 'Find Path'.",
                                      font=("Arial", 11))
        self.result_label.pack(side=tk.TOP, pady=(0, 10))

        # --- Canvas to draw the graph ---
        self.canvas = tk.Canvas(root, width=720, height=480, bg="white")
        self.canvas.pack(padx=10, pady=10)

        self.draw_graph()

    def draw_graph(self, highlight_path=None):
        self.canvas.delete("all")
        highlight_path = highlight_path or []
        highlight_edges = set(zip(highlight_path, highlight_path[1:]))

        # draw edges first (so nodes sit on top)
        for node, neighbors in GRAPH.items():
            x1, y1 = NODE_POSITIONS[node]
            for neighbor, cost in neighbors:
                x2, y2 = NODE_POSITIONS[neighbor]
                key = (node, neighbor)
                is_path_edge = key in highlight_edges
                color = "red" if is_path_edge else "gray"
                width = 3 if is_path_edge else 1
                self.canvas.create_line(x1, y1, x2, y2, fill=color, width=width, arrow=tk.LAST)

                mx, my = (x1 + x2) / 2, (y1 + y2) / 2
                self.canvas.create_text(mx, my - 10, text=str(cost), fill="blue")

        # draw nodes
        for node, (x, y) in NODE_POSITIONS.items():
            fill = "lightgreen" if node in highlight_path else "lightblue"
            self.canvas.create_oval(x - 20, y - 20, x + 20, y + 20, fill=fill, outline="black")
            self.canvas.create_text(x, y, text=node, font=("Arial", 12, "bold"))

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