"""Builds data/flowers.json - the Hamara Bagh ornamental/flower catalog.

Approach: every plant inherits a Pakistan-focused trait set from its group
defaults (water, sun, difficulty, bloom window, pot-friendliness ...), and
per-plant overrides are applied only where the plant genuinely differs
(bloom window, water need, pet safety, fragrance, native status, ...).

Bloom/sow windows are typical for the Pakistan plains (Punjab/Sindh) and
shift a few weeks in the north - the JSON note says this on the page too.

Run:  python scripts/build_flowers_json.py
"""
import json
import os
import re

OUT_PATH = os.path.join(os.path.dirname(__file__), "..", "data", "flowers.json")

GROUPS = {
    "seasonal": {"label": "Seasonal flowers", "emoji": "\U0001F33C",
                 "tip": "Winter/spring annuals: sow in the cool months and deadhead spent blooms to keep them flowering - most wrap up when the heat arrives."},
    "perennial": {"label": "Garden perennials", "emoji": "\U0001F338",
                  "tip": "Tough once established. Feed in spring and after the monsoon, and prune after each flush to keep the flowers coming."},
    "rose": {"label": "Roses", "emoji": "\U0001F339",
             "tip": "Prune hard in December-January and feed after every flush. Water at the base - wet leaves invite black spot."},
    "bulb": {"label": "Bulbs & corms", "emoji": "\U0001F337",
             "tip": "Bulbs rot in soggy soil - use free-draining mix. Let the leaves yellow fully after bloom before cutting; that feeds next year's flowers."},
    "fragrant": {"label": "Fragrant & climbers", "emoji": "\U0001F4AE",
                 "tip": "Plant near a window or your favourite sitting spot. Most love morning sun and a trellis, wall or railing to climb."},
    "palm": {"label": "Palms", "emoji": "\U0001F334",
             "tip": "Steady moisture while young, well-drained soil forever. Trim only fully brown fronds - the green ones are still feeding the palm."},
    "indoor": {"label": "Indoor favourites", "emoji": "\U0001FAF4",
               "tip": "Bright indirect light suits most. Water less in winter and never let pots stand in water."},
    "cactus": {"label": "Cacti", "emoji": "\U0001F335",
               "tip": "Full sun plus grit. Water deeply but only after the mix has been dry for days - overwatering kills more cacti than drought ever will."},
    "succulent": {"label": "Succulents", "emoji": "\U0001F343",
                  "tip": "Let the soil dry fully between waterings. In monsoon, move pots under shelter - rot is the real enemy, not thirst."},
    "tree": {"label": "Flowering trees", "emoji": "\U0001F333",
             "tip": "Plant in spring or at monsoon onset. Water deeply but infrequently once established - the roots will find their own way."},
    "fruit": {"label": "Fruit & orchard", "emoji": "\U0001F34B",
              "tip": "Plant in spring or at monsoon onset. Feed before flowering and after harvest, and thin young fruit for bigger, better quality."},
    "native": {"label": "Wild & native", "emoji": "\U0001F1F5\U0001F1F0",
               "tip": "Local survivors: they already know Pakistan's seasons. Minimal fuss - water only through long dry spells."},
}

# group defaults -> merged into every entry unless overridden
DEFAULTS = {
    "seasonal": dict(water="medium", sun_hours_min=6, sun="full", difficulty="easy",
                     bloom_months=[2, 3, 4], sow_months=[9, 10, 11], pot=True,
                     indoor=False, balcony=True, rooftop=True, ground=True,
                     fragrant=False, pollinator=True, pet_safe=True, native=False,
                     heat="medium", frost="low", salt=False),
    "perennial": dict(water="medium", sun_hours_min=5, sun="full", difficulty="easy",
                      bloom_months=[4, 5, 6, 7, 8, 9], sow_months=[2, 3, 8], pot=True,
                      indoor=False, balcony=True, rooftop=True, ground=True,
                      fragrant=False, pollinator=True, pet_safe=True, native=False,
                      heat="high", frost="low", salt=False),
    "rose": dict(water="medium", sun_hours_min=6, sun="full", difficulty="medium",
                 bloom_months=[3, 4, 5, 9, 10, 11], sow_months=[12, 1, 2], pot=True,
                 indoor=False, balcony=True, rooftop=True, ground=True,
                 fragrant=False, pollinator=True, pet_safe=True, native=False,
                 heat="medium", frost="medium", salt=False),
    "bulb": dict(water="medium", sun_hours_min=5, sun="full", difficulty="medium",
                 bloom_months=[2, 3, 4], sow_months=[10, 11], pot=True,
                 indoor=False, balcony=True, rooftop=True, ground=True,
                 fragrant=False, pollinator=True, pet_safe=True, native=False,
                 heat="medium", frost="medium", salt=False),
    "fragrant": dict(water="medium", sun_hours_min=5, sun="full", difficulty="easy",
                     bloom_months=[5, 6, 7, 8, 9], sow_months=[2, 3, 8], pot=True,
                     indoor=False, balcony=True, rooftop=True, ground=True,
                     fragrant=True, pollinator=True, pet_safe=True, native=False,
                     heat="high", frost="low", salt=False),
    "palm": dict(water="medium", sun_hours_min=5, sun="full", difficulty="easy",
                 bloom_months=[], sow_months=[3, 4], pot=True,
                 indoor=False, balcony=False, rooftop=False, ground=True,
                 fragrant=False, pollinator=False, pet_safe=True, native=False,
                 heat="high", frost="low", salt=True),
    "indoor": dict(water="medium", sun_hours_min=2, sun="part", difficulty="easy",
                   bloom_months=[], sow_months=[], pot=True,
                   indoor=True, balcony=False, rooftop=False, ground=False,
                   fragrant=False, pollinator=False, pet_safe=True, native=False,
                   heat="medium", frost="low", salt=False),
    "cactus": dict(water="very_low", sun_hours_min=6, sun="full", difficulty="very_easy",
                   bloom_months=[4, 5], sow_months=[2, 3, 4], pot=True,
                   indoor=True, balcony=True, rooftop=True, ground=True,
                   fragrant=False, pollinator=True, pet_safe=True, native=False,
                   heat="very_high", frost="low", salt=False),
    "succulent": dict(water="very_low", sun_hours_min=5, sun="full", difficulty="very_easy",
                      bloom_months=[3, 4, 5], sow_months=[2, 3, 4], pot=True,
                      indoor=True, balcony=True, rooftop=True, ground=True,
                      fragrant=False, pollinator=True, pet_safe=True, native=False,
                      heat="high", frost="low", salt=False),
    "tree": dict(water="medium", sun_hours_min=6, sun="full", difficulty="easy",
                 bloom_months=[4, 5], sow_months=[2, 3, 7, 8], pot=False,
                 indoor=False, balcony=False, rooftop=False, ground=True,
                 fragrant=False, pollinator=True, pet_safe=True, native=False,
                 heat="high", frost="low", salt=False),
    "fruit": dict(water="medium", sun_hours_min=6, sun="full", difficulty="medium",
                  bloom_months=[2, 3, 4], sow_months=[2, 3], pot=False,
                  indoor=False, balcony=False, rooftop=False, ground=True,
                  fragrant=False, pollinator=True, pet_safe=True, native=False,
                  heat="high", frost="low", salt=False),
    "native": dict(water="low", sun_hours_min=6, sun="full", difficulty="easy",
                   bloom_months=[4, 5], sow_months=[2, 3, 7, 8], pot=True,
                   indoor=False, balcony=True, rooftop=True, ground=True,
                   fragrant=False, pollinator=True, pet_safe=True, native=True,
                   heat="high", frost="low", salt=True),
}

