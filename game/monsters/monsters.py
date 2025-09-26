"""
Monster System - Handles monster AI, stats, and combat using MonsterDatabase
"""

import random
from .monster_database import MonsterDatabase, MonsterStatsSystem
from game.defense_config import calculate_threshold_defense

class Monster:
    """Base monster class using MonsterDatabase for definitions"""
    
    def __init__(self, x, y, monster_category, monster_type):
        # Position
        self.x = x
        self.y = y
        
        # Monster identity
        self.category = monster_category
        self.type = monster_type
        
        # Get monster data from database
        self.data = MonsterDatabase.MONSTERS[monster_category][monster_type]
        
        # Initialize combat state before setup
        self.attack_cooldowns = {}
        self.status_effects = {}
        
        self.setup_monster_stats()
        
        # AI state
        self.last_seen_player = None
        self.alert_turns = 0
        self.max_alert = 5
    
    def get_attacks(self):
        """Get monster attacks - either calculated or legacy"""
        if hasattr(self, 'calculated_attacks'):
            return self.calculated_attacks
        else:
            return self.data.get('attacks', [])
        
    def setup_monster_stats(self):
        """Setup stats based on monster data from database"""
        # Basic info
        self.name = self.data['name']
        self.symbol = self.data['symbol']
        self.color = self.data['color']
        self.description = self.data['description']
        self.level = self.data.get('level', 1)  # Monster level for experience multipliers
        
        # Check if monster uses new stats system
        if 'base_stats' in self.data and 'creature_type' in self.data:
            # New stats system - calculate stats dynamically
            self.stats_system = MonsterStatsSystem()
            calculated_stats = self.stats_system.calculate_stats(
                self.data['base_stats'], 
                self.data['creature_type'], 
                self.data.get('level', 1)
            )
            
            # Combat stats from calculated values
            self.max_hp = calculated_stats['hp']
            self.hp = self.max_hp
            self.attack = calculated_stats['attack'] 
            self.defense = calculated_stats['defense']
            self.speed = calculated_stats['speed']
            self.accuracy = calculated_stats['accuracy'] / 100.0  # Convert to decimal
            
            # Experience reward - check both new format and legacy format
            if 'exp_reward' in self.data:
                self.exp_reward = self.data['exp_reward']
            else:
                legacy = self.data.get('legacy_stats', {})
                self.exp_reward = legacy.get('exp_reward', 10)
            
            # Store main stats for reference
            self.main_stats = self.data['base_stats'].copy()
            self.derived_stats = calculated_stats
            
            # Calculate dynamic attacks using main stats for formulas
            self.calculated_attacks = []
            if 'attacks' in self.data:
                # Get the creature type data to calculate main stats with affinities
                creature_data = MonsterDatabase.CREATURE_TYPES.get(self.data['creature_type'], MonsterDatabase.CREATURE_TYPES['brute'])
                level = self.data.get('level', 1)
                
                # Calculate main stats with affinities for use in attack formulas
                main_stats_for_attacks = {}
                for stat_name, base_value in self.data['base_stats'].items():
                    affinity = creature_data['affinities'].get(stat_name, 1.0)
                    main_stats_for_attacks[stat_name] = int(base_value * affinity * level)
                
                for attack_data in self.data['attacks']:
                    calculated_attack = self.stats_system.calculate_attack_stats(attack_data, main_stats_for_attacks)
                    self.calculated_attacks.append(calculated_attack)
            
        else:
            # Legacy stats system - use old format
            stats = self.data['stats']
            self.max_hp = stats['hp']
            self.hp = self.max_hp
            self.attack = stats['attack']
            self.defense = stats['defense']
            self.speed = stats['speed']
            self.accuracy = stats['accuracy']
            self.exp_reward = stats['exp_reward']
        
        # Simple AI defaults - no complex AI needed
        # Basic AI attributes for movement and detection
        self.aggression = 0.8
        self.detection_range = 6
        
        # Initialize attack cooldowns
        for attack in self.data['attacks']:
            self.attack_cooldowns[attack['name']] = 0
            
    def is_alive(self):
        """Check if monster is still alive"""
        return self.hp > 0
        
    def take_damage(self, damage, attacker_armor_penetration=0):
        defense_rating = self.derived_stats.get("damage_reduction", 0)
        actual, blocked, succeeded, category = calculate_threshold_defense(
            damage, defense_rating, attacker_armor_penetration
        )
        self.hp -= actual
        # Optionally: store blocked damage or log it
        return actual, blocked, succeeded, category
        
    def get_distance_to(self, x, y):
        """Calculate distance to a position"""
        return abs(self.x - x) + abs(self.y - y)
        
    def can_see_player(self, player):
        """Check if monster can detect the player"""
        distance = self.get_distance_to(player.x, player.y)
        return distance <= self.detection_range
        
    def get_available_attacks(self):
        """Get list of attacks that are not on cooldown"""
        available = []
        
        # Use calculated attacks if available (new stats system)
        if hasattr(self, 'calculated_attacks') and self.calculated_attacks:
            for attack in self.calculated_attacks:
                if self.attack_cooldowns[attack['name']] <= 0:
                    available.append(attack)
        else:
            # Use raw attack data (legacy system)
            for attack in self.data['attacks']:
                if self.attack_cooldowns[attack['name']] <= 0:
                    available.append(attack)
        return available
        
    def choose_attack(self):
        """Choose an attack from available options"""
        available_attacks = self.get_available_attacks()
        
        # Always include basic attack as an option
        # Convert accuracy to percentage (0.0-1.0) if it's a raw number
        accuracy_value = self.accuracy
        if accuracy_value > 1.0:
            accuracy_value = accuracy_value / 100.0
        
        basic_attack = {
            'name': 'Basic Attack',
            'damage': self.attack,
            'accuracy': accuracy_value,
            'description': f'{self.name} attacks',
            'type': 'basic',
            'cooldown': 0,
            'special_effects': None
        }
        
        # Simple strategy: use special attacks when available, otherwise basic attack
        if available_attacks and random.random() < 0.7:  # 70% chance to use special attack
            # Prefer higher damage attacks
            return max(available_attacks, key=lambda a: a['damage'])
        else:
            return basic_attack
    
    def update_cooldowns(self):
        """Reduce all attack cooldowns by 1"""
        for attack_name in self.attack_cooldowns:
            if self.attack_cooldowns[attack_name] > 0:
                self.attack_cooldowns[attack_name] -= 1
                
    def update_status_effects(self):
        """Update and apply status effects"""
        effects_to_remove = []
        damage_taken = 0
        
        for effect_name, effect_data in self.status_effects.items():
            effect_data['duration'] -= 1
            
            # Apply effect
            if effect_name == 'poison':
                damage_taken += effect_data['damage_per_turn']
            
            # Remove expired effects
            if effect_data['duration'] <= 0:
                effects_to_remove.append(effect_name)
                
        # Remove expired effects
        for effect_name in effects_to_remove:
            del self.status_effects[effect_name]
            
        # Apply damage from status effects
        if damage_taken > 0:
            self.hp = max(0, self.hp - damage_taken)
            
        return damage_taken
        
    def ai_turn(self, player, level):
        """Execute AI behavior for this turn"""
        if not self.is_alive():
            return None
            
        # Update cooldowns and status effects
        self.update_cooldowns()
        status_damage = self.update_status_effects()
        
        events = []
        if status_damage > 0:
            events.append({
                "type": "status_damage",
                "target": self.name,
                "damage": status_damage
            })
            
        # Check if player is visible
        if self.can_see_player(player):
            self.last_seen_player = (player.x, player.y)
            self.alert_turns = self.max_alert
            
            # If adjacent to player, attack
            if self.get_distance_to(player.x, player.y) == 1:
                attack_event = self.attack_player(player)
                if attack_event:
                    events.append(attack_event)
            
            # Otherwise, move towards player if aggressive enough
            elif random.random() < self.aggression:
                new_x, new_y = self.get_move_towards_player(player, level)
                if level.is_walkable(new_x, new_y):
                    self.x, self.y = new_x, new_y
                    
        elif self.alert_turns > 0:
            # Move towards last known player position
            self.alert_turns -= 1
            if self.last_seen_player:
                target_x, target_y = self.last_seen_player
                new_x, new_y = self.get_move_towards_target(target_x, target_y, level)
                if level.is_walkable(new_x, new_y):
                    self.x, self.y = new_x, new_y
        else:
            # Wander randomly
            self.wander(level)
            
        return events if events else None
        
    def get_move_towards_player(self, player, level):
        """Calculate next move towards player"""
        dx = 0 if self.x == player.x else (1 if self.x < player.x else -1)
        dy = 0 if self.y == player.y else (1 if self.y < player.y else -1)
        
        # Try to move diagonally first, then straight
        if dx != 0 and dy != 0:
            # Try diagonal movement
            if level.is_walkable(self.x + dx, self.y + dy):
                return self.x + dx, self.y + dy
        
        # Try horizontal movement
        if dx != 0 and level.is_walkable(self.x + dx, self.y):
            return self.x + dx, self.y
            
        # Try vertical movement
        if dy != 0 and level.is_walkable(self.x, self.y + dy):
            return self.x, self.y + dy
            
        return self.x, self.y  # Can't move
        
    def get_move_towards_target(self, target_x, target_y, level):
        """Move towards a specific target position"""
        dx = 0 if self.x == target_x else (1 if self.x < target_x else -1)
        dy = 0 if self.y == target_y else (1 if self.y < target_y else -1)
        
        new_x = self.x + dx
        new_y = self.y + dy
        
        if level.is_walkable(new_x, new_y):
            return new_x, new_y
        return self.x, self.y
        
    def wander(self, level):
        """Random movement when not alert"""
        if random.random() < 0.3:
            directions = [(0, 1), (0, -1), (1, 0), (-1, 0)]
            dx, dy = random.choice(directions)
            new_x, new_y = self.x + dx, self.y + dy
            
            if level.is_walkable(new_x, new_y):
                self.x, self.y = new_x, new_y
                
    def attack_player(self, player):
        """Attack the player using monster's attack system"""
        chosen_attack = self.choose_attack()
        
        # Set cooldown for the attack
        if chosen_attack['name'] in self.attack_cooldowns:
            self.attack_cooldowns[chosen_attack['name']] = chosen_attack['cooldown']
        
        # Calculate hit chance vs monster accuracy
        hit_roll = random.random()
        if hit_roll > chosen_attack['accuracy']:
            # Show clearer miss explanation
            needed = int(chosen_attack['accuracy'] * 100)
            rolled = int(hit_roll * 100)
            miss_reason = f" (Needed ≤{needed}%, rolled {rolled}%)"
            return {
                "type": "combat",
                "attacker": self.name,
                "attack_name": chosen_attack['name'],
                "damage": 0,
                "hit": False,
                "description": f"{self.name} misses!{miss_reason}",
                "player_died": False,
                "hit_roll": hit_roll,
                "monster_accuracy": chosen_attack['accuracy']
            }
        
        # Check player dodge chance
        player_dodge_chance = min(95, max(0, player.dodge)) / 100.0  # Convert to 0-1 range, cap at 95%
        dodge_roll = random.random()
        if dodge_roll <= player_dodge_chance:
            # Show clearer dodge explanation  
            needed = int(player_dodge_chance * 100)
            rolled = int(dodge_roll * 100)
            dodge_reason = f" (Rolled {rolled}% ≤ {needed}% dodge chance)"
            return {
                "type": "combat",
                "attacker": self.name,
                "attack_name": chosen_attack['name'],
                "damage": 0,
                "hit": False,
                "dodged": True,
                "description": f"{player.name} dodges {self.name}'s {chosen_attack['name']}!{dodge_reason}",
                "player_died": False,
                "dodge_roll": dodge_roll,
                "player_dodge_chance": player_dodge_chance
            }
        
        # Calculate damage
        base_damage = chosen_attack['damage']
        damage_variance = random.randint(-4, 2)
        final_damage = max(1, base_damage + damage_variance)
        
        # Apply attack to player
        monster_armor_penetration = self.derived_stats.get('armor_penetration', 0) if hasattr(self, 'derived_stats') else 0
        damage_result = player.take_damage(final_damage, monster_armor_penetration)
        message = generate_defense_message(damage_result, monster.name, player.name)
        print(message) # Or pass to your UI/log
        player_died = damage_result["died"]
        
        # Handle special effects
        effect_description = chosen_attack['description']
        if chosen_attack['special_effects']:
            effect_description += self.apply_special_effect(chosen_attack['special_effects'], player)
        
        # Get deflected damage for return data (UI will handle display)
        deflected = damage_result.get("deflected", 0)
        
        return {
            "type": "combat",
            "attacker": self.name,
            "attack_name": chosen_attack['name'],
            "damage": final_damage,
            "deflected": deflected,
            "damage_reduction": damage_result.get("damage_reduction", 0),
            "base_damage_reduction": damage_result.get("base_damage_reduction", 0),
            "armor_penetration": monster_armor_penetration,
            "base_attack_damage": base_damage,
            "damage_variance": damage_variance,
            "original_damage": damage_result.get("original_damage", final_damage),
            "final_damage": damage_result.get("final_damage", final_damage - deflected),
            "hit": True,
            "dodged": False,
            "description": effect_description,
            "player_died": player_died,
            "special_effects": chosen_attack['special_effects']
        }
        
    def apply_special_effect(self, effect, player):
        """Apply special attack effects"""
        if not effect:
            return ""
            
        effect_type = effect['type']
        
        if effect_type == 'poison':
            # Apply poison to player (would need player to support status effects)
            return f" and inflicts poison!"
        elif effect_type == 'intimidate':
            # Apply intimidation effect
            return f" and intimidates the player!"
        elif effect_type == 'armor_break':
            # Apply armor break effect
            return f" and weakens armor!"
        elif effect_type == 'magic_damage':
            # Magic damage ignores armor
            return f" with magical force!"
        
        return ""
        
    def get_drops(self):
        """Generate random drops based on monster's drop table"""
        drops = []
        drop_chances = self.data['drop_chances']
        possible_drops = self.data.get('possible_drops', {})
        
        for category, chance in drop_chances.items():
            if random.random() < chance and category in possible_drops:
                # Pick a random item from this category
                items = possible_drops[category]
                if items:
                    drops.append(random.choice(items))
                    
        return drops


