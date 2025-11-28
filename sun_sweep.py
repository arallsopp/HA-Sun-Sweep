# sun_sweep.py
# Expects:
#   data.position (0..100)
#   data.severity (0.5..2.0)
# Exports
#   input_text.sun_debugger
# Lights
#   my entities, arranged from dawn to dusk as lounge > kitchen > atrium.

pos = float(data.get("position", 0.0))
severity = float(data.get("severity", 1.0))

# --- Entity IDs ----------------------------------------------------------
lounge_tw_entities = [
    "light.slope_spot",
    "light.music_corner",
    "light.reading_light",
    "light.music_stand"
]
lounge_rgb_entities = [
    "light.towards_slope",
    "light.foot_stool",
    "light.burner",
    "light.towards_axel"
]
kitchen_tw_entities = ["light.kitchen"]
atrium_rgb_entities = [
    "light.table_uplight_colour",
    "light.table_downlight_colour"
]
atrium_tw_entities = [
    "light.table_uplight_white",
    "light.table_downlight_white"
]

# --- Helper functions ----------------------------------------------------
def clamp(v, a, b):
    return max(a, min(b, v))

def lerp(a,b,t):
    return a + (b-a)*t

def bell(x, center, width, power=3):  # power 2=sharp, 3=soft, 4=very soft
    dx = abs((x - center) / width)
    if dx >= 1:
        return 0
    return 1 - dx**power

# --- Curve centers & widths ---------------------------------------------
centers = {
    "lounge": 30,
    "kitchen": 55,
    "atrium": 85
}
base_widths = {
    "lounge": 25,
    "kitchen": 30,
    "atrium": 35
}

widths = {k: v*severity for k,v in base_widths.items()}

# --- Max brightness ------------------------------------------------------
max_brightness = {
    "lounge": 85,
    "kitchen": 100,
    "atrium": 100
}

# --- Compute envelopes --------------------------------------------------
lounge_pct = clamp(int(bell(pos, centers["lounge"], widths["lounge"])*max_brightness["lounge"]),0,100)
kitchen_pct = clamp(int(bell(pos, centers["kitchen"], widths["kitchen"])*max_brightness["kitchen"]),0,100)
atrium_pct = clamp(int(bell(pos, centers["atrium"], widths["atrium"])*max_brightness["atrium"]),0,100)

# --- Tunable white color temperatures ----------------------------------
def tw_kelvin(p):
    if p < 60:
        return 5500
    elif p < 80:
        t = (p-60)/20
        return int(lerp(5500,3500,t))
    else:
        t = (p-80)/20
        return int(lerp(3500,2200,t))

lounge_ct = tw_kelvin(pos)
kitchen_ct = tw_kelvin(pos)
atrium_ct = tw_kelvin(pos)

# --- Atrium RGBs ---------------------------------------------------------
def atrium_rgb(p,uplight=True):
    if p<=20:
        return (30,50,160)
    elif p<=40:
        t=(p-20)/20
        return (int(lerp(30,120,t)), int(lerp(50,180,t)), int(lerp(160,255,t)))
    elif p<=60:
        t=(p-40)/20
        return (int(lerp(120,255,t)), int(lerp(180,255,t)), int(lerp(255,245,t)))
    elif p<=80:
        t=(p-60)/20
        return (255, int(lerp(255,140,t)), int(lerp(245,40,t)))
    else:
        t=(p-80)/20
        return (int(lerp(255,200,t)), int(lerp(140,20,t)), int(lerp(40,255,t)))
        
