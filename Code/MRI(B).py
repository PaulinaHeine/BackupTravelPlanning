import heapq


class Itinerary:
    def __init__(self, route, reliability, expected_arrival, arrival_distribution):
        self.route = route  # Liste der Haltestellen
        self.reliability = reliability  # Wahrscheinlichkeit, dass der Trip funktioniert
        self.expected_arrival = expected_arrival  # Erwartete Ankunftszeit
        self.arrival_distribution = arrival_distribution  # Wahrscheinlichkeitsverteilung der Ankunftszeiten

    def __lt__(self, other):
        """Vergleichsfunktion für Priority Queue, basierend auf kürzester erwarteter Ankunftszeit."""
        return self.expected_arrival < other.expected_arrival


def compute_reliability(prob_arrival_on_time, missed_transfer_prob):
    """Berechnet die Zuverlässigkeit des Backup-Itineraries gemäß Paper-Formel."""
    return prob_arrival_on_time * (1 - missed_transfer_prob)


def most_reliable_itinerary(primary_leg, alternative_legs, missed_transfer_prob, arrival_distribution):
    """
    Algorithmus 2 (MRI): Berechnung der zuverlässigsten Backup-Route gemäß Paper.
    """
    best_itinerary = None
    best_reliability = 0

    for leg in alternative_legs:
        start, end, dep_time, arr_time = leg
        prob_on_time = arrival_distribution(dep_time)  # P(Y_arr_g ≤ τ_dep_h)
        reliability = compute_reliability(prob_on_time, missed_transfer_prob)

        if reliability > best_reliability:
            best_reliability = reliability
            best_itinerary = Itinerary([primary_leg, leg], reliability, arr_time, arrival_distribution)

    return best_itinerary


def most_reliable_itinerary_with_budget(primary_leg, alternative_legs, missed_transfer_prob, arrival_distribution,
                                        max_extra_time):
    """
    Algorithmus 3 (MRIB): Berechnung der zuverlässigsten Backup-Route mit Zeitbudget.
    """
    best_itinerary = None
    best_reliability = 0

    for leg in alternative_legs:
        start, end, dep_time, arr_time = leg
        delay = arr_time - primary_leg[3]  # Zeitverzögerung zur Hauptverbindung

        if delay > max_extra_time:
            continue  # Überspringe zu späte Alternativen

        prob_on_time = arrival_distribution(dep_time)
        reliability = compute_reliability(prob_on_time, missed_transfer_prob)

        if reliability > best_reliability:
            best_reliability = reliability
            best_itinerary = Itinerary([primary_leg, leg], reliability, arr_time, arrival_distribution)

    return best_itinerary