# override key -> output field
OV = {
    "ln": "local_name", "co": "colors", "w": "water", "sm": "sun_hours_min",
    "su": "sun", "d": "difficulty", "bl": "bloom_months", "sw": "sow_months",
    "fr": "fragrant", "po": "pollinator", "pt": "pet_safe", "nv": "native",
    "sa": "salt", "pot": "pot", "indoor": "indoor",
    "balcony": "balcony", "rooftop": "rooftop", "ground": "ground",
    "ht": "heat", "fo": "frost", "ct": "care",
}

# (name, scientific name, group, {overrides})
PLANTS = [
    # ------------------------------------------------------------- seasonal --
    ("Snapdragon", "Antirrhinum majus", "seasonal", {"ht": "low", "co": ["pink", "red", "yellow", "white", "purple"]}),
    ("Calendula", "Calendula officinalis", "seasonal", {"bl": [1, 2, 3, 4], "ht": "low", "co": ["orange", "yellow"]}),
    ("Aster", "Callistephus chinensis", "seasonal", {"co": ["purple", "pink", "white", "red"]}),
    ("Cosmos", "Cosmos bipinnatus", "seasonal", {"bl": [3, 4, 5, 10, 11], "ht": "high", "co": ["pink", "white"]}),
    ("Dianthus", "Dianthus chinensis", "seasonal", {"co": ["pink", "red", "white"]}),
    ("Sweet William", "Dianthus barbatus", "seasonal", {"fr": True, "co": ["red", "pink", "white"]}),
    ("Sweet Pea", "Lathyrus odoratus", "seasonal", {"bl": [2, 3], "fr": True, "co": ["pink", "purple", "white", "red"]}),
    ("Phlox", "Phlox drummondii", "seasonal", {"co": ["pink", "purple", "red", "white"]}),
    ("Salvia", "Salvia splendens", "seasonal", {"bl": [3, 4, 5, 9, 10, 11], "co": ["red"]}),
    ("Celosia", "Celosia argentea", "seasonal", {"bl": [6, 7, 8, 9, 10], "sw": [3, 4], "ht": "very_high", "sa": True, "co": ["red", "yellow", "orange", "pink"]}),
    ("Portulaca", "Portulaca grandiflora", "seasonal", {"bl": [4, 5, 6, 7, 8, 9], "sw": [3, 4], "w": "low", "ht": "very_high", "sa": True, "co": ["pink", "red", "yellow", "orange", "white", "purple"]}),
    ("Nasturtium", "Tropaeolum majus", "seasonal", {"co": ["orange", "yellow", "red"]}),
    ("Coreopsis", "Coreopsis tinctoria", "seasonal", {"bl": [3, 4, 5, 6], "ht": "high", "co": ["yellow"]}),
    ("Verbena", "Verbena x hybrida", "seasonal", {"bl": [3, 4, 5, 9, 10], "ht": "high", "co": ["purple", "pink", "red", "white"]}),
    ("Sweet Alyssum", "Lobularia maritima", "seasonal", {"fr": True, "co": ["white", "purple"]}),
    ("Gazania", "Gazania rigens", "seasonal", {"bl": [2, 3, 4, 5, 9, 10, 11], "w": "low", "ht": "high", "sa": True, "co": ["yellow", "orange", "pink", "white"]}),
    ("Torenia", "Torenia fournieri", "seasonal", {"su": "part", "sm": 3, "co": ["purple", "pink", "white", "blue"]}),
    ("Impatiens", "Impatiens walleriana", "seasonal", {"su": "part", "sm": 3, "w": "high", "co": ["pink", "red", "white", "orange"]}),
    ("Nicotiana", "Nicotiana alata", "seasonal", {"su": "part", "sm": 4, "co": ["white", "pink"]}),
    ("Candytuft", "Iberis amara", "seasonal", {"co": ["white", "pink"]}),
    ("Cornflower", "Centaurea cyanus", "seasonal", {"co": ["blue", "pink", "white"]}),
    ("Four O'Clock", "Mirabilis jalapa", "seasonal", {"bl": [7, 8, 9, 10], "sw": [3, 4], "ht": "very_high", "fr": True, "co": ["pink", "yellow", "white", "red"]}),
    ("Balsam", "Impatiens balsamina", "seasonal", {"bl": [6, 7, 8, 9], "sw": [3, 4], "ht": "high", "co": ["pink", "red", "white", "purple"]}),
    ("Kochia", "Bassia scoparia", "seasonal", {"bl": [], "sw": [3, 4], "w": "low", "ht": "very_high", "po": False}),
    ("Globe Amaranth", "Gomphrena globosa", "seasonal", {"bl": [5, 6, 7, 8, 9, 10], "sw": [3, 4], "ht": "very_high", "co": ["purple", "pink", "white"]}),
    ("Strawflower", "Xerochrysum bracteatum", "seasonal", {"bl": [4, 5, 6, 7], "ht": "high", "co": ["yellow", "pink", "orange", "red"]}),
    ("African Daisy", "Osteospermum ecklonis", "seasonal", {"co": ["white", "pink", "purple"]}),
    ("French Daisy", "Felicia amelloides", "seasonal", {"co": ["blue"]}),
    ("Swan River Daisy", "Brachyscome iberidifolia", "seasonal", {"co": ["blue", "purple", "white", "pink"]}),
    ("Flax Flower", "Linum grandiflorum", "seasonal", {"ht": "high", "co": ["red"]}),
    ("California Poppy", "Eschscholzia californica", "seasonal", {"bl": [2, 3, 4, 5], "w": "low", "co": ["orange", "yellow"]}),
    ("Love-in-a-Mist", "Nigella damascena", "seasonal", {"bl": [3, 4, 5], "co": ["blue", "white", "pink"]}),
    ("Larkspur", "Delphinium ajacis", "seasonal", {"ht": "low", "co": ["blue", "pink", "white", "purple"]}),
    ("Clarkia", "Clarkia amoena", "seasonal", {"ht": "low", "co": ["pink", "purple", "white"]}),
    ("Chinese Forget-me-not", "Cynoglossum amabile", "seasonal", {"bl": [3, 4], "co": ["blue"]}),
    ("Blanket Flower", "Gaillardia aristata", "seasonal", {"bl": [3, 4, 5, 6], "w": "low", "ht": "very_high", "co": ["red", "yellow"]}),
    ("Mexican Sunflower", "Tithonia rotundifolia", "seasonal", {"bl": [6, 7, 8, 9, 10], "sw": [3, 4], "ht": "very_high", "co": ["orange"]}),
    ("Cleome", "Cleome hassleriana", "seasonal", {"bl": [6, 7, 8, 9], "sw": [3, 4], "ht": "very_high", "co": ["pink", "white", "purple"]}),
    ("Mexican Marigold", "Tagetes lucida", "seasonal", {"bl": [6, 7, 8, 9], "sw": [3, 4], "ht": "high", "co": ["yellow"]}),
    ("Tidy Tips", "Layia platyglossa", "seasonal", {"co": ["yellow", "white"]}),
    ("Swan Plant", "Asclepias physocarpa", "seasonal", {"bl": [6, 7, 8], "pt": False, "co": ["white"]}),
    ("Crown Daisy", "Glebionis coronaria", "seasonal", {"co": ["yellow"]}),
    ("Amaranthus", "Amaranthus tricolor", "seasonal", {"bl": [], "sw": [3, 4], "ht": "very_high", "po": False, "co": ["red"]}),
    # ------------------------------------------------------------ perennial --
    ("Gardenia", "Gardenia jasminoides", "perennial", {"su": "part", "sm": 4, "w": "high", "d": "medium", "fr": True, "bl": [4, 5, 6], "co": ["white"]}),
    ("Ixora", "Ixora coccinea", "perennial", {"sm": 5, "ht": "high", "bl": [4, 5, 6, 7, 8, 9], "co": ["red", "pink", "white"]}),
    ("Plumbago", "Plumbago auriculata", "perennial", {"w": "low", "ht": "very_high", "sa": True, "bl": [5, 6, 7, 8, 9, 10], "co": ["blue"]}),
    ("Lantana", "Lantana camara", "perennial", {"w": "low", "ht": "very_high", "sa": True, "bl": [3, 4, 5, 6, 7, 8, 9, 10], "co": ["pink", "yellow", "red", "orange"]}),
    ("Oleander", "Nerium oleander", "perennial", {"w": "low", "ht": "very_high", "sa": True, "pt": False, "fo": "medium", "bl": [4, 5, 6, 7, 8, 9], "co": ["pink", "white", "red"]}),
    ("Crown Flower", "Calotropis gigantea", "perennial", {"nv": True, "w": "low", "ht": "very_high", "sa": True, "pt": False, "bl": [4, 5, 6, 7], "co": ["purple", "white"]}),
    ("Allamanda", "Allamanda cathartica", "perennial", {"ht": "high", "sa": True, "bl": [5, 6, 7, 8, 9], "co": ["yellow"]}),
    ("Golden Trumpet", "Allamanda schottii", "perennial", {"sa": True, "bl": [5, 6, 7, 8, 9], "co": ["yellow"]}),
    ("Yesterday-Today-Tomorrow", "Brunfelsia pauciflora", "perennial", {"fr": True, "pt": False, "bl": [3, 4, 5, 9, 10], "co": ["purple"]}),
    ("Bottlebrush", "Callistemon citrinus", "perennial", {"ht": "high", "bl": [3, 4, 5, 9, 10], "co": ["red"]}),
    ("Firebush", "Hamelia patens", "perennial", {"ht": "high", "bl": [5, 6, 7, 8, 9, 10], "co": ["red", "orange"]}),
    ("Peacock Flower", "Caesalpinia pulcherrima", "perennial", {"w": "low", "ht": "very_high", "sa": True, "bl": [5, 6, 7, 8, 9, 10], "co": ["red", "yellow", "orange"]}),
    ("Golden Dewdrop", "Duranta erecta", "perennial", {"ht": "high", "pt": False, "bl": [6, 7, 8, 9, 10], "co": ["purple", "blue"]}),
    ("Clerodendrum", "Clerodendrum splendens", "perennial", {"bl": [5, 6, 7, 8, 9], "co": ["red"]}),
    ("Pentas", "Pentas lanceolata", "perennial", {"ht": "high", "bl": [4, 5, 6, 7, 8, 9], "co": ["pink", "red", "purple", "white"]}),
    ("Angelonia", "Angelonia angustifolia", "perennial", {"ht": "very_high", "bl": [5, 6, 7, 8, 9, 10], "co": ["purple", "pink", "white"]}),
    ("Mexican Heather", "Cuphea hyssopifolia", "perennial", {"ht": "high", "bl": [5, 6, 7, 8, 9, 10], "co": ["purple", "pink"]}),
    ("Ruellia", "Ruellia simplex", "perennial", {"ht": "very_high", "bl": [5, 6, 7, 8, 9, 10], "co": ["purple", "pink"]}),
    ("Mexican Bush Sage", "Salvia leucantha", "perennial", {"ht": "medium", "fo": "medium", "bl": [10, 11, 12, 1], "co": ["purple", "white"]}),
    ("Russian Sage", "Salvia yangii", "perennial", {"w": "low", "ht": "high", "fo": "medium", "bl": [6, 7, 8], "co": ["purple"]}),
    ("Lamb's Ear", "Stachys byzantina", "perennial", {"w": "low", "bl": [6, 7]}),
    ("Yarrow", "Achillea millefolium", "perennial", {"w": "low", "bl": [4, 5, 6, 7], "co": ["yellow", "pink", "white", "red"]}),
    ("Lavender", "Lavandula angustifolia", "perennial", {"w": "low", "d": "medium", "fr": True, "fo": "medium", "ht": "high", "bl": [3, 4, 5], "co": ["purple"]}),
    ("Spanish Lavender", "Lavandula stoechas", "perennial", {"w": "low", "d": "medium", "fr": True, "ht": "high", "bl": [2, 3, 4], "co": ["purple"]}),
    ("Bird of Paradise", "Strelitzia reginae", "perennial", {"ht": "high", "w": "medium", "bl": [5, 6, 7, 8], "co": ["orange", "blue"], "ct": "Needs 3-5 years of full sun before the first bird-shaped bloom - worth the wait."}),
    ("Canna Lily", "Canna indica", "perennial", {"w": "high", "ht": "very_high", "bl": [4, 5, 6, 7, 8, 9, 10], "co": ["red", "yellow", "orange", "pink"]}),
    ("Daylily", "Hemerocallis fulva", "perennial", {"ht": "high", "bl": [3, 4, 5], "co": ["orange", "yellow", "red"]}),
    # ------------------------------------------------------------------ rose --
    ("Desi Gulab", "Rosa damascena (local selection)", "rose", {"ln": "Desi Gulab", "fr": True, "co": ["pink", "red"]}),
    ("Damask Rose", "Rosa x damascena", "rose", {"ln": "Surkha Gulab", "fr": True, "co": ["pink", "red"]}),
    ("China Rose", "Rosa chinensis", "rose", {"co": ["red", "pink"]}),
    ("Tea Rose", "Rosa x odorata", "rose", {"fr": True, "co": ["yellow", "pink", "white"]}),
    ("Bourbon Rose", "Rosa bourboniana", "rose", {"fr": True, "co": ["pink", "red"]}),
    ("Centifolia Rose", "Rosa x centifolia", "rose", {"fr": True, "co": ["pink"]}),
    ("Musk Rose", "Rosa moschata", "rose", {"fr": True, "co": ["white"]}),
    ("Rugosa Rose", "Rosa rugosa", "rose", {"fr": True, "co": ["purple", "pink", "white"]}),
    ("Miniature Rose", "Rosa hybrid (miniature)", "rose", {"co": ["red", "pink", "yellow", "white"]}),
    ("Floribunda Rose", "Rosa hybrid (floribunda)", "rose", {"co": ["red", "pink", "yellow", "orange", "white"]}),
    ("Hybrid Tea Rose", "Rosa hybrid (hybrid tea)", "rose", {"fr": True, "co": ["red", "pink", "yellow", "white"]}),
    ("Climbing Rose", "Rosa hybrid (climbing)", "rose", {"fr": True, "co": ["red", "pink", "yellow", "white"]}),
    ("Polyantha Rose", "Rosa hybrid (polyantha)", "rose", {"co": ["pink", "red", "white"]}),
    ("Groundcover Rose", "Rosa hybrid (groundcover)", "rose", {"co": ["pink", "red", "white"]}),
    ("Banksian Rose", "Rosa banksiae", "rose", {"fr": True, "ht": "high", "co": ["yellow", "white"]}),
    ("Sweet Briar", "Rosa rubiginosa", "rose", {"fr": True, "co": ["pink"]}),
    # ------------------------------------------------------------------ bulb --
    ("Tuberose", "Polianthes tuberosa", "bulb", {"bl": [6, 7, 8, 9], "ht": "high", "fr": True, "co": ["white"]}),
    ("Gladiolus", "Gladiolus x hortulanus", "bulb", {"bl": [3, 4, 10, 11], "co": ["red", "pink", "yellow", "white", "purple", "orange"]}),
    ("Freesia", "Freesia x hybrida", "bulb", {"fr": True, "co": ["yellow", "white", "pink", "purple", "red"]}),
    ("Ranunculus", "Ranunculus asiaticus", "bulb", {"pt": False, "co": ["red", "pink", "yellow", "white", "orange"], "ct": "Soak the dry corms overnight before planting - they wake up much faster."}),
    ("Anemone", "Anemone coronaria", "bulb", {"pt": False, "co": ["red", "blue", "white", "purple"]}),
    ("Daffodil", "Narcissus pseudonarcissus", "bulb", {"bl": [1, 2, 3], "pt": False, "co": ["yellow", "white"]}),
    ("Jonquil", "Narcissus jonquilla", "bulb", {"pt": False, "fr": True, "co": ["yellow"]}),
    ("Paperwhite", "Narcissus papyraceus", "bulb", {"bl": [12, 1, 2], "pt": False, "fr": True, "indoor": True, "co": ["white"]}),
    ("Hyacinth", "Hyacinthus orientalis", "bulb", {"bl": [2, 3], "pt": False, "fr": True, "indoor": True, "co": ["purple", "pink", "white", "blue"], "ct": "In the plains, pre-chill bulbs in the fridge (not with fruit) for 4-6 weeks before planting for the best blooms."}),
    ("Tulip", "Tulipa gesneriana", "bulb", {"bl": [2, 3], "pt": False, "co": ["red", "yellow", "pink", "white", "purple"], "ct": "In the plains, pre-chill bulbs in the fridge (not with fruit) for 4-6 weeks before planting - tulips need that false winter."}),
    ("Asiatic Lily", "Lilium (Asiatic hybrids)", "bulb", {"bl": [3, 4, 5], "pt": False, "co": ["red", "pink", "yellow", "orange", "white"]}),
    ("Oriental Lily", "Lilium (Oriental hybrids)", "bulb", {"bl": [6, 7, 8], "pt": False, "fr": True, "co": ["white", "pink"]}),
    ("Amaryllis", "Hippeastrum x hybridum", "bulb", {"bl": [4, 5], "pt": False, "indoor": True, "co": ["red", "pink", "white"]}),
    ("Crinum Lily", "Crinum asiaticum", "bulb", {"bl": [5, 6, 7], "pt": False, "fr": True, "co": ["white", "pink"]}),
    ("Spider Lily", "Hymenocallis littoralis", "bulb", {"bl": [5, 6, 7, 8], "pt": False, "fr": True, "co": ["white"]}),
    ("Rain Lily", "Zephyranthes spp.", "bulb", {"bl": [6, 7, 8, 9], "d": "very_easy", "co": ["pink", "white", "yellow"]}),
    ("Kaffir Lily", "Clivia miniata", "bulb", {"bl": [3, 4, 5], "pt": False, "su": "part", "sm": 3, "indoor": True, "co": ["orange", "red"]}),
    ("Dutch Iris", "Iris x hollandica", "bulb", {"bl": [2, 3], "pt": False, "co": ["blue", "purple", "white", "yellow"]}),
    ("Bearded Iris", "Iris germanica", "bulb", {"bl": [3, 4], "pt": False, "co": ["purple", "blue", "yellow", "white"]}),
    ("Crocosmia", "Crocosmia x crocosmiiflora", "bulb", {"bl": [6, 7, 8], "co": ["orange", "red"]}),
    ("Alstroemeria", "Alstroemeria hybrids", "bulb", {"bl": [3, 4, 5, 6], "pt": False, "co": ["pink", "yellow", "red", "white", "purple"]}),
    ("Oxalis", "Oxalis triangularis", "bulb", {"bl": [3, 4, 5, 10, 11], "pt": False, "su": "part", "sm": 3, "indoor": True, "co": ["pink", "white"]}),
    ("Tigridia", "Tigridia pavonia", "bulb", {"bl": [6, 7, 8], "pt": False, "co": ["red", "yellow", "pink"]}),
    ("African Lily", "Agapanthus praecox", "bulb", {"bl": [6, 7, 8], "co": ["blue", "white"]}),
    # -------------------------------------------------------------- fragrant --
    ("Arabian Jasmine (Mogra)", "Jasminum sambac", "fragrant", {"ln": "Mogra / Bela", "co": ["white"]}),
    ("Common Jasmine", "Jasminum officinale", "fragrant", {"ln": "Chambeli", "bl": [4, 5, 6], "co": ["white"]}),
    ("Spanish Jasmine", "Jasminum grandiflorum", "fragrant", {"bl": [4, 5, 6, 7], "co": ["white", "pink"]}),
    ("Winter Jasmine", "Jasminum nudiflorum", "fragrant", {"bl": [1, 2], "fo": "medium", "co": ["yellow"]}),
    ("Star Jasmine", "Trachelospermum jasminoides", "fragrant", {"bl": [4, 5, 6], "su": "part", "sm": 4, "co": ["white"]}),
    ("Rangoon Creeper", "Combretum indicum", "fragrant", {"bl": [6, 7, 8, 9, 10], "ln": "Madhu Malti", "co": ["red", "pink", "white"]}),
    ("Honeysuckle", "Lonicera japonica", "fragrant", {"bl": [3, 4, 5], "co": ["white", "yellow"]}),
    ("Cape Honeysuckle", "Tecomaria capensis", "fragrant", {"bl": [10, 11, 12, 1, 2], "fr": False, "sa": True, "co": ["orange"]}),
    ("Passion Flower", "Passiflora caerulea", "fragrant", {"fr": False, "bl": [5, 6, 7, 8, 9], "co": ["blue", "purple"]}),
    ("Butterfly Pea", "Clitoria ternatea", "fragrant", {"bl": [6, 7, 8, 9, 10], "ht": "very_high", "fr": False, "co": ["blue"]}),
    ("Garlic Vine", "Mansoa alliacea", "fragrant", {"bl": [3, 4, 9, 10], "co": ["purple"]}),
    ("Petrea", "Petrea volubilis", "fragrant", {"bl": [3, 4, 5, 6], "fr": False, "co": ["purple"]}),
    ("Golden Shower Vine", "Pyrostegia venusta", "fragrant", {"bl": [12, 1, 2, 3], "fr": False, "co": ["orange"]}),
    ("Bleeding Heart Vine", "Clerodendrum thomsoniae", "fragrant", {"bl": [3, 4, 5, 9, 10], "fr": False, "co": ["red", "white"]}),
    ("Coral Vine", "Antigonon leptopus", "fragrant", {"bl": [7, 8, 9, 10], "w": "low", "ht": "very_high", "sa": True, "fr": False, "co": ["pink"]}),
    ("Cypress Vine", "Ipomoea quamoclit", "fragrant", {"bl": [6, 7, 8, 9], "pt": False, "fr": False, "co": ["red"]}),
    ("Moonflower", "Ipomoea alba", "fragrant", {"bl": [7, 8, 9, 10], "pt": False, "co": ["white"]}),
    ("Hyacinth Bean", "Lablab purpureus", "fragrant", {"bl": [7, 8, 9, 10], "fr": False, "co": ["purple"]}),
    ("Black-eyed Susan Vine", "Thunbergia alata", "fragrant", {"bl": [6, 7, 8, 9, 10], "fr": False, "co": ["orange", "yellow"]}),
    ("Bengal Clock Vine", "Thunbergia grandiflora", "fragrant", {"bl": [7, 8, 9, 10, 11], "fr": False, "co": ["blue", "purple"]}),
    ("Mandevilla", "Mandevilla sanderi", "fragrant", {"bl": [4, 5, 6, 9, 10], "fo": "low", "co": ["pink", "red", "white"]}),
    ("Rangoon Jasmine", "Jasminum multiflorum", "fragrant", {"bl": [11, 12, 1, 2, 3], "ln": "Kund", "co": ["white"]}),
    ("Morning Glory", "Ipomoea purpurea", "fragrant", {"bl": [6, 7, 8, 9], "pt": False, "fr": False, "co": ["purple", "pink", "blue", "white"]}),
    ("Wisteria", "Wisteria sinensis", "fragrant", {"bl": [3, 4], "d": "medium", "fo": "medium", "fr": True, "co": ["purple", "white"], "ct": "Best in Islamabad, Murree and other cool spots - it sulks in the hot plains. Needs a strong pergola and years of patience."}),
    # ------------------------------------------------------------------ palm --
    ("Areca Palm", "Dypsis lutescens", "palm", {"indoor": True, "co": ["yellow"]}),
    ("Date Palm", "Phoenix dactylifera", "palm", {"pot": False, "ct": "A farm tree, not a pot plant - it wants deep ground and decades of blazing sun."}),
    ("Canary Island Date Palm", "Phoenix canariensis", "palm", {"pot": False, "fo": "medium"}),
    ("Pygmy Date Palm", "Phoenix roebelenii", "palm", {"indoor": True}),
    ("Washingtonia Palm", "Washingtonia robusta", "palm", {"pot": False, "fo": "medium"}),
    ("Lady Palm", "Rhapis excelsa", "palm", {"indoor": True}),
    ("Parlor Palm", "Chamaedorea elegans", "palm", {"indoor": True}),
    ("Kentia Palm", "Howea forsteriana", "palm", {"indoor": True}),
    ("Queen Palm", "Syagrus romanzoffiana", "palm", {"pot": False}),
    ("Fan Palm", "Livistona chinensis", "palm", {"pot": False}),
    ("Bottle Palm", "Hyophorbe lagenicaulis", "palm", {"pot": False, "fo": "low"}),
    ("Sago Palm", "Cycas revoluta", "palm", {"pt": False, "su": "part", "sm": 4, "fo": "medium"}),
    ("Traveler's Palm", "Ravenala madagascariensis", "palm", {"pot": False}),
    ("Giant Bird of Paradise", "Strelitzia nicolai", "palm", {"bl": [6, 7, 8], "pot": False, "ht": "high", "co": ["white", "blue"]}),
    # ---------------------------------------------------------------- indoor --
    ("Spider Plant", "Chlorophytum comosum", "indoor", {"d": "very_easy", "su": "shade", "w": "low"}),
    ("Peace Lily", "Spathiphyllum wallisii", "indoor", {"w": "high", "su": "shade", "d": "very_easy", "pt": False}),
    ("Boston Fern", "Nephrolepis exaltata", "indoor", {"w": "high", "su": "part", "sm": 3}),
    ("Maidenhair Fern", "Adiantum raddianum", "indoor", {"w": "high", "su": "part", "sm": 3, "d": "hard"}),
    ("Bird's Nest Fern", "Asplenium nidus", "indoor", {"w": "high", "su": "part", "sm": 3}),
    ("Chinese Evergreen", "Aglaonema commutatum", "indoor", {"pt": False, "su": "shade", "d": "very_easy"}),
    ("Dieffenbachia", "Dieffenbachia seguine", "indoor", {"pt": False, "su": "shade"}),
    ("Philodendron", "Philodendron hederaceum", "indoor", {"pt": False, "su": "part", "sm": 3, "d": "very_easy"}),
    ("Monstera", "Monstera deliciosa", "indoor", {"pt": False, "su": "part", "sm": 3, "d": "very_easy"}),
    ("Swiss Cheese Vine", "Monstera adansonii", "indoor", {"pt": False, "su": "part", "sm": 3}),
    ("Syngonium", "Syngonium podophyllum", "indoor", {"pt": False, "su": "part", "sm": 3, "d": "very_easy"}),
    ("Calathea", "Goeppertia orbifolia", "indoor", {"w": "high", "su": "part", "sm": 3, "d": "medium"}),
    ("Prayer Plant", "Maranta leuconeura", "indoor", {"su": "part", "sm": 3}),
    ("Dracaena (Corn Plant)", "Dracaena fragrans", "indoor", {"pt": False, "su": "shade", "d": "very_easy"}),
    ("Dragon Tree", "Dracaena marginata", "indoor", {"pt": False, "su": "part", "sm": 3}),
    ("Cast Iron Plant", "Aspidistra elatior", "indoor", {"su": "shade", "w": "low", "d": "very_easy"}),
    ("Chinese Money Plant", "Pilea peperomioides", "indoor", {"su": "part", "sm": 3}),
    ("Nerve Plant", "Fittonia albivenis", "indoor", {"w": "high", "su": "part", "sm": 3, "d": "medium"}),
    ("Baby Rubber Plant", "Peperomia obtusifolia", "indoor", {"w": "low", "su": "part", "sm": 3, "d": "very_easy"}),
    ("Watermelon Peperomia", "Peperomia argyreia", "indoor", {"su": "part", "sm": 3}),
    ("Polka Dot Plant", "Hypoestes phyllostachya", "indoor", {"pt": False, "su": "part", "sm": 3}),
    ("Croton", "Codiaeum variegatum", "indoor", {"pt": False, "su": "part", "sm": 4, "d": "medium"}),
    ("Ti Plant", "Cordyline fruticosa", "indoor", {"pt": False, "su": "part", "sm": 3}),
    ("Snake Plant", "Dracaena trifasciata", "indoor", {"pt": False, "w": "low", "su": "shade", "d": "very_easy"}),
    # ---------------------------------------------------------------- cactus --
    ("Echinopsis", "Echinopsis spp.", "cactus", {"bl": [5, 6], "co": ["pink", "white", "yellow"]}),
    ("Mammillaria", "Mammillaria spp.", "cactus", {"bl": [3, 4, 5], "co": ["pink", "white", "yellow", "red"]}),
    ("Gymnocalycium", "Gymnocalycium spp.", "cactus", {"bl": [5, 6, 7], "co": ["pink", "white"]}),
    ("Rebutia", "Rebutia spp.", "cactus", {"bl": [4, 5], "co": ["red", "orange", "yellow"]}),
    ("Parodia", "Parodia spp.", "cactus", {"bl": [3, 4, 5], "co": ["yellow", "orange", "red"]}),
    ("Ferocactus", "Ferocactus spp.", "cactus", {"bl": [6, 7], "indoor": False, "co": ["yellow", "red"]}),
    ("Astrophytum", "Astrophytum spp.", "cactus", {"bl": [5, 6, 7], "co": ["yellow"]}),
    ("Opuntia", "Opuntia spp.", "cactus", {"bl": [4, 5, 6], "indoor": False, "co": ["yellow", "orange", "pink"]}),
    ("Peruvian Apple Cactus", "Cereus repandus", "cactus", {"bl": [5, 6, 7], "indoor": False, "co": ["white"]}),
    ("Totem Pole Cactus", "Pachycereus schottii monstrose", "cactus", {"bl": [], "indoor": False}),
    ("Columnar Cactus", "Cereus spp.", "cactus", {"bl": [5, 6], "indoor": False, "co": ["white"]}),
    ("Golden Barrel Cactus", "Echinocactus grusonii", "cactus", {"bl": [6, 7], "indoor": False, "co": ["yellow"]}),
    ("Old Man Cactus", "Cephalocereus senilis", "cactus", {"bl": [], "indoor": False}),
    ("Moon Cactus", "Gymnocalycium mihanovichii", "cactus", {"bl": [5, 6, 7], "co": ["pink", "red", "yellow"]}),
    ("Easter Cactus", "Hatiora gaertneri", "cactus", {"bl": [3, 4], "su": "part", "sm": 3, "w": "low", "co": ["red", "pink"]}),
    ("Christmas Cactus", "Schlumbergera truncata", "cactus", {"bl": [11, 12], "su": "part", "sm": 3, "co": ["red", "pink", "white"], "ct": "Blooms best in a bright spot that cools down at night - water only when the top of the mix dries."}),
    ("Rat Tail Cactus", "Aporocactus flagelliformis", "cactus", {"bl": [4, 5], "co": ["pink", "red"]}),
    ("Peanut Cactus", "Echinopsis chamaecereus", "cactus", {"bl": [5, 6], "co": ["orange", "red"]}),
    ("Bishop's Cap", "Astrophytum myriostigma", "cactus", {"bl": [5, 6, 7], "co": ["yellow"]}),
    ("Star Cactus", "Astrophytum asterias", "cactus", {"bl": [6, 7, 8], "co": ["yellow"]}),
    ("Fairy Castle Cactus", "Acanthocereus tetragonus", "cactus", {"bl": [], "indoor": False}),
    ("Ladyfinger Cactus", "Mammillaria elongata", "cactus", {"bl": [3, 4, 5], "co": ["yellow", "white"]}),
    ("Thimble Cactus", "Mammillaria vetula", "cactus", {"bl": [3, 4], "co": ["yellow", "white"]}),
    ("Fishbone Cactus", "Disocactus anguliger", "cactus", {"bl": [9, 10], "su": "part", "sm": 3, "w": "medium"}),
    ("Orchid Cactus", "Epiphyllum hybrids", "cactus", {"bl": [4, 5, 6], "su": "part", "sm": 3, "w": "medium", "co": ["white", "pink", "red"]}),
    # ------------------------------------------------------------- succulent --
    ("Jade Plant", "Crassula ovata", "succulent", {"pt": False, "bl": [12, 1], "w": "low", "co": ["white", "pink"]}),
    ("Haworthia Zebra", "Haworthiopsis attenuata", "succulent", {"su": "part", "sm": 3, "co": ["white"]}),
    ("Gasteria", "Gasteria spp.", "succulent", {"su": "part", "sm": 3}),
    ("Echeveria", "Echeveria spp.", "succulent", {"sm": 5, "co": ["pink", "yellow", "red"]}),
    ("Black Prince Echeveria", "Echeveria hybrid", "succulent", {"sm": 5, "co": ["red"]}),
    ("Aeonium", "Aeonium spp.", "succulent", {"su": "part", "sm": 4, "co": ["yellow"]}),
    ("Sedum", "Sedum spp.", "succulent", {"co": ["yellow", "pink", "white"]}),
    ("Jelly Bean Plant", "Sedum rubrotinctum", "succulent", {"co": ["yellow"]}),
    ("String of Pearls", "Curio rowleyanus", "succulent", {"pt": False, "su": "part", "sm": 4, "w": "very_low"}),
    ("String of Bananas", "Curio radicans", "succulent", {"pt": False, "su": "part", "sm": 4, "w": "very_low"}),
    ("String of Hearts", "Ceropegia woodii", "succulent", {"su": "part", "sm": 4, "bl": [7, 8, 9], "co": ["pink", "purple"]}),
    ("Kalanchoe", "Kalanchoe blossfeldiana", "succulent", {"pt": False, "bl": [12, 1, 2, 3], "co": ["red", "pink", "yellow", "orange"]}),
    ("Paddle Plant", "Kalanchoe luciae", "succulent", {"pt": False, "bl": [3, 4], "co": ["yellow"]}),
    ("Burro's Tail", "Sedum morganianum", "succulent", {"su": "part", "sm": 4, "co": ["pink", "red"]}),
    ("Panda Plant", "Kalanchoe tomentosa", "succulent", {"pt": False}),
    ("Lithops", "Lithops spp.", "succulent", {"bl": [9, 10, 11], "sm": 6, "co": ["yellow", "white"], "ct": "Water only in autumn and spring - a resting lithops given summer water simply splits and dies."}),
    ("Tiger Jaws", "Faucaria tigrina", "succulent", {"bl": [9, 10, 11], "co": ["yellow"]}),
    ("Elephant Bush", "Portulacaria afra", "succulent", {"w": "low", "bl": [4, 5], "co": ["pink"]}),
    ("Pencil Euphorbia", "Euphorbia tirucalli", "succulent", {"pt": False, "bl": []}),
    ("Dwarf Crown of Thorns", "Euphorbia milii", "succulent", {"pt": False, "bl": [3, 4, 5, 6, 7, 8, 9, 10], "co": ["red", "pink", "yellow"]}),
    ("Adenium (Desert Rose)", "Adenium obesum", "succulent", {"pt": False, "w": "low", "ht": "very_high", "sa": True, "d": "easy", "bl": [4, 5, 6, 7, 8, 9], "co": ["pink", "red", "white"], "ct": "A rooftop star - loves blazing sun and hates wet feet. Let it dry out completely between waterings."}),
    ("Pachypodium", "Pachypodium lamerei", "succulent", {"pt": False, "bl": [6, 7], "co": ["white"]}),
    ("Agave", "Agave americana", "succulent", {"w": "very_low", "sm": 6, "ht": "very_high", "sa": True, "indoor": False, "bl": [], "d": "very_easy"}),
    ("Blue Agave", "Agave tequilana", "succulent", {"sa": True, "indoor": False, "bl": []}),
    ("Sempervivum", "Sempervivum spp.", "succulent", {"fo": "medium", "bl": [6, 7]}),
    # ------------------------------------------------------------------ tree --
    ("Gulmohar", "Delonix regia", "tree", {"ht": "very_high", "bl": [5, 6], "co": ["red", "orange"]}),
    ("Jacaranda", "Jacaranda mimosifolia", "tree", {"bl": [4, 5], "co": ["purple"]}),
    ("Amaltas", "Cassia fistula", "tree", {"nv": True, "bl": [5, 6], "co": ["yellow"]}),
    ("Kachnar", "Bauhinia variegata", "tree", {"nv": True, "bl": [3, 4], "co": ["pink", "purple", "white"]}),
    ("Pink Trumpet Tree", "Tabebuia rosea", "tree", {"bl": [3, 4], "co": ["pink"]}),
    ("Yellow Trumpet Tree", "Handroanthus chrysotrichus", "tree", {"bl": [3, 4], "co": ["yellow"]}),
    ("Copperpod", "Peltophorum pterocarpum", "tree", {"bl": [4, 5], "co": ["yellow"]}),
    ("Pride of India", "Lagerstroemia speciosa", "tree", {"bl": [5, 6, 7], "co": ["pink", "purple"]}),
    ("Crape Myrtle", "Lagerstroemia indica", "tree", {"bl": [6, 7, 8, 9], "co": ["pink", "red", "white"]}),
    ("Champa", "Magnolia champaca", "tree", {"nv": True, "bl": [6, 7, 8, 9], "fr": True, "co": ["yellow", "orange"]}),
    ("Frangipani", "Plumeria rubra", "tree", {"w": "low", "ht": "very_high", "fo": "low", "fr": True, "pot": True, "bl": [5, 6, 7, 8, 9, 10], "co": ["pink", "white", "yellow", "red"]}),
    ("Neem", "Azadirachta indica", "tree", {"nv": True, "w": "low", "ht": "very_high", "sa": True, "fr": True, "bl": [3, 4], "co": ["white", "yellow"]}),
    ("Siris", "Albizia lebbeck", "tree", {"nv": True, "bl": [5, 6], "co": ["white", "yellow"]}),
    ("Rain Tree", "Samanea saman", "tree", {"bl": [6, 7, 8], "co": ["pink", "white"]}),
    ("Sukh Chain", "Pongamia pinnata", "tree", {"nv": True, "w": "low", "bl": [4, 5], "co": ["purple", "white"]}),
    ("Arjun Tree", "Terminalia arjuna", "tree", {"nv": True, "w": "low", "bl": [4, 5], "co": ["yellow", "white"]}),
    ("Pilkhan", "Ficus virens", "tree", {"nv": True, "bl": [], "po": False}),
    ("Banyan", "Ficus benghalensis", "tree", {"nv": True, "ln": "Bargad", "bl": [], "po": False}),
    ("Peepal", "Ficus religiosa", "tree", {"nv": True, "bl": [], "po": False}),
    # ----------------------------------------------------------------- fruit --
    ("Guava (Amrood)", "Psidium guajava", "fruit", {"ln": "Amrood", "bl": [3, 4, 5], "ht": "high", "pot": True, "sa": True}),
    ("Pomegranate (Anaar)", "Punica granatum", "fruit", {"ln": "Anaar", "bl": [4, 5], "w": "low", "ht": "very_high", "pot": True, "sa": True, "co": ["red", "orange"]}),
    ("Fig (Anjeer)", "Ficus carica", "fruit", {"ln": "Anjeer", "w": "low", "bl": [], "pot": True, "d": "easy"}),
    ("Mulberry (Shahtoot)", "Morus alba", "fruit", {"ln": "Shahtoot", "bl": [], "po": False, "d": "easy"}),
    ("Papaya", "Carica papaya", "fruit", {"bl": [3, 4, 5, 6, 7, 8], "ht": "very_high", "d": "easy", "co": ["white", "yellow"]}),
    ("Mango (Aam)", "Mangifera indica", "fruit", {"ln": "Aam", "ht": "very_high", "bl": [2, 3, 4], "co": ["white", "yellow"]}),
    ("Orange (Santra)", "Citrus sinensis", "fruit", {"ln": "Santra", "bl": [3, 4], "fr": True, "pot": True, "ht": "high", "co": ["white"]}),
    ("Kinnow", "Citrus reticulata", "fruit", {"bl": [3, 4], "fr": True, "pot": True, "ht": "high", "co": ["white"]}),
    ("Grapefruit", "Citrus x paradisi", "fruit", {"bl": [3, 4], "fr": True, "pot": True, "ht": "high", "co": ["white", "pink"]}),
    ("Sweet Lime (Mosambi)", "Citrus limetta", "fruit", {"ln": "Mosambi", "bl": [3, 4], "fr": True, "pot": True, "ht": "high", "co": ["white"]}),
    ("Grapevine (Angoor)", "Vitis vinifera", "fruit", {"ln": "Angoor", "bl": [3, 4], "pt": False, "pot": True}),
    ("Peach (Aroo)", "Prunus persica", "fruit", {"ln": "Aroo", "bl": [2, 3], "pt": False, "fo": "high", "co": ["pink"]}),
    ("Plum (Aloo Bukhara)", "Prunus domestica", "fruit", {"ln": "Aloo Bukhara", "bl": [3, 4], "pt": False, "fo": "high", "co": ["white"]}),
    ("Apricot (Khubani)", "Prunus armeniaca", "fruit", {"ln": "Khubani", "bl": [2, 3, 4], "pt": False, "fo": "high", "co": ["white", "pink"]}),
    ("Apple (Seb)", "Malus domestica", "fruit", {"ln": "Seb", "bl": [3, 4], "fo": "high", "co": ["white", "pink"]}),
    ("Pear (Nashpati)", "Pyrus communis", "fruit", {"ln": "Nashpati", "bl": [3, 4], "fo": "high", "co": ["white"]}),
    ("Loquat (Lokat)", "Eriobotrya japonica", "fruit", {"ln": "Lokat", "bl": [11, 12], "fr": True, "co": ["white"]}),
    ("Lychee (Litchi)", "Litchi chinensis", "fruit", {"ln": "Litchi", "bl": [2, 3, 4], "ht": "high"}),
    ("Persimmon", "Diospyros kaki", "fruit", {"bl": [4, 5], "fo": "medium"}),
    ("Almond (Badam)", "Prunus dulcis", "fruit", {"ln": "Badam", "bl": [2, 3], "pt": False, "fo": "high", "co": ["white", "pink"]}),
    ("Walnut (Akhrot)", "Juglans regia", "fruit", {"ln": "Akhrot", "bl": [3, 4], "fo": "high"}),
    ("Ber (Jujube)", "Ziziphus mauritiana", "fruit", {"ln": "Ber", "bl": [8, 9, 10], "w": "low", "ht": "very_high", "d": "very_easy", "pot": True, "sa": True, "co": ["yellow", "white"]}),
    ("Tamarind (Imli)", "Tamarindus indica", "fruit", {"ln": "Imli", "bl": [4, 5], "w": "low", "ht": "very_high", "sa": True, "d": "easy", "co": ["red", "yellow"]}),
    # ---------------------------------------------------------------- native --
    ("Desert Marigold", "Pulicaria spp.", "native", {"bl": [2, 3, 4], "w": "low", "co": ["yellow"]}),
    ("Indian Mallow", "Abutilon indicum", "native", {"bl": [7, 8, 9, 10], "co": ["yellow", "orange"]}),
    ("Butterfly Bush", "Buddleja asiatica", "native", {"bl": [1, 2, 3], "fr": True, "ht": "medium", "co": ["white"]}),
    ("Indian Senna", "Senna alexandrina", "native", {"bl": [9, 10, 11], "pt": False, "co": ["yellow"]}),
    ("Cassia", "Senna siamea", "native", {"nv": False, "bl": [6, 7, 8], "ht": "very_high", "w": "low", "pot": False, "co": ["yellow"]}),
    ("Karonda", "Carissa carandas", "native", {"bl": [3, 4, 5], "w": "low", "ht": "high", "co": ["white", "pink"]}),
    ("Henna (Mehndi)", "Lawsonia inermis", "native", {"ln": "Mehndi", "bl": [6, 7, 8], "fr": True, "ht": "very_high", "w": "low", "co": ["white", "pink"], "ct": "Pick a sunny rooftop spot - henna turns into a fragrant little tree after a few cuts of 'mehndi' leaves."}),
    ("Murraya (Kamini)", "Murraya paniculata", "native", {"ln": "Kamini", "bl": [4, 5, 6, 7], "fr": True, "pt": False, "co": ["white"]}),
    ("Arabian Lilac", "Vitex negundo", "native", {"bl": [5, 6, 7], "w": "low", "co": ["purple", "blue"]}),
]


