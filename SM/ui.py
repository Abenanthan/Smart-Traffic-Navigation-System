import tkinter as tk
from tkinter import ttk

from ucs import ucs
from road_rules import ROAD_RULES, build_graph


# ============================================================
# GRAPH
# ============================================================

graph = build_graph(ROAD_RULES)


# ============================================================
# WINDOW
# ============================================================

root = tk.Tk()
root.title("Smart Traffic Navigation System")
root.geometry("900x650")
root.resizable(False, False)


# ============================================================
# TITLE
# ============================================================

title = tk.Label(
    root,
    text="SMART TRAFFIC NAVIGATION SYSTEM",
    font=("Arial", 22, "bold")
)

title.pack(pady=15)


# ============================================================
# MAIN FRAME
# ============================================================

main_frame = tk.Frame(root)
main_frame.pack(fill="both", expand=True, padx=20, pady=10)


# ============================================================
# GRAPH FRAME
# ============================================================

graph_frame = tk.LabelFrame(
    main_frame,
    text="Road Network",
    font=("Arial", 13, "bold"),
    width=550,
    height=500
)

graph_frame.pack(side="left", fill="both", expand=True, padx=(0, 10))
graph_frame.pack_propagate(False)


canvas = tk.Canvas(
    graph_frame,
    width=520,
    height=450,
    bg="white"
)

canvas.pack(padx=10, pady=10)


# ============================================================
# NODE POSITIONS
# ============================================================

positions = {
    "A": (100, 220),
    "B": (250, 100),
    "C": (250, 340),
    "D": (400, 220),
    "E": (480, 380)
}


# ============================================================
# DRAW GRAPH
# ============================================================

def draw_graph():

    canvas.delete("all")

    # Draw roads
    drawn_edges = set()

    for start, end, cost in ROAD_RULES:

        edge = tuple(sorted((start, end)))

        if edge in drawn_edges:
            continue

        drawn_edges.add(edge)

        x1, y1 = positions[start]
        x2, y2 = positions[end]

        canvas.create_line(
            x1,
            y1,
            x2,
            y2,
            width=3,
            fill="gray"
        )

        # Cost position
        mid_x = (x1 + x2) / 2
        mid_y = (y1 + y2) / 2

        canvas.create_text(
            mid_x,
            mid_y - 10,
            text=str(cost),
            font=("Arial", 11, "bold"),
            fill="black"
        )

    # Draw nodes
    for node, (x, y) in positions.items():

        canvas.create_oval(
            x - 25,
            y - 25,
            x + 25,
            y + 25,
            fill="lightblue",
            outline="black",
            width=2
        )

        canvas.create_text(
            x,
            y,
            text=node,
            font=("Arial", 14, "bold")
        )


draw_graph()


# ============================================================
# CONTROL FRAME
# ============================================================

control_frame = tk.LabelFrame(
    main_frame,
    text="Navigation",
    font=("Arial", 13, "bold"),
    width=280,
    height=500
)

control_frame.pack(side="right", fill="both", padx=(10, 0))
control_frame.pack_propagate(False)


# ============================================================
# START LOCATION
# ============================================================

tk.Label(
    control_frame,
    text="Start Location",
    font=("Arial", 12)
).pack(pady=(30, 5))


start_combo = ttk.Combobox(
    control_frame,
    values=list(graph.keys()),
    state="readonly",
    width=18
)

start_combo.pack()
start_combo.set("A")


# ============================================================
# DESTINATION
# ============================================================

tk.Label(
    control_frame,
    text="Destination",
    font=("Arial", 12)
).pack(pady=(25, 5))


goal_combo = ttk.Combobox(
    control_frame,
    values=list(graph.keys()),
    state="readonly",
    width=18
)

goal_combo.pack()
goal_combo.set("E")


# ============================================================
# RESULT LABELS
# ============================================================

route_label = tk.Label(
    control_frame,
    text="Optimal Route: -",
    font=("Arial", 11),
    wraplength=230
)

route_label.pack(pady=(40, 8))


cost_label = tk.Label(
    control_frame,
    text="Total Cost: -",
    font=("Arial", 11)
)

cost_label.pack(pady=8)


status_label = tk.Label(
    control_frame,
    text="Status: -",
    font=("Arial", 11)
)

status_label.pack(pady=8)


# ============================================================
# HIGHLIGHT OPTIMAL ROUTE
# ============================================================

def highlight_route(path):

    # Redraw normal graph first
    draw_graph()

    # Highlight route edges
    for i in range(len(path) - 1):

        start = path[i]
        end = path[i + 1]

        x1, y1 = positions[start]
        x2, y2 = positions[end]

        canvas.create_line(
            x1,
            y1,
            x2,
            y2,
            width=7,
            fill="red"
        )

    # Redraw nodes on top
    for node, (x, y) in positions.items():

        canvas.create_oval(
            x - 25,
            y - 25,
            x + 25,
            y + 25,
            fill="lightblue",
            outline="black",
            width=2
        )

        canvas.create_text(
            x,
            y,
            text=node,
            font=("Arial", 14, "bold")
        )


# ============================================================
# FIND ROUTE
# ============================================================

def find_route():

    start_node = start_combo.get()
    goal_node = goal_combo.get()

    if not start_node or not goal_node:

        status_label.config(
            text="Status: Select both locations"
        )

        return

    status, cost, path = ucs(
        graph,
        start_node,
        goal_node
    )

    if status == "Goal Found":

        route_label.config(
            text="Optimal Route: " + " → ".join(path)
        )

        cost_label.config(
            text="Total Cost: " + str(cost)
        )

        status_label.config(
            text="Status: Goal Found"
        )

        highlight_route(path)

    else:

        route_label.config(
            text="Optimal Route: Not Found"
        )

        cost_label.config(
            text="Total Cost: -"
        )

        status_label.config(
            text="Status: Goal Not Found"
        )

        draw_graph()


# ============================================================
# BUTTON
# ============================================================

find_button = tk.Button(
    control_frame,
    text="FIND ROUTE",
    command=find_route,
    font=("Arial", 12, "bold"),
    width=18
)

find_button.pack(pady=30)


# ============================================================
# START APPLICATION
# ============================================================

root.mainloop()