# --- Atrium Sunset -------------------------------------------------------
def atrium_uplight_sunset(pos):
    """
    Ceiling uplight: amber → orange → deep purple
    Triggered for pos > 85
    """
    if pos <= 85:
        # not yet sunset, return None to fallback to normal
        return None
    # Normalize to 0..1 within the final 15%
    t = (pos - 85) / 15.0  # 0 at start of sunset, 1 at slider max
    # Interpolate RGB
    # Amber -> Orange -> Deep Purple
    if t <= 0.5:
        # Amber -> Orange
        t2 = t / 0.5
        r = int(lerp(255, 255, t2))
        g = int(lerp(140, 80, t2))
        b = int(lerp(40, 50, t2))
    else:
        # Orange -> Deep Purple
        t2 = (t - 0.5) / 0.5
        r = int(lerp(255, 120, t2))
        g = int(lerp(80, 40, t2))
        b = int(lerp(50, 150, t2))
    return (clamp(r,0,255), clamp(g,0,255), clamp(b,0,255))

def atrium_downlight_sunset(pos):
    """
    Table downlight: golden → deep orange → magenta flare
    Triggered for pos > 85
    """
    if pos <= 85:
        return None
    t = (pos - 85) / 15.0
    if t <= 0.5:
        # Golden -> Deep Orange
        t2 = t / 0.5
        r = int(lerp(255, 255, t2))
        g = int(lerp(200, 80, t2))
        b = int(lerp(100, 40, t2))
    else:
        # Deep Orange -> Magenta flare
        t2 = (t - 0.5) / 0.5
        r = int(lerp(255, 200, t2))
        g = int(lerp(80, 20, t2))
        b = int(lerp(40, 150, t2))
    return (clamp(r,0,255), clamp(g,0,255), clamp(b,0,255))
# --- Send commands -------------------------------------------------------

transition_fast = 6
transition_slow = 20

# Lounge TW
for ent in lounge_tw_entities:
    hass.services.call("light","turn_on",{
        "entity_id": ent,
        "brightness_pct": lounge_pct,
        "color_temp_kelvin": lounge_ct,
        "transition": transition_fast
    })

# Lounge RGB
for ent in lounge_rgb_entities:
    # subtle tint based on CT
    if lounge_ct>=5000:
        color=(180,200,255)
    elif lounge_ct>=3500:
        color=(255,235,200)
    else:
        color=(255,200,150)
    hass.services.call("light","turn_on",{
        "entity_id": ent,
        "brightness_pct": int(clamp(lounge_pct*0.95,0,100)),
        "rgb_color": color,
        "transition": transition_fast
    })

# Kitchen TW
for ent in kitchen_tw_entities:
    hass.services.call("light","turn_on",{
        "entity_id": ent,
        "brightness_pct": kitchen_pct,
        "color_temp_kelvin": kitchen_ct,
        "transition": transition_fast
    })

# Atrium TW
for ent in atrium_tw_entities:
    hass.services.call("light","turn_on",{
        "entity_id": ent,
        "brightness_pct": int(clamp(atrium_pct*0.9,0,100)),
        "color_temp_kelvin": atrium_ct,
        "transition": transition_slow
    })

# Atrium RGB
if pos > 85:
    # Use cinematic sunset for final 15%
    uplight_color = atrium_uplight_sunset(pos)
    downlight_color = atrium_downlight_sunset(pos)
else:
    uplight_color = atrium_rgb(pos, uplight=True)
    downlight_color = atrium_rgb(pos, uplight=False)

# Apply lights
hass.services.call("light","turn_on",{
    "entity_id": atrium_rgb_entities[0],
    "rgb_color": uplight_color,
    "brightness_pct": atrium_pct,
    "transition": transition_slow
})
hass.services.call("light","turn_on",{
    "entity_id": atrium_rgb_entities[1],
    "rgb_color": downlight_color,
    "brightness_pct": int(clamp(atrium_pct*0.9,0,100)),
    "transition": transition_slow
})

# Debugging support
debug = f"pos={pos}, sev={severity}: L{lounge_pct}/{lounge_ct}, K{kitchen_pct}/{kitchen_ct}, A{atrium_pct}/{atrium_ct}"
hass.states.set("input_text.sun_debugger", debug)

