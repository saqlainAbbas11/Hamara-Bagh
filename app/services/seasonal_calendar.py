"""
Maps the current month to South Asia's Rabi (winter) / Kharif (summer)
agricultural seasons and returns which plants in our dataset are good to
sow right now. This is a genuinely useful, under-served feature for a
Pakistan-focused audience - most global plant apps ignore local seasonality.
"""
from app.models import Plant

RABI_MONTHS = {10, 11, 12, 1}     # sown Oct-Dec, harvested Mar-May
KHARIF_MONTHS = {4, 5, 6}         # sown Apr-Jun, harvested Sep-Oct
TRANSITION_MONTHS = {2, 3, 7, 8, 9}


def current_agri_season(month: int) -> dict:
    if month in RABI_MONTHS:
        name = "rabi"
        label = "Rabi (winter) sowing season"
        description = "Good time to sow winter/cool-season crops - spinach, fenugreek, petunia, and to plant roses."
    elif month in KHARIF_MONTHS:
        name = "kharif"
        label = "Kharif (summer/monsoon) sowing season"
        description = "Good time to sow heat-loving crops - chili, basil, zinnia - ahead of the monsoon."
    else:
        name = "transition"
        label = "Transition period"
        description = "Between main sowing seasons - good time to prep beds, or grow fast perennials/houseplants."

    return {"season": name, "label": label, "description": description}


def what_to_sow_now(month: int, limit: int = 20):
    plants = Plant.query.all()
    matches = []
    for p in plants:
        sow_months = p.sow_months or []
        if month in sow_months or p.season == "perennial":
            matches.append(p)

    # Prioritize plants whose sowing window is this month over perennials
    matches.sort(key=lambda p: (month not in (p.sow_months or []), p.common_name))
    return [p.to_dict() for p in matches[:limit]]
