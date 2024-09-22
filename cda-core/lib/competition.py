from datetime import date
import pandas as pd

class Competition:
    """Representation of a CDA competition."""

    raw_data = pd.DataFrame()
    comp_name = ""
    comp_date = date()
    partnerships = {}  # Partnership name keys, Partnership object values.