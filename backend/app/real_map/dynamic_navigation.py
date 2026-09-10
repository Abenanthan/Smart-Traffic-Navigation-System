"""Large-map orchestration: the same UCS, with its existing trace switch off.

The original educational session and engine remain untouched. Only these two
entry points differ; route construction, traffic and cost comparison are inherited.
"""
from .. import navigation
from ..navigation import NavigationResult, RerouteDecision
from .service import GeographicNavigation


class DynamicNavigation(GeographicNavigation):
    def find_route(self, source_text, destination_text):
        validation = self.input_processing.validate(source_text, destination_text)
        if not validation.valid:
            self.active_route = None
            return NavigationResult(False, RerouteDecision.NO_ROUTE, 'No route available', validation.message, validation=validation)
        request = validation.request
        search = navigation.uniform_cost_search(self.graph, request.source, request.destination, record_trace=False)
        self.last_search = search
        self.active_route = self._build_route(search) if search.found else None
        result = NavigationResult(
            search.found, RerouteDecision.INITIAL_ROUTE if search.found else RerouteDecision.NO_ROUTE,
            'Optimal route found' if search.found else 'No route available',
            f'Uniform Cost Search found the lowest cost among the loaded roads after exploring {search.explored_count} junctions.' if search.found else search.failure_reason,
            route=self.active_route, search=search, validation=validation)
        self.history.append(result)
        return result

    def _recalculate(self, update):
        previous = self.active_route
        cost = self.graph.path_cost(previous.path)
        search = navigation.uniform_cost_search(self.graph, previous.source, previous.destination, record_trace=False)
        self.last_search = search
        self.active_route = self._build_route(search) if search.found else None
        if not search.found:
            return NavigationResult(False, RerouteDecision.NO_ROUTE, 'No route available',
                                    'No open route connects the selected locations in the loaded roads.',
                                    previous_route=previous, search=search, traffic_update=update)
        return self._decide(previous, cost, self.active_route, search, update)
