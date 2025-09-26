import random

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

def calculate_threshold_defense(damage, defense_rating, armor_penetration=0):
    category = DAMAGE_CATEGORY(damage)
    base = DEFENSE_EFFECTIVENESS[category]
    
    # Calculate bonuses
    defense_bonus = defense_rating * 0.004  # Each defense point = +0.4% deflection
    penetration_penalty = armor_penetration * 0.003  # Each armor pen = -0.3% deflection
    
    deflection_chance = base["deflection_chance"] + defense_bonus - penetration_penalty
    deflection_chance = max(0.05, min(0.95, deflection_chance))  # Clamp between 5%-95%
    
    roll = random.random()
    
    if roll <= deflection_chance:
        # Defense succeeds
        reduction_range = base["deflection_amount"]
        reduction_factor = random.uniform(*reduction_range)
        blocked = int(damage * reduction_factor)
        actual = max(1, damage - blocked)
        return actual, blocked, True, category
    else:
        # Defense fails
        penetration_range = base["penetration_amount"]
        penetration_factor = random.uniform(*penetration_range)
        actual = int(damage * penetration_factor)
        blocked = max(0, damage - actual)
        return actual, blocked, False, category

def generate_defense_message(result, attacker_name, defender_name):
    """Generate enhanced combat messages using new defense data"""
    actual, blocked, succeeded, category = result
    total = actual + blocked
    
    if succeeded:
        if blocked > total * 0.7:
            if category == "LIGHT":
                return f"{defender_name} easily deflects the light attack! ({blocked} damage blocked)"
            elif category == "MEDIUM":
                return f"{defender_name} skillfully parries the blow! ({blocked} damage deflected)"
            elif category == "HEAVY":
                return f"{defender_name} impressively deflects the heavy strike! ({blocked} damage absorbed)"
            else:
                return f"{defender_name} miraculously deflects the devastating attack! ({blocked} damage blocked)"
        else:
            return f"{defender_name} partially deflects the attack ({blocked} damage reduced)"
    else:
        if actual > total * 0.9:
            if category in ["HEAVY", "MASSIVE"]:
                return f"The powerful attack smashes through {defender_name}'s defenses!"
            else:
                return f"The attack finds its mark, bypassing {defender_name}'s guard!"
        else:
            return f"{defender_name}'s defenses are partly overcome ({blocked} damage still blocked)"
