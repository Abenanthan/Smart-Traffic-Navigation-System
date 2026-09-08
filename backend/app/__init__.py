"""
Smart Traffic Navigation System -- application package.

Six modules, in the order data flows through them:

    Module 1  input_processing.py   validate the user's source and destination
    Module 2  road_network.py       the static road network (nodes and roads)
    Module 3  traffic_data.py       simulated congestion and road status
    Module 4  weighted_graph.py     road network + traffic -> costed edges
    Module 5  ucs_engine.py         Uniform Cost Search over the weighted graph
    Module 6  navigation.py         route presentation and dynamic rerouting

`api.py` exposes these over HTTP; it contains no logic of its own. The system is
fully usable and testable without it -- see demo_cli.py.
"""
