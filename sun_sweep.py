# sun_sweep.py
pos = float(data.get("position",0.0))
severity = float(data.get("severity",1.0))
transition_fast = 6
transition_slow = 20

# --- Entity IDs ----------------------------------------------------------
row1_tw = ["light.slope_spot", "light.music_corner"]
row2_rgb = ["light.towards_slope", "light.foot_stool"]
row3_rgb = ["light.burner", "light.axel"]
row4_tw = ["light.reading_light", "light.music_stand"]
row5_tw = ["light.breakfast_bar"]
row6_atrium_tw = ["light.table_uplight_white", "light.table_downlight_white"]
row6_atrium_rgb = ["light.table_uplight_colour", "light.table_downlight_colour"]


# --- Row Config (slightly widened) ---------------------------------------
row_config = {
    "row1_tw": {"center":30, "width":20, "max":85},
    "row2_rgb":{"center":40, "width":26, "max":90},
    "row3_rgb":{"center":50, "width":28, "max":95},
    "row4_tw":{"center":60, "width":30, "max":90},
    "row5_tw":{"center":70, "width":32, "max":100},
    "row6_atrium":{"center":85, "width":34, "max":100},
}

# --- Helpers -------------------------------------------------------------
def clamp(v,a,b): return max(a,min(b,v))
def lerp(a,b,t): return a+(b-a)*t

# Softer bell for wider sweep
def bell(x,c,w):
    dx=(x-c)/w
    return max(0, 1 - (dx*dx / (severity*0.85)))   # softer → wider

# Kelvin curved for sunrise/midday/sunset
def tw_kelvin(pos):
    if pos < 50:
        t = pos/50.0
        k = lerp(2200, 5600, t)
    else:
        t = (pos-50)/50.0
        k = lerp(5600, 2200, t)

    # Extra orange in last 15%
    if pos > 85:
        t2 = (pos-85)/15.0
        k -= 650 * t2   # stronger

    return int(clamp(k, 1800, 5600))

def safe_rgb(c, fallback=(255,180,120)):
    return c if c is not None else fallback

# --- CINEMATIC SUNSET RGB CURVES (NEW, MUCH MORE VIBRANT) -------------

def atrium_uplight_sunset(pos):
    if pos <= 85: return None
    t = (pos-85)/15.0

    # Start deep orange → molten amber → pink → red → purple
    return (
        int(lerp(255, 140, t)),     # red: fades down slightly
        int(lerp(120, 20, t)),      # green: collapses, gives warmth → magenta
        int(lerp(30, 140, t))       # blue: rises → purple
    )

def atrium_downlight_sunset(pos):
    if pos <= 85: return None
    t = (pos-85)/15.0

    # A brighter version with golden core early stage
    return (
        int(lerp(255, 180, t)),     # red
        int(lerp(180, 30, t)),      # green
        int(lerp(40, 160, t))       # blue
    )

# Daylight RGB for non-atrium rows
def atrium_default_rgb(pos):
    k = tw_kelvin(pos)
    if k > 5000:
        return (180, 205, 255)
    if k > 3500:
        return (255, 235, 205)
    return (255, 200, 150)

# --- Sunset white fade in atrium (FIXED TO 1 > 0) ------------------------
if pos <= 85:
    tw_factor = 1.0
else:
    tw_factor = max(0.0, 1 - ((pos - 85) / 15.0))  # 85→100 now fades perfectly

# --- Calculate the row bell intensities ---------------------------------
for k in row_config:
    row_config[k]["width"] *= severity

row_pct = {
    r: clamp(int(bell(pos,cfg["center"],cfg["width"])*cfg["max"]),0,100)
    for r,cfg in row_config.items()
}

# --- Apply TW rows -------------------------------------------------------
for ent in row1_tw:
    hass.services.call("light","turn_on",{
        "entity_id": ent,
        "brightness_pct": row_pct["row1_tw"],
        "color_temp_kelvin": tw_kelvin(pos),
        "transition": transition_fast
    })

for ent in row4_tw:
    hass.services.call("light","turn_on",{
        "entity_id": ent,
        "brightness_pct": row_pct["row4_tw"],
        "color_temp_kelvin": tw_kelvin(pos),
        "transition": transition_fast
    })

for ent in row5_tw:
    hass.services.call("light","turn_on",{
        "entity_id": ent,
        "brightness_pct": row_pct["row5_tw"],
        "color_temp_kelvin": tw_kelvin(pos),
        "transition": transition_fast
    })

# Atrium TW
for ent in row6_atrium_tw:
    hass.services.call("light","turn_on",{
        "entity_id": ent,
        "brightness_pct": int(row_pct["row6_atrium"] * tw_factor), # apply the reduction
        "color_temp_kelvin": tw_kelvin(pos),
        "transition": transition_slow
    })

# --- Apply RGB rows ------------------------------------------------------
# Row 2 + 3
for ent in row2_rgb:
    hass.services.call("light","turn_on",{
        "entity_id": ent,
        "brightness_pct": row_pct["row2_rgb"],
        "rgb_color": atrium_default_rgb(pos),
        "transition": transition_fast
    })

for ent in row3_rgb:
    hass.services.call("light","turn_on",{
        "entity_id": ent,
        "brightness_pct": row_pct["row3_rgb"],
        "rgb_color": atrium_default_rgb(pos),
        "transition": transition_fast
    })

# Atrium RGB (cinematic sunset)
up_rgb = atrium_uplight_sunset(pos) or atrium_default_rgb(pos)
down_rgb = atrium_downlight_sunset(pos) or atrium_default_rgb(pos)

hass.services.call("light","turn_on",{
    "entity_id": row6_atrium_rgb[0],
    "rgb_color": safe_rgb(up_rgb),
    "brightness_pct": row_pct["row6_atrium"],
    "transition": transition_slow
})

hass.services.call("light","turn_on",{
    "entity_id": row6_atrium_rgb[1],
    "rgb_color": safe_rgb(down_rgb),
    "brightness_pct": int(clamp(row_pct["row6_atrium"]*0.9,0,100)),
    "transition": transition_slow
})

# --- Debug ---------------------------------------------------------------
debug = (
    f"pos={pos:.1f} sev={severity:.2f} | "
    f"r1={row_pct['row1_tw']} r2={row_pct['row2_rgb']} "
    f"r3={row_pct['row3_rgb']} r4={row_pct['row4_tw']} "
    f"r5={row_pct['row5_tw']} r6={row_pct['row6_atrium']} | "
    f"kelvin={tw_kelvin(pos)} tw_factor={tw_factor:.2f}"
)
hass.states.set("input_text.sun_debugger", debug)
