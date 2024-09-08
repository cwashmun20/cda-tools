import dance
import dancer
import dancer_points as pts
import numpy as np

class Partnership:
    """Representation of a partnership."""

    names = ""
    lead = None
    follow = None
    newcomers = None
    nc_beginners = None


    def __init__(self, leader: dancer.Dancer, follower: dancer.Dancer):
        """Create a partnership from two dancers."""
        
        self.names = leader.name + " & " + follower.name
        self.lead = leader
        self.follow = follower
        self.newcomers = leader.newcomer() and follower.newcomer()
        self.nc_beginners = leader.nc_beginner() and follower.nc_beginner()

    def __repr__(self) -> str:
        """String representation of a partnership with registration-relevant 
        information.
        """
        string = f"""\
        Names (Lead & Follow): {self.names}
        Newcomers?             {self.newcomers}
        NC Beginners?          {self.nc_beginners}
        """
        # TODO (CWA): Future feature: add recommended levels for each syllabus style,
        #             AKA the lowest common level where neither dancer has pointed
        #             out of any dances, plus the level above that. Will need to
        #             ignore Newcomer if dancers are ineligible. 

    # TODO (CWA): Change default value of rv_ruleset if new ruleset not in effect Fall 2024.
    def eligible(self, dance_obj: dance.Dance, rv_ruleset: str = "newcomer") -> bool:
        """Returns a boolean corresponding to whether a couple is eligible for
        a certain dance at a certain level.
        rv_ruleset should be a string, either "newcomer" or "level" based on
            how rookie-vet eligibility is assigned. 
            "newcomer": rookies == newcomers; vets == non-newcomers
            "level": rookies == newcomer/bronze dancer; vets == silver+ dancers 
        """
        # Check eligibility for Newcomer
        if not self.newcomers and dance_obj.level == dance.SYLLABUS_LEVELS[0]:
            return False

        # Check eligibility for Beginner Nightclub
        if not self.nc_beginners and dance_obj.level == dance.NC_LEVELS[0]:
            return False
        
        # Check eligibility for Rookie/Vet
        if rv_ruleset == "newcomer":
            # Check Rookie Lead
            if dance_obj.level == dance.ALL_LEVELS[-2]:
                return self.lead.newcomer() and not self.follow.newcomer()
            # Check Rookie Follow
            elif dance_obj.level == dance.ALL_LEVELS[-1]:
                return self.follow.newcomer and not self.lead.newcomer()     
        elif rv_ruleset == "level":
            # TODO (CWA): Checking rookie/vet based on dancer level will require 
            #             keeping a list of each dancer's entries.
            raise NotImplementedError("TODO (CWA) in partnership.py: Checking rookie/vet based on dancer level will require keeping a list of each dancer's entries.")
        elif rv_ruleset not in ["newcomer", "level"]:
            raise ValueError("Invalid Rookie/Vet ruleset.")

        lead_level = self.lead.points.proficiency_level(dance_obj)
        follow_level = self.follow.points.proficiency_level(dance_obj)
        event_level = dance.FLC_LEVELS.index(dance_obj.level)

        # Check for Split-Level Exception and Pointing Out
        if abs(lead_level - follow_level) >= 2:
            combined_level = max(lead_level, follow_level) - 1
            # TODO (CWA): If this is how combined_level is assigned, sync this
            #             with the couple's entries and awarded points, if applicable.
        else:
            combined_level = max(lead_level, follow_level)

        return combined_level <= event_level

