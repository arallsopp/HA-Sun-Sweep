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


# --- Row Config ----------------------------------------------------------
# trying wider versions
row_config = {
    "row1_tw": {"center":30, "width":20, "max":85},
    "row2_rgb":{"center":40, "width":22, "max":85},
    "row3_rgb":{"center":50, "width":24, "max":90},
    "row4_tw":{"center":60, "width":28, "max":85},
    "row5_tw":{"center":70, "width":30, "max":95},
    "row6_atrium":{"center":85, "width":32, "max":100},
}

# --- Helpers -------------------------------------------------------------
def clamp(v,a,b): return max(a,min(b,v))
def lerp(a,b,t): return a+(b-a)*t
def bell(x,c,w):
    dx=(x-c)/w
    return max(0,1-dx*dx)

# corrected tw_kelvin for soft warm mornings, cool midday, warm evenings.
def tw_kelvin(pos):
    # Sunrise → Midday → Sunset curve
    if pos < 50:
        # 2200 → 5500
        t = pos/50.0
        kelvin = int(lerp(2200, 5500, t))
    else:
        # 5500 → 2200
        t = (pos-50)/50.0
        kelvin = int(lerp(5500, 2200, t))

    # Extra orange in last 15%
    if pos > 85:
        t2 = (pos-85)/15.0
        kelvin -= int(500 * t2)

    return clamp(kelvin, 1800, 5500)

def safe_rgb(c, fallback=(255,200,150)):
    # Ensures rgb_color never receives None
    return c if c is not None else fallback

# Atrium cinematic sunset
def atrium_uplight_sunset(pos):
    if pos <= 85: return None
    t=(pos-85)/15.0
    if t <= 0.5:
        t2=t/0.5
        return (255, lerp(140,80,t2), lerp(40,50,t2))
    else:
        t2=(t-0.5)/0.5
        return (lerp(255,120,t2), lerp(80,40,t2), lerp(50,150,t2))

def atrium_downlight_sunset(pos):
    if pos <= 85: return None
    t=(pos-85)/15.0
    if t <= 0.5:
        t2=t/0.5
        return (255, lerp(200,80,t2), lerp(100,40,t2))
    else:
        t2=(t-0.5)/0.5
        return (lerp(255,200,t2), lerp(80,20,t2), lerp(40,150,t2))

# Fallback for atrium RGB when pos ≤ 85
def atrium_default_rgb(pos):
    k = tw_kelvin(pos)
    if k >= 5000: return (180,200,255)
    elif k >= 3500: return (255,235,200)
    else: return (255,200,150)

# --- Calculate Row envelopes -------------------------------------------------------
for k in row_config:
    row_config[k]["width"] = row_config[k]["width"] * severity

row_pct = { r: clamp(int(bell(pos,cfg["center"],cfg["width"])*cfg["max"]),0,100)
            for r,cfg in row_config.items() }

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
sunset_zone = pos > 85 # sunset zone will drop the white brightness
tw_factor = 0.2 if sunset_zone else 0.9 #reduce brightness for sunset.

for ent in row6_atrium_tw:
    hass.services.call("light","turn_on",{
        "entity_id": ent,
        "brightness_pct": int(row_pct["row6_atrium"]*0.9),
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
    f"pos={pos:.1f}, sev={severity:.2f} | "
    f"r1={row_pct['row1_tw']}%, "
    f"r2={row_pct['row2_rgb']}%, "
    f"r3={row_pct['row3_rgb']}%, "
    f"r4={row_pct['row4_tw']}%, "
    f"r5={row_pct['row5_tw']}%, "
    f"r6={row_pct['row6_atrium']}% | "
    f"kelvin={tw_kelvin(pos)}"
)
hass.states.set("input_text.sun_debugger", debug)

# can't access the log. Durrr!