def slugify(name):
    slug = re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-")
    return re.sub(r"-+", "-", slug)


def build():
    flowers = []
    seen_slugs = set()
    seen_names = set()
    for name, sci, group, over in PLANTS:
        assert group in GROUPS, "unknown group %r for %s" % (group, name)
        assert name not in seen_names, "duplicate plant name %r" % name
        seen_names.add(name)
        entry = dict(DEFAULTS[group])
        for key, value in over.items():
            assert key in OV, "unknown override %r on %s" % (key, name)
            entry[OV[key]] = value

        slug = slugify(name)
        if slug in seen_slugs:
            slug = slug + "-" + slugify(sci.split()[0])
        seen_slugs.add(slug)

        item = {
            "slug": slug,
            "name": name,
            "scientific": sci,
            "group": group,
        }
        if entry.get("local_name"):
            item["local_name"] = entry["local_name"]
        if entry.get("colors"):
            item["colors"] = entry["colors"]
        item.update({
            "water": entry["water"],
            "sun_hours_min": entry["sun_hours_min"],
            "sun": entry["sun"],
            "difficulty": entry["difficulty"],
            "bloom_months": sorted(set(entry["bloom_months"])),
            "sow_months": sorted(set(entry["sow_months"])),
            "fragrant": entry["fragrant"],
            "pollinator": entry["pollinator"],
            "pet_safe": entry["pet_safe"],
            "native": entry["native"],
            "container": entry["pot"],
            "indoor": entry["indoor"],
            "balcony": entry["balcony"],
            "rooftop": entry["rooftop"],
            "ground": entry["ground"],
            "heat_tolerance": entry["heat"],
            "frost_tolerance": entry["frost"],
            "salt_tolerant": entry["salt"],
        })
        if entry.get("care"):
            item["care"] = entry["care"]
        flowers.append(item)

    # sanity checks
    assert len(flowers) >= 250, "catalog too small: %d" % len(flowers)
    for f in flowers:
        for m in f["bloom_months"] + f["sow_months"]:
            assert 1 <= m <= 12, "bad month %d on %s" % (m, f["name"])
        assert f["water"] in ("very_low", "low", "medium", "high"), f["name"]
        assert f["difficulty"] in ("very_easy", "easy", "medium", "hard"), f["name"]
        assert f["heat_tolerance"] in ("low", "medium", "high", "very_high"), f["name"]
        assert f["frost_tolerance"] in ("low", "medium", "high"), f["name"]
        assert f["sun"] in ("full", "part", "shade"), f["name"]

    groups_out = {}
    for gid, g in GROUPS.items():
        count = sum(1 for f in flowers if f["group"] == gid)
        groups_out[gid] = dict(g, count=count)
        assert count > 0, "empty group %s" % gid

    payload = {
        "note": "Hamara Bagh ornamental catalog. Bloom and sowing windows are typical for the Pakistan plains and shift a few weeks in the north.",
        "generated_by": "scripts/build_flowers_json.py",
        "groups": groups_out,
        "flowers": flowers,
    }
    with open(OUT_PATH, "w", encoding="utf-8") as fh:
        json.dump(payload, fh, ensure_ascii=False, indent=2)
        fh.write("\n")

    print("wrote", os.path.abspath(OUT_PATH))
    print("total flowers:", len(flowers))
    for gid, g in groups_out.items():
        print("  %-10s %3d  %s" % (gid, g["count"], g["label"]))


if __name__ == "__main__":
    build()
