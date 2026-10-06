import tkinter as tk
from tkinter import ttk

from ucs import ucs
from road_rules import build_graph
from graph_scenarios import GRAPH_SCENARIOS


# ============================================================
# MAIN WINDOW
# ============================================================

root = tk.Tk()
root.title("Smart Traffic Navigation System")
root.geometry("1000x700")
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
main_frame.pack(
    fill="both",
    expand=True,
    padx=20,
    pady=10
)


# ============================================================
# GRAPH FRAME
# ============================================================

graph_frame = tk.LabelFrame(
    main_frame,
    text="Road Network",
    font=("Arial", 13, "bold"),
    width=620,
    height=550
)

graph_frame.pack(
    side="left",
    fill="both",
    expand=True,
    padx=(0, 10)
)

graph_frame.pack_propagate(False)


canvas = tk.Canvas(
    graph_frame,
    width=580,
    height=500,
    bg="white"
)

canvas.pack(
    padx=10,
    pady=10
)


# ============================================================
# CONTROL FRAME
# ============================================================

control_frame = tk.LabelFrame(
    main_frame,
    text="Navigation",
    font=("Arial", 13, "bold"),
    width=300,
    height=550
)

control_frame.pack(
    side="right",
    fill="both",
    padx=(10, 0)
)

control_frame.pack_propagate(False)


# ============================================================
# CURRENT GRAPH DATA
# ============================================================

current_graph = {}
current_positions = {}


# ============================================================
# DRAW GRAPH
# ============================================================

def draw_graph():

    canvas.delete("all")

    if not current_graph:
        return

    drawn_edges = set()

    # --------------------------------------------------------
    # Draw roads
    # --------------------------------------------------------

    for start, neighbors in current_graph.items():

        for end, cost in neighbors:

            edge = tuple(sorted((start, end)))

            if edge in drawn_edges:
                continue

            drawn_edges.add(edge)

            if start not in current_positions:
                continue

            if end not in current_positions:
                continue

            x1, y1 = current_positions[start]
            x2, y2 = current_positions[end]

            # Road
            canvas.create_line(
                x1,
                y1,
                x2,
                y2,
                width=3,
                fill="gray"
            )

            # Cost label position
            mid_x = (x1 + x2) / 2
            mid_y = (y1 + y2) / 2

            canvas.create_rectangle(
                mid_x - 13,
                mid_y - 11,
                mid_x + 13,
                mid_y + 11,
                fill="white",
                outline=""
            )

            canvas.create_text(
                mid_x,
                mid_y,
                text=str(cost),
                font=("Arial", 11, "bold")
            )

    # --------------------------------------------------------
    # Draw nodes
    # --------------------------------------------------------

    for node in current_graph:

        if node not in current_positions:
            continue

        x, y = current_positions[node]

        canvas.create_oval(
            x - 28,
            y - 28,
            x + 28,
            y + 28,
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
# HIGHLIGHT OPTIMAL ROUTE
# ============================================================

def highlight_route(path):

    draw_graph()

    # --------------------------------------------------------
    # Highlight route roads
    # --------------------------------------------------------

    for i in range(len(path) - 1):

        start = path[i]
        end = path[i + 1]

        if start not in current_positions:
            continue

        if end not in current_positions:
            continue

        x1, y1 = current_positions[start]
        x2, y2 = current_positions[end]

        canvas.create_line(
            x1,
            y1,
            x2,
            y2,
            width=7,
            fill="red"
        )

    # --------------------------------------------------------
    # Redraw nodes
    # --------------------------------------------------------

    for node in current_graph:

        if node not in current_positions:
            continue

        x, y = current_positions[node]

        if node in path:
            fill_color = "lightgreen"
        else:
            fill_color = "lightblue"

        canvas.create_oval(
            x - 28,
            y - 28,
            x + 28,
            y + 28,
            fill=fill_color,
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
# GRAPH SCENARIO
# ============================================================

tk.Label(
    control_frame,
    text="Graph Scenario",
    font=("Arial", 12)
).pack(
    pady=(25, 5)
)


scenario_combo = ttk.Combobox(
    control_frame,
    values=list(GRAPH_SCENARIOS.keys()),
    state="readonly",
    width=27
)

scenario_combo.pack(pady=5)


scenario_combo.set(
    list(GRAPH_SCENARIOS.keys())[0]
)


# ============================================================
# START LOCATION
# ============================================================

tk.Label(
    control_frame,
    text="Start Location",
    font=("Arial", 12)
).pack(
    pady=(25, 5)
)


start_combo = ttk.Combobox(
    control_frame,
    state="readonly",
    width=20
)

start_combo.pack(pady=5)


# ============================================================
# DESTINATION
# ============================================================

tk.Label(
    control_frame,
    text="Destination",
    font=("Arial", 12)
).pack(
    pady=(20, 5)
)


goal_combo = ttk.Combobox(
    control_frame,
    state="readonly",
    width=20
)

goal_combo.pack(pady=5)


# ============================================================
# RESULTS
# ============================================================

route_label = tk.Label(
    control_frame,
    text="Optimal Route: -",
    font=("Arial", 11),
    wraplength=260
)

route_label.pack(
    pady=(35, 8)
)


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
# UPDATE SCENARIO
# ============================================================

def update_scenario(event=None):

    global current_graph
    global current_positions

    selected_scenario = scenario_combo.get()

    # Get selected scenario
    scenario = GRAPH_SCENARIOS[selected_scenario]

    # Get roads
    road_rules = scenario["roads"]

    # Get node positions
    current_positions = scenario["positions"]

    # Build graph
    current_graph = build_graph(road_rules)

    # Get available nodes
    nodes = list(current_graph.keys())

    # Update start dropdown
    start_combo["values"] = nodes

    # Update goal dropdown
    goal_combo["values"] = nodes

    # Set default start
    if nodes:
        start_combo.set(nodes[0])

    # Set default destination
    if len(nodes) > 1:
        goal_combo.set(nodes[-1])
    elif nodes:
        goal_combo.set(nodes[0])

    # Reset result
    route_label.config(
        text="Optimal Route: -"
    )

    cost_label.config(
        text="Total Cost: -"
    )

    status_label.config(
        text="Status: -"
    )

    # Draw selected scenario
    draw_graph()


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
        current_graph,
        start_node,
        goal_node
    )

    if status == "Goal Found":

        route_label.config(
            text="Optimal Route:\n" +
                 " → ".join(path)
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
# FIND ROUTE BUTTON
# ============================================================

find_button = tk.Button(
    control_frame,
    text="FIND ROUTE",
    command=find_route,
    font=("Arial", 12, "bold"),
    width=20
)

find_button.pack(pady=25)


# ============================================================
# SCENARIO CHANGE EVENT
# ============================================================

scenario_combo.bind(
    "<<ComboboxSelected>>",
    update_scenario
)


# ============================================================
# LOAD FIRST SCENARIO
# ============================================================

update_scenario()


# ============================================================
# START APPLICATION
# ============================================================

root.mainloop()