class MonsterManager:
    """Manages all monsters on the current level - replaces EnemyManager"""
    
    def __init__(self):
        self.enemies = []  # Keep the same attribute name for compatibility
        self.monsters = []  # Additional reference for clarity
                    
    def spawn_monster(self, x, y, category, monster_type):
        """Spawn a specific monster type"""
        monster = Monster(x, y, category, monster_type)
        self.enemies.append(monster)
        self.monsters.append(monster)
        return monster
        
    def get_enemy_at(self, x, y):
        """Get monster at specific position - maintains EnemyManager interface"""
        for monster in self.enemies:
            if monster.x == x and monster.y == y and monster.is_alive():
                return monster
        return None
        
    def get_monster_at(self, x, y):
        """Get monster at specific position"""
        return self.get_enemy_at(x, y)
        
    def remove_dead_enemies(self):
        """Remove dead monsters from the list"""
        alive_monsters = [monster for monster in self.enemies if monster.is_alive()]
        self.enemies = alive_monsters
        self.monsters = alive_monsters
    
    def remove_enemy(self, enemy):
        """Remove a specific enemy from the list"""
        if enemy in self.enemies:
            self.enemies.remove(enemy)
        if enemy in self.monsters:
            self.monsters.remove(enemy)
        
    def update_all(self, player, level):
        """Update all monsters (AI turns) - maintains EnemyManager interface"""
        combat_events = []
        
        for monster in self.enemies[:]:
            if monster.is_alive():
                events = monster.ai_turn(player, level)
                if events:
                    if isinstance(events, list):
                        combat_events.extend(events)
                    else:
                        combat_events.append(events)
                        
        self.remove_dead_enemies()
        
        return combat_events
        
    def get_all_positions(self):
        """Get positions of all living monsters"""
        return [(monster.x, monster.y) for monster in self.enemies if monster.is_alive()]
        
    def get_monsters_by_category(self, category):
        """Get all monsters of a specific category"""
        return [monster for monster in self.monsters if monster.category == category and monster.is_alive()]
        
    def get_total_exp_value(self):
        """Get total experience value of all living monsters"""
        return sum(monster.exp_reward for monster in self.monsters if monster.is_alive())
    
    def spawn_random_monster(self, x, y, difficulty_tier="easy"):
        """Spawn a random monster from the database by difficulty tier"""
        category, monster_type = MonsterDatabase.get_random_monster_by_tier(difficulty_tier)
        return self.spawn_monster(x, y, category, monster_type)
    
    def spawn_random_monster_by_exp(self, x, y, min_exp=0, max_exp=30):
        """Spawn a random monster within an exp reward range"""
        category, monster_type = MonsterDatabase.get_random_monster_by_difficulty(min_exp, max_exp)
        return self.spawn_monster(x, y, category, monster_type)
    
    def spawn_monster_from_category(self, x, y, category):
        """Spawn a random monster from a specific category"""
        available_types = MonsterDatabase.get_monsters_in_category(category)
        if not available_types:
            # Fallback to easy monster if category doesn't exist
            return self.spawn_random_monster(x, y, "easy")
        
        import random
        monster_type = random.choice(available_types)
        return self.spawn_monster(x, y, category, monster_type)
    
    def spawn_monster_by_level(self, x, y, player_level):
        """Spawn a monster appropriate for the player's level
        
        Args:
            x, y: Position to spawn monster
            player_level: Player's current level
            
        Spawns:
            80% chance: monster at player's level
            20% chance: monster one level above player
        """
        import random
        
        # Determine target monster level
        if random.random() < 0.8:  # 80% chance
            target_level = player_level
        else:  # 20% chance
            target_level = player_level + 1
        
        # Get monsters at the target level
        category, monster_type = MonsterDatabase.get_random_monster_by_level(target_level)
        return self.spawn_monster(x, y, category, monster_type)


# Alias for backward compatibility
EnemyManager = MonsterManager
Enemy = Monster
