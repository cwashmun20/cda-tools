import dance
import dancer

class Partnership:
    """Representation of a partnership."""

    names = ""
    lead = None
    follow = None
    newcomers = None
    nc_beginners = None
    entries = []

    def __init__(self, leader: dancer.Dancer, follower: dancer.Dancer):
        """Create a partnership from two dancers."""
        
        self.names = leader.name + " & " + follower.name
        self.lead = leader
        self.follow = follower
        self.newcomers = leader.newcomer() and follower.newcomer()
        self.nc_beginners = leader.nc_beginner() and follower.nc_beginner()
        self.entries = set()

    def __repr__(self) -> str:
        """String representation of a partnership with registration-relevant 
        information.
        """
        return self.names
    
    # TODO (CWA): Future feature: add recommended levels for each syllabus style,
    #             AKA the lowest common level where neither dancer has pointed
    #             out of any dances, plus the level above that. Will need to
    #             ignore Newcomer if dancers are ineligible. 

    # TODO (CWA): Change or remove default value of rv_ruleset depending on convention in Fall 2024.
    # TODO (CWA): Implement a way to pass on the reason why eligibility was denied.
    def eligible(self, dance_obj: dance.Dance, rv_ruleset: str = "newcomer") -> bool:
        """Returns a boolean corresponding to whether a couple is eligible for
        a certain dance at a certain level.

        Args:
            dance_obj: a Dance object used to determine eligibility for that dance.
            rv_ruleset: a string, either "newcomer" or "level", based on which
                        ruleset a competition uses for rookie-vet eligibility:
                        "newcomer": rookies == newcomers; vets == non-newcomers;
                        "level": rookies == newcomer/bronze dancer; vets == silver+ dancers.
        Returns:
            True if a couple is eligible for the dance; otherwise False.
        Prints:
            The couple's name, dance, and violation description if ineligible for an event.
        Raises:
            ValueError: if the ruleset is not recognized. 
        """
        # Everyone is always eligible for int./adv. Nightclub and Championship
        if dance_obj.level == dance.NC_LEVELS[-1] or dance_obj.level == dance.OPEN_LEVELS[-1]:
            return True

        # Check eligibility for Beginner Nightclub
        if dance_obj.level == dance.NC_LEVELS[0]:
            if self.nc_beginners:
                return True
            else:
                print(f"NIGHTCLUB BEGINNER VIOLATION: '{self.names}' are ineligible for '{dance_obj}'.")
                return False

        # Check eligibility for Newcomer
        if dance_obj.level == dance.SYLLABUS_LEVELS[0]:
            if self.newcomers:
                return True
            else:
                print(f"NEWCOMER VIOLATION: '{self.names}' ineligible for '{dance_obj}'.")
                return False
        
        # Check eligibility for Rookie/Vet
        if rv_ruleset == "newcomer":
            # Check Rookie Lead
            if dance_obj.level == dance.ALL_LEVELS[-2]:
                if self.lead.newcomer() and not self.follow.newcomer():
                    return True
                else:
                    print(f"ROOKIE-LEAD VIOLATION: '{self.names}' ineligible for '{dance_obj}'.")
                    print(f"\tLead ({self.lead}) is rookie: {self.lead.newcomer()}.")
                    print(f"\tFollow ({self.follow}) is vet: {not self.follow.newcomer()}.")
                    print()
                    return False
            # Check Rookie Follow
            elif dance_obj.level == dance.ALL_LEVELS[-1]:
                if self.follow.newcomer() and not self.lead.newcomer():
                    return True
                else:
                    print(f"ROOKIE-FOLLOW VIOLATION: '{self.names}' ineligible for '{dance_obj}'.")
                    print(f"\tLead ({self.lead}) is vet: {not self.lead.newcomer()}.")
                    print(f"\tFollow ({self.follow}) is rookie: {self.follow.newcomer()}.")
                    print()
                    return False

        elif rv_ruleset == "level":
            # Check Rookie Lead
            if dance_obj.level == dance.ALL_LEVELS[-2]:
                # TODO (CWA): Rename and update has_BLANK_entries so that negation isn't needed.
                rookie_lead = not self.lead.has_vet_entries(dance_obj.style)
                vet_follow = not self.follow.has_rookie_entries(dance_obj.style)
                if rookie_lead and vet_follow:
                    return True
                else:
                    print(f"ROOKIE-LEAD VIOLATION: '{self.names}' ineligible for '{dance_obj}'.")
                    print(f"\tLead ({self.lead}) is rookie: {rookie_lead}.")
                    print(f"\tFollow ({self.follow}) is vet: {vet_follow}.")
                    print()
                    return False
            # Check Rookie Follow
            elif dance_obj.level == dance.ALL_LEVELS[-1]:
                rookie_follow = not self.follow.has_vet_entries(dance_obj.style)
                vet_lead = not self.lead.has_rookie_entries(dance_obj.style)
                if rookie_follow and vet_lead:
                    return True
                else:
                    print(f"ROOKIE-FOLLOW VIOLATION: '{self.names}' ineligible for '{dance_obj}'.")
                    print(f"\tLead ({self.lead}) is vet: {vet_lead}.")
                    print(f"\tFollow ({self.follow}) is rookie: {rookie_follow}.")
                    print()
                    return False
        elif rv_ruleset not in ["newcomer", "level"]:
            raise ValueError(f"'{rv_ruleset}' is an invalid Rookie/Vet ruleset.")

        lead_level = self.lead.proficiency_level(dance_obj)
        follow_level = self.follow.proficiency_level(dance_obj)
        event_level = dance.FLC_LEVELS.index(dance_obj.level)

        # Check for Split-Level Exception and Pointing Out
        if abs(lead_level - follow_level) >= 2:
            combined_level = max(lead_level, follow_level) - 1
            if combined_level == event_level:
                print(f"""SPLIT-LEVEL EXCEPTION (NOT a violation): '{self.names}' are competing '{dance_obj}' 
                    under the Split-Level Exception. Be sure to award 3x points 
                    if points are awarded to this couple for this event.""")
                # TODO (CWA): If this is how combined_level is assigned, sync this
                #             with the couple's entries and awarded points to award 
                #             3x points, if applicable.
        else:
            combined_level = max(lead_level, follow_level)

        if combined_level <= event_level:
            return True
        else:
            lead_eligibility = dance.FLC_LEVELS[lead_level]
            follow_eligibility = dance.FLC_LEVELS[follow_level]
            print(f"POINTED OUT VIOLATION: '{self.names}' are ineligible for '{dance_obj}'")
            print(f"\t{self.lead} lowest allowed level is {lead_eligibility}.")
            print(f"\t{self.follow} lowest allowed level is {follow_eligibility}.")
            print()
            return False
    
    def add(self, entry_obj):
        """Adds a competition entry for a couple. Should only be called within the Entry constructor."""
        self.entries.add(entry_obj)
        self.lead.add(entry_obj)
        self.follow.add(entry_obj)

    def drop(self, entry_obj):
        """Drops a competition entry for a couple."""
        self.entries.remove(entry_obj)
        self.lead.drop(entry_obj)
        self.follow.drop(entry_obj)