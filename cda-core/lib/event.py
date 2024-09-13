import dance

ROUNDS = ["Final", "Semifinal", "Quarterfinal", "1/8 Final", "1/16 Final", "1/32 Final"]  # We hope we won't have to add more!

class Event:
    """Representation of a competition event."""

    dance = None
    num_rounds = 0
