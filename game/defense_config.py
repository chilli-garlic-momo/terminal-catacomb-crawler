def DAMAGE_CATEGORY(damage):
    if damage <= 8:
        return "LIGHT"
    elif damage <= 20:
        return "MEDIUM"
    elif damage <= 35:
        return "HEAVY"
    else:
        return "MASSIVE"

DEFENSE_EFFECTIVENESS = {
    "LIGHT": {
        "deflection_chance": 0.7,
        "deflection_amount": (0.6, 0.9),
        "penetration_amount": (0.4, 0.7)
    },
    "MEDIUM": {
        "deflection_chance": 0.5,
        "deflection_amount": (0.4, 0.7),
        "penetration_amount": (0.6, 0.9)
    },
    "HEAVY": {
        "deflection_chance": 0.3,
        "deflection_amount": (0.3, 0.6),
        "penetration_amount": (0.8, 1.0)
    },
    "MASSIVE": {
        "deflection_chance": 0.15,
        "deflection_amount": (0.2, 0.4),
        "penetration_amount": (0.9, 1.0)
    }
}

def calculate_defense_modifiers(defense_rating):
    defense_bonus = defense_rating / 100.0
    deflection_bonus = defense_bonus * 0.4
    reduction_bonus = defense_bonus * 0.2
    return deflection_bonus, reduction_bonus

def apply_armor_penetration(deflection_chance, armor_penetration):
    penetration_factor = armor_penetration / 100.0
    deflection_penalty = penetration_factor * 0.3
    return max(0.05, deflection_chance - deflection_penalty)

def calculate_threshold_defense(damage, defense_rating, armor_penetration=0):
    import random
    category = DAMAGE_CATEGORY(damage)
    base = DEFENSE_EFFECTIVENESS[category]
    deflection_bonus, reduction_bonus = calculate_defense_modifiers(defense_rating)
    deflection_chance = base["deflection_chance"] + deflection_bonus
    deflection_chance = apply_armor_penetration(deflection_chance, armor_penetration)
    roll = random.random()
    if roll <= deflection_chance:
        reduction_range = base["deflection_amount"]
        reduction_factor = random.uniform(*reduction_range)
        reduction_factor = min(0.95, reduction_factor + reduction_bonus)
        blocked = int(damage * reduction_factor)
        actual = max(1, damage - blocked)
        return actual, blocked, True, category
    else:
        penetration_range = base["penetration_amount"]
        penetration_factor = random.uniform(*penetration_range)
        actual = int(damage * penetration_factor)
        blocked = max(0, damage - actual)
        return actual, blocked, False